"""Core deduplication behaviour — proven against an in-memory DB + fake resolver."""
from moldedup.models import ExternalIdentifier, Molecule, Source, Synonym
from moldedup.normalize import normalize_name
from moldedup.pipeline import (
    ATTACHED, AMBIGUOUS, CREATED, EXISTS, UNRESOLVED, IngestionPipeline,
)


def _pipe(session_factory, resolver):
    return IngestionPipeline(session_factory, resolver)


def test_new_name_creates_molecule(session_factory, resolver):
    p = _pipe(session_factory, resolver)
    outs = p.ingest_batch(["vanillin"], "test")
    assert outs[0].status == CREATED
    s = session_factory()
    assert s.query(Molecule).count() == 1
    assert s.query(Molecule).one().inchikey == "MWOOGOJBHIARFG-UHFFFAOYSA-N"
    s.close()


def test_alias_attaches_to_same_molecule(session_factory, resolver):
    """Two different names → same InChIKey → ONE molecule, both names attached."""
    p = _pipe(session_factory, resolver)
    outs = p.ingest_batch(["vanillin", "aliasx"], "test")
    assert [o.status for o in outs] == [CREATED, ATTACHED]
    s = session_factory()
    assert s.query(Molecule).count() == 1
    mol = s.query(Molecule).one()
    for name in ("vanillin", "aliasx"):
        syn = s.query(Synonym).filter_by(normalized_name=normalize_name(name)).one()
        assert syn.molecule_id == mol.id and syn.status == "resolved"
    s.close()


def test_second_name_already_a_synonym_dedupes(session_factory, resolver):
    """The 2nd input is one of vanillin's PubChem synonyms → still ONE molecule."""
    p = _pipe(session_factory, resolver)
    p.ingest_batch(["vanillin", "4-hydroxy-3-methoxybenzaldehyde"], "test")
    s = session_factory()
    assert s.query(Molecule).count() == 1
    s.close()


def test_distinct_molecule_gets_its_own_record(session_factory, resolver):
    p = _pipe(session_factory, resolver)
    p.ingest_batch(["vanillin", "furaneol"], "test")
    s = session_factory()
    assert s.query(Molecule).count() == 2
    assert {m.inchikey for m in s.query(Molecule)} == {
        "MWOOGOJBHIARFG-UHFFFAOYSA-N", "RKHKNZALDBTRHM-UHFFFAOYSA-N"}
    s.close()


def test_ambiguous_name_flagged_for_review(session_factory, resolver):
    p = _pipe(session_factory, resolver)
    outs = p.ingest_batch(["ambiguous name"], "test")
    assert outs[0].status == AMBIGUOUS
    s = session_factory()
    assert s.query(Molecule).count() == 0
    syn = s.query(Synonym).filter_by(normalized_name=normalize_name("ambiguous name")).one()
    assert syn.status == "ambiguous" and syn.molecule_id is None and syn.review_reason
    s.close()


def test_unresolved_name_flagged(session_factory, resolver):
    p = _pipe(session_factory, resolver)
    outs = p.ingest_batch(["unobtanium"], "test")
    assert outs[0].status == UNRESOLVED
    s = session_factory()
    syn = s.query(Synonym).filter_by(normalized_name=normalize_name("unobtanium")).one()
    assert syn.status == "unresolved" and syn.molecule_id is None
    s.close()


def test_idempotent_reingest(session_factory, resolver):
    p = _pipe(session_factory, resolver)
    p.ingest_batch(["vanillin"], "batch1")
    outs = p.ingest_batch(["vanillin"], "batch2")
    assert outs[0].status == EXISTS
    s = session_factory()
    assert s.query(Molecule).count() == 1
    s.close()


def test_external_identifiers_and_cas_stored(session_factory, resolver):
    p = _pipe(session_factory, resolver)
    p.ingest_batch(["vanillin"], "test")
    s = session_factory()
    mol = s.query(Molecule).one()
    schemes = {(e.scheme, e.value) for e in mol.external_ids}
    assert ("CID", "1183") in schemes
    assert ("CAS", "121-33-5") in schemes
    assert any(scheme == "ChEBI" for scheme, _ in schemes)
    s.close()


def test_provenance_sources_recorded(session_factory, resolver):
    p = _pipe(session_factory, resolver)
    p.ingest_batch(["vanillin"], "my-import")
    s = session_factory()
    names = {src.name for src in s.query(Source)}
    assert "my-import" in names   # the batch source
    assert "fake" in names        # the resolver source
    s.close()
