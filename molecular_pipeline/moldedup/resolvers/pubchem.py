"""PubChem PUG REST resolver.

Resolves a name → CID(s) → Standard InChIKey + properties + synonyms, with
caching, retries (exponential backoff on 5xx / timeouts / PUGREST.ServerBusy),
per-request timeouts and client-side rate limiting.

Ambiguity: if a name maps to more than one CID, we do NOT guess — the result is
flagged `ambiguous` and the pipeline routes it to manual review.

Docs: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import List, Optional, Tuple
from urllib.parse import quote

import requests

from ..cache import HttpCache
from ..config import Config
from ..ratelimit import RateLimiter
from .base import ResolutionResult, Resolver

log = logging.getLogger("moldedup.pubchem")

PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# CAS regex, e.g. 121-33-5 ; ChEBI / HMDB / KEGG registry patterns among synonyms.
_CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
_CHEBI_RE = re.compile(r"^CHEBI:\d+$", re.I)
_HMDB_RE = re.compile(r"^HMDB\d+$", re.I)
_KEGG_RE = re.compile(r"^C\d{5}$")

# Retryable HTTP statuses + PubChem's soft "busy" signal.
_RETRY_STATUS = {429, 500, 502, 503, 504}

_CLASSIC_PROPS = ("InChIKey,InChI,CanonicalSMILES,IsomericSMILES,"
                  "MolecularFormula,MolecularWeight,IUPACName")
_MIN_PROPS = "InChIKey,InChI,MolecularFormula,MolecularWeight,IUPACName"
# PubChem renamed the SMILES properties in 2024; try the modern names as a fallback.
_MODERN_SMILES = "ConnectivitySMILES,SMILES"


class PubChemResolver(Resolver):
    name = "pubchem"

    def __init__(self, config: Optional[Config] = None, cache: Optional[HttpCache] = None,
                 session: Optional["requests.Session"] = None):
        self.cfg = config or Config()
        self.cache = cache if cache is not None else HttpCache(self.cfg.cache_path, self.cfg.cache_ttl)
        self.limiter = RateLimiter(self.cfg.min_request_interval)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": self.cfg.user_agent})

    # ---- HTTP with cache + retry + rate limit + timeout -------------------
    def _get(self, url: str) -> Tuple[int, Optional[dict]]:
        """Return (status_code, parsed_json_or_None). Cached (including negatives)."""
        cached = self.cache.get(url)
        if cached is not None:
            body = cached["body"]
            return cached["status"], (json.loads(body) if body else None)

        last_exc = None
        for attempt in range(self.cfg.max_retries + 1):
            self.limiter.wait()
            try:
                resp = self.session.get(url, timeout=self.cfg.request_timeout)
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exc = exc
                self._sleep_backoff(attempt)
                continue

            if resp.status_code in _RETRY_STATUS:
                self._sleep_backoff(attempt)
                last_exc = RuntimeError(f"HTTP {resp.status_code}")
                continue

            text = resp.text or ""
            # PubChem sometimes returns 200 with a soft "ServerBusy" fault → retry.
            if "PUGREST.ServerBusy" in text and attempt < self.cfg.max_retries:
                self._sleep_backoff(attempt)
                continue

            parsed = None
            if text.strip():
                try:
                    parsed = resp.json()
                except ValueError:
                    parsed = None
            # cache success + genuine "not found"; do not cache transient failures
            if resp.status_code == 200 or resp.status_code == 404:
                self.cache.set(url, resp.status_code, text)
            return resp.status_code, parsed

        raise RuntimeError(f"PubChem request failed after retries: {url} ({last_exc})")

    def _sleep_backoff(self, attempt: int) -> None:
        time.sleep(self.cfg.backoff_base * (2 ** attempt))

    # ---- resolution steps ------------------------------------------------
    def _name_to_cids(self, name: str) -> List[int]:
        url = f"{PUG}/compound/name/{quote(name, safe='')}/cids/JSON"
        status, data = self._get(url)
        if status == 404 or not data:
            return []
        return list(data.get("IdentifierList", {}).get("CID", []) or [])

    def _properties(self, cid: int) -> dict:
        """Best-effort property fetch, tolerant of PubChem's property-name changes."""
        url = f"{PUG}/compound/cid/{cid}/property/{_CLASSIC_PROPS}/JSON"
        status, data = self._get(url)
        props = self._first_prop(data)
        if status == 200 and props:
            return props
        # classic names rejected → minimal safe set + modern SMILES names
        _, data_min = self._get(f"{PUG}/compound/cid/{cid}/property/{_MIN_PROPS}/JSON")
        props = self._first_prop(data_min) or {}
        _, data_smiles = self._get(f"{PUG}/compound/cid/{cid}/property/{_MODERN_SMILES}/JSON")
        smiles = self._first_prop(data_smiles) or {}
        if smiles.get("SMILES"):
            props.setdefault("IsomericSMILES", smiles["SMILES"])
        if smiles.get("ConnectivitySMILES"):
            props.setdefault("CanonicalSMILES", smiles["ConnectivitySMILES"])
        return props

    @staticmethod
    def _first_prop(data: Optional[dict]) -> Optional[dict]:
        if not data:
            return None
        rows = data.get("PropertyTable", {}).get("Properties", [])
        return rows[0] if rows else None

    def _synonyms(self, cid: int) -> List[str]:
        url = f"{PUG}/compound/cid/{cid}/synonyms/JSON"
        _, data = self._get(url)
        if not data:
            return []
        info = data.get("InformationList", {}).get("Information", [])
        if not info:
            return []
        return list(info[0].get("Synonym", []) or [])

    # ---- public API ------------------------------------------------------
    def resolve(self, name: str) -> ResolutionResult:
        r = ResolutionResult(query=name, source_name=self.name)
        cids = self._name_to_cids(name)
        if not cids:
            r.resolved = False
            r.review_reason = "no PubChem match for name"
            return r
        if len(cids) > 1:
            r.ambiguous = True
            r.review_reason = f"name maps to {len(cids)} PubChem CIDs: {cids[:10]}"
            r.cid = cids[0]
            return r

        cid = int(cids[0])
        props = self._properties(cid)
        inchikey = (props.get("InChIKey") or "").strip()
        if not inchikey:
            r.resolved = False
            r.review_reason = f"CID {cid} returned no InChIKey"
            r.cid = cid
            return r

        r.resolved = True
        r.cid = cid
        r.inchikey = inchikey
        r.inchi = props.get("InChI")
        r.canonical_smiles = props.get("CanonicalSMILES")
        r.isomeric_smiles = props.get("IsomericSMILES")
        r.formula = props.get("MolecularFormula")
        r.iupac_name = props.get("IUPACName")
        r.molecular_weight = _to_float(props.get("MolecularWeight"))

        syns = self._synonyms(cid)
        r.synonyms = syns
        r.add_external("CID", str(cid))
        for s in syns:
            s = s.strip()
            if _CAS_RE.match(s):
                if r.cas is None:
                    r.cas = s
                r.add_external("CAS", s)
            elif _CHEBI_RE.match(s):
                r.add_external("ChEBI", s.upper())
            elif _HMDB_RE.match(s):
                r.add_external("HMDB", s.upper())
            elif _KEGG_RE.match(s):
                r.add_external("KEGG", s)
        return r


def _to_float(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
