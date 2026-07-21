"""moldedup — molecular name → canonical-molecule deduplication pipeline.

Canonical identity is the **Standard InChIKey**. Every incoming name is resolved
(via a pluggable resolver — PubChem PUG REST by default), reduced to its Standard
InChIKey, and either attached to the existing molecule or used to create a new one.

Public surface:
    from moldedup import IngestionPipeline, build_session_factory, init_db, Config
"""
from .config import Config
from .db import build_engine, build_session_factory, init_db
from .models import Base, Molecule, Synonym, ExternalIdentifier, Source
from .pipeline import IngestionPipeline, IngestOutcome
from .resolvers.base import Resolver, ResolutionResult

__all__ = [
    "Config",
    "build_engine", "build_session_factory", "init_db",
    "Base", "Molecule", "Synonym", "ExternalIdentifier", "Source",
    "IngestionPipeline", "IngestOutcome",
    "Resolver", "ResolutionResult",
]

__version__ = "1.0.0"
