"""SQLAlchemy ORM models — the normalized deduplication schema.

    Molecule            one row per unique Standard InChIKey (the canonical identity)
    Synonym             many names → one molecule (or none, when unresolved/ambiguous)
    ExternalIdentifier  CAS / CID / ChEBI / HMDB / KEGG / … per molecule
    Source              provenance for every synonym / external id

Design rule: molecule identity is the Standard InChIKey — never CAS, CID or a name.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, Integer, Float, String, Text, DateTime, ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Synonym resolution states.
STATUS_RESOLVED = "resolved"      # mapped to a molecule
STATUS_UNRESOLVED = "unresolved"  # no resolver match → manual review
STATUS_AMBIGUOUS = "ambiguous"    # resolver returned >1 candidate → manual review


class Molecule(Base):
    """One unique chemical entity, keyed by its Standard InChIKey."""
    __tablename__ = "molecules"

    id = Column(Integer, primary_key=True)
    # Canonical identity. 27-char Standard InChIKey, e.g. "MWOOGOJBHIARFG-UHFFFAOYSA-N".
    inchikey = Column(String(27), nullable=False, unique=True, index=True)
    inchi = Column(Text)                       # Standard InChI
    cid = Column(Integer, index=True)          # PubChem CID (an identifier, NOT the primary key)
    canonical_smiles = Column(Text)
    isomeric_smiles = Column(Text)
    formula = Column(String(255))
    molecular_weight = Column(Float)
    iupac_name = Column(Text)
    preferred_name = Column(Text)              # human-facing preferred label
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    synonyms = relationship("Synonym", back_populates="molecule", cascade="all, delete-orphan")
    external_ids = relationship("ExternalIdentifier", back_populates="molecule", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Molecule {self.inchikey} cid={self.cid} name={self.preferred_name!r}>"


class Source(Base):
    """Where a synonym / identifier came from (an import batch, a resolver, manual entry)."""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)  # e.g. "import:molecules.csv" or "pubchem"
    kind = Column(String(30), default="import")              # import | resolver | manual
    detail = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Source {self.name} ({self.kind})>"


class Synonym(Base):
    """A name that refers to a molecule. `normalized_name` is globally unique — it is
    the key used to answer 'have we seen this name before?'."""
    __tablename__ = "synonyms"

    id = Column(Integer, primary_key=True)
    molecule_id = Column(Integer, ForeignKey("molecules.id"), nullable=True, index=True)
    name = Column(Text, nullable=False)                          # original, as supplied
    normalized_name = Column(String(500), nullable=False, unique=True, index=True)
    status = Column(String(20), default=STATUS_RESOLVED, index=True)
    review_reason = Column(Text)                                 # why it needs manual review
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    molecule = relationship("Molecule", back_populates="synonyms")
    source = relationship("Source")

    def __repr__(self) -> str:
        return f"<Synonym {self.name!r} → mol={self.molecule_id} [{self.status}]>"


class ExternalIdentifier(Base):
    """A cross-reference identifier for a molecule (CAS, CID, ChEBI, HMDB, KEGG, …)."""
    __tablename__ = "external_identifiers"

    id = Column(Integer, primary_key=True)
    molecule_id = Column(Integer, ForeignKey("molecules.id"), nullable=False, index=True)
    scheme = Column(String(40), nullable=False)   # CAS | CID | ChEBI | HMDB | KEGG | ...
    value = Column(String(255), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    molecule = relationship("Molecule", back_populates="external_ids")
    source = relationship("Source")

    __table_args__ = (
        UniqueConstraint("molecule_id", "scheme", "value", name="uq_external_identifier"),
        Index("ix_external_scheme_value", "scheme", "value"),
    )

    def __repr__(self) -> str:
        return f"<ExternalIdentifier {self.scheme}={self.value} mol={self.molecule_id}>"
