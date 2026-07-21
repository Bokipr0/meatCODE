"""PubChem resolver parsing — with a fake HTTP session (no network)."""
import json

from moldedup.config import Config
from moldedup.resolvers.pubchem import PubChemResolver


class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self.text = json.dumps(payload) if payload is not None else ""

    def json(self):
        if not self.text:
            raise ValueError("no json")
        return json.loads(self.text)


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.headers = {}

    def get(self, url, timeout=None):
        for frag, resp in self.routes.items():
            if frag in url:
                return resp
        return FakeResp(404, None)


VANILLIN_ROUTES = {
    "name/vanillin/cids": FakeResp(200, {"IdentifierList": {"CID": [1183]}}),
    "cid/1183/property": FakeResp(200, {"PropertyTable": {"Properties": [{
        "CID": 1183, "InChIKey": "MWOOGOJBHIARFG-UHFFFAOYSA-N",
        "InChI": "InChI=1S/C8H8O3/...", "CanonicalSMILES": "COC1=CC(=CC=C1O)C=O",
        "IsomericSMILES": "COC1=CC(=CC=C1O)C=O", "MolecularFormula": "C8H8O3",
        "MolecularWeight": "152.15", "IUPACName": "4-hydroxy-3-methoxybenzaldehyde"}]}}),
    "cid/1183/synonyms": FakeResp(200, {"InformationList": {"Information": [{
        "CID": 1183, "Synonym": ["Vanillin", "121-33-5",
                                 "4-Hydroxy-3-methoxybenzaldehyde", "CHEBI:18346"]}]}}),
}


def _resolver(tmp_path, routes):
    cfg = Config(min_request_interval=0.0, cache_path=str(tmp_path / "cache.sqlite"))
    return PubChemResolver(cfg, session=FakeSession(routes))


def test_resolves_vanillin(tmp_path):
    r = _resolver(tmp_path, VANILLIN_ROUTES).resolve("vanillin")
    assert r.resolved and not r.ambiguous
    assert r.inchikey == "MWOOGOJBHIARFG-UHFFFAOYSA-N"
    assert r.cid == 1183
    assert r.formula == "C8H8O3"
    assert r.molecular_weight == 152.15
    assert r.cas == "121-33-5"
    assert r.canonical_smiles == "COC1=CC(=CC=C1O)C=O"
    assert "CHEBI:18346" in r.external_ids.get("ChEBI", [])
    assert "121-33-5" in r.external_ids.get("CAS", [])


def test_ambiguous_multiple_cids(tmp_path):
    routes = {"name/glucose/cids": FakeResp(200, {"IdentifierList": {"CID": [5793, 79025]}})}
    r = _resolver(tmp_path, routes).resolve("glucose")
    assert r.ambiguous and not r.resolved
    assert r.review_reason and "2 PubChem CIDs" in r.review_reason


def test_unknown_name_not_resolved(tmp_path):
    r = _resolver(tmp_path, {}).resolve("definitely-not-a-molecule")  # all 404
    assert not r.resolved and not r.ambiguous
    assert r.review_reason


def test_http_cache_prevents_second_request(tmp_path):
    routes = dict(VANILLIN_ROUTES)
    resolver = _resolver(tmp_path, routes)
    resolver.resolve("vanillin")
    # swap the session to one that would fail if actually called — cache should serve it
    resolver.session = FakeSession({})
    r2 = resolver.resolve("vanillin")
    assert r2.resolved and r2.inchikey == "MWOOGOJBHIARFG-UHFFFAOYSA-N"
