"""The ingestion pipeline — the 8-step name → canonical-molecule dedup logic.

For every incoming name:
    1. normalize the text
    2. if we've already resolved this synonym → done (idempotent)
    3. resolve the name via the injected resolver (PubChem by default)
    4. obtain the Standard InChIKey
    5. look up an existing molecule by that InChIKey
    6. found  → attach the synonym to it
    7. not    → create a new molecule record
    8. store all identifiers (CAS/CID/…), every synonym, and provenance

Ambiguous names (resolver returned >1 candidate) and unresolved names are NOT
guessed — they are stored as review-flagged synonyms with no molecule.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional

from sqlalchemy.exc import IntegrityError

from .models import (
    STATUS_AMBIGUOUS, STATUS_RESOLVED, STATUS_UNRESOLVED,
    ExternalIdentifier, Molecule, Source, Synonym,
)
from .normalize import clean_display_name, normalize_name
from .resolvers.base import Resolver, ResolutionResult

log = logging.getLogger("moldedup.pipeline")

# Outcome statuses
CREATED = "created"        # new molecule created
ATTACHED = "attached"      # synonym attached to an existing molecule
EXISTS = "exists"          # synonym already known + resolved (no work done)
AMBIGUOUS = "ambiguous"    # flagged for manual review
UNRESOLVED = "unresolved"  # flagged for manual review
ERROR = "error"            # resolver/DB error (name left unstored)


@dataclass
class IngestOutcome:
    name: str
    status: str
    inchikey: Optional[str] = None
    message: str = ""


class IngestionPipeline:
    def __init__(self, session_factory, resolver: Resolver, logger: Optional[logging.Logger] = None):
        self.session_factory = session_factory
        self.resolver = resolver
        self.log = logger or log

    # ---- source provenance ----------------------------------------------
    def get_or_create_source(self, session, name: str, kind: str = "import",
                             detail: str = "") -> Source:
        src = session.query(Source).filter_by(name=name).one_or_none()
        if src is None:
            src = Source(name=name, kind=kind, detail=detail)
            session.add(src)
            session.flush()
        return src

    # ---- single name -----------------------------------------------------
    def ingest_name(self, session, name: str, source: Source) -> IngestOutcome:
        """Ingest ONE name within an existing session (caller commits)."""
        norm = normalize_name(name)
        display = clean_display_name(name)
        if not norm:
            return IngestOutcome(name, ERROR, message="empty name")

        # (2) already seen + resolved?
        existing = session.query(Synonym).filter_by(normalized_name=norm).one_or_none()
        if existing is not None and existing.status == STATUS_RESOLVED and existing.molecule_id:
            mol = existing.molecule
            return IngestOutcome(name, EXISTS, inchikey=mol.inchikey if mol else None,
                                 message="synonym already resolved")

        # (3) resolve
        result = self.resolver.resolve(name)

        # ambiguous → review, do not guess
        if result.ambiguous:
            self._upsert_review_synonym(session, norm, display, source,
                                        STATUS_AMBIGUOUS, result.review_reason or "ambiguous")
            return IngestOutcome(name, AMBIGUOUS, message=result.review_reason or "ambiguous")

        # (4) require an InChIKey
        if not result.resolved or not result.inchikey:
            self._upsert_review_synonym(session, norm, display, source,
                                        STATUS_UNRESOLVED, result.review_reason or "no match")
            return IngestOutcome(name, UNRESOLVED, message=result.review_reason or "no match")

        # (5) find molecule by canonical InChIKey
        mol = session.query(Molecule).filter_by(inchikey=result.inchikey).one_or_none()
        created = False
        if mol is None:
            # (7) create
            mol = Molecule(
                inchikey=result.inchikey,
                inchi=result.inchi,
                cid=result.cid,
                canonical_smiles=result.canonical_smiles,
                isomeric_smiles=result.isomeric_smiles,
                formula=result.formula,
                molecular_weight=result.molecular_weight,
                iupac_name=result.iupac_name,
                preferred_name=result.iupac_name or display,
            )
            session.add(mol)
            session.flush()
            created = True
        else:
            self._backfill(mol, result, display)

        # (6) attach the input synonym
        self._attach_synonym(session, mol, norm, display, source, STATUS_RESOLVED)

        # (8) store every resolver synonym + identifiers + provenance
        resolver_source = self.get_or_create_source(session, self.resolver.name, kind="resolver")
        for syn in result.synonyms:
            sn = normalize_name(syn)
            if not sn or sn == norm:
                continue
            self._attach_synonym(session, mol, sn, clean_display_name(syn),
                                 resolver_source, STATUS_RESOLVED, skip_if_other=True)
        self._store_external_ids(session, mol, result, resolver_source)

        return IngestOutcome(name, CREATED if created else ATTACHED, inchikey=mol.inchikey,
                             message="ok")

    # ---- batch -----------------------------------------------------------
    def ingest_batch(self, names: Iterable[str], source_name: str,
                     source_detail: str = "") -> List[IngestOutcome]:
        """Ingest many names. One session; committed per name so progress persists
        and a single bad name never rolls back the whole batch."""
        session = self.session_factory()
        outcomes: List[IngestOutcome] = []
        try:
            source = self.get_or_create_source(session, source_name, kind="import",
                                                detail=source_detail)
            session.commit()
            for raw in names:
                name = (raw or "").strip()
                if not name:
                    continue
                try:
                    outcome = self.ingest_name(session, name, source)
                    session.commit()
                except IntegrityError as exc:
                    session.rollback()
                    outcome = self._retry_after_conflict(session, name, source, exc)
                except Exception as exc:  # noqa: BLE001 — never let one name kill the batch
                    session.rollback()
                    self.log.exception("error ingesting %r", name)
                    outcome = IngestOutcome(name, ERROR, message=str(exc)[:200])
                outcomes.append(outcome)
                self.log.info("[%s] %s", outcome.status, name)
        finally:
            session.close()
        return outcomes

    def _retry_after_conflict(self, session, name, source, exc) -> IngestOutcome:
        """A unique-constraint race (e.g. concurrent writer created the same
        InChIKey/synonym). Re-run once; the second pass finds the existing row."""
        try:
            outcome = self.ingest_name(session, name, source)
            session.commit()
            return outcome
        except Exception as exc2:  # noqa: BLE001
            session.rollback()
            self.log.warning("conflict retry failed for %r: %s", name, exc2)
            return IngestOutcome(name, ERROR, message=f"conflict: {str(exc)[:120]}")

    # ---- helpers ---------------------------------------------------------
    def _attach_synonym(self, session, mol: Molecule, norm: str, display: str,
                        source: Source, status: str, skip_if_other: bool = False) -> Synonym:
        syn = session.query(Synonym).filter_by(normalized_name=norm).one_or_none()
        if syn is None:
            syn = Synonym(molecule_id=mol.id, name=display, normalized_name=norm,
                          status=status, source_id=source.id)
            session.add(syn)
            return syn
        if syn.molecule_id is None:
            syn.molecule_id = mol.id
            syn.status = status
            syn.review_reason = None
        elif syn.molecule_id != mol.id:
            # same normalized string already points at a DIFFERENT molecule → real collision
            self.log.warning("synonym %r already maps to molecule %s, not reassigning to %s",
                             norm, syn.molecule_id, mol.id)
        return syn

    def _upsert_review_synonym(self, session, norm: str, display: str, source: Source,
                               status: str, reason: str) -> Synonym:
        syn = session.query(Synonym).filter_by(normalized_name=norm).one_or_none()
        if syn is None:
            syn = Synonym(molecule_id=None, name=display, normalized_name=norm,
                          status=status, review_reason=reason, source_id=source.id)
            session.add(syn)
        elif syn.molecule_id is None:  # don't overwrite an already-resolved synonym
            syn.status = status
            syn.review_reason = reason
        return syn

    def _store_external_ids(self, session, mol: Molecule, result: ResolutionResult,
                            source: Source) -> None:
        # De-duplicate the incoming pairs (CID may arrive both from result.cid and
        # from external_ids["CID"]), then insert only those not already stored.
        pairs = set()
        if result.cid:
            pairs.add(("CID", str(result.cid)))
        for scheme, values in result.external_ids.items():
            for v in values:
                if v:
                    pairs.add((scheme, str(v)))
        if not pairs:
            return
        existing = {(scheme, value) for scheme, value in
                    session.query(ExternalIdentifier.scheme, ExternalIdentifier.value)
                    .filter(ExternalIdentifier.molecule_id == mol.id).all()}
        for scheme, value in pairs - existing:
            session.add(ExternalIdentifier(molecule_id=mol.id, scheme=scheme,
                                           value=value, source_id=source.id))

    @staticmethod
    def _backfill(mol: Molecule, result: ResolutionResult, display: str) -> None:
        """Fill only fields that are currently empty — never clobber good data."""
        if mol.inchi is None: mol.inchi = result.inchi
        if mol.cid is None: mol.cid = result.cid
        if mol.canonical_smiles is None: mol.canonical_smiles = result.canonical_smiles
        if mol.isomeric_smiles is None: mol.isomeric_smiles = result.isomeric_smiles
        if mol.formula is None: mol.formula = result.formula
        if mol.molecular_weight is None: mol.molecular_weight = result.molecular_weight
        if mol.iupac_name is None: mol.iupac_name = result.iupac_name
        if not mol.preferred_name: mol.preferred_name = result.iupac_name or display
