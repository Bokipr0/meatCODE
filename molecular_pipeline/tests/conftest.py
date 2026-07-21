"""Shared test fixtures: an in-memory SQLite DB and a deterministic fake resolver
(so the pipeline is tested without touching the network)."""
import copy

import pytest

from moldedup.db import build_engine, build_session_factory, init_db
from moldedup.resolvers.base import ResolutionResult, Resolver
from moldedup.normalize import normalize_name


@pytest.fixture
def session_factory():
    engine = build_engine("sqlite:///:memory:")
    init_db(engine)
    return build_session_factory(engine)


# Two names for the SAME molecule (vanillin) + a distinct one, an ambiguous one,
# and an unknown one.
_VANILLIN = ResolutionResult(
    query="vanillin", resolved=True,
    inchikey="MWOOGOJBHIARFG-UHFFFAOYSA-N", inchi="InChI=1S/C8H8O3/c1-11-8-4-6(5-9)2-3-7(8)10/h2-5,10H,1H3",
    cid=1183, canonical_smiles="COC1=CC(=CC=C1O)C=O", isomeric_smiles="COC1=CC(=CC=C1O)C=O",
    cas="121-33-5", formula="C8H8O3", molecular_weight=152.15, iupac_name="4-hydroxy-3-methoxybenzaldehyde",
    synonyms=["Vanillin", "121-33-5", "4-Hydroxy-3-methoxybenzaldehyde", "CHEBI:18346"],
    source_name="fake",
)
_VANILLIN.external_ids = {"CID": ["1183"], "CAS": ["121-33-5"], "ChEBI": ["CHEBI:18346"]}

_FURANEOL = ResolutionResult(
    query="furaneol", resolved=True, inchikey="RKHKNZALDBTRHM-UHFFFAOYSA-N",
    cid=19309, formula="C6H8O3", molecular_weight=128.13, cas="3658-77-3",
    iupac_name="4-hydroxy-2,5-dimethylfuran-3(2H)-one",
    synonyms=["Furaneol", "3658-77-3"], source_name="fake",
)
_FURANEOL.external_ids = {"CID": ["19309"], "CAS": ["3658-77-3"]}

_TABLE = {
    normalize_name("vanillin"): _VANILLIN,
    normalize_name("4-hydroxy-3-methoxybenzaldehyde"): _VANILLIN,
    # an alias for vanillin that is NOT in _VANILLIN.synonyms → exercises the "attach" path
    normalize_name("aliasx"): _VANILLIN,
    normalize_name("furaneol"): _FURANEOL,
}


class FakeResolver(Resolver):
    name = "fake"

    def resolve(self, name):
        key = normalize_name(name)
        if key in _TABLE:
            return copy.deepcopy(_TABLE[key])
        if key == normalize_name("ambiguous name"):
            return ResolutionResult(query=name, ambiguous=True,
                                    review_reason="maps to 2 CIDs", source_name=self.name)
        return ResolutionResult(query=name, resolved=False,
                                review_reason="no match", source_name=self.name)


@pytest.fixture
def resolver():
    return FakeResolver()
