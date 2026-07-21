"""The resolver interface + the result object the pipeline consumes.

Adding a new resolver (ChEBI, HMDB, ChemSpider, KEGG, …) is just: subclass
`Resolver`, implement `resolve(name) -> ResolutionResult`. The pipeline never
imports a concrete resolver — it is injected — so the architecture stays modular.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ResolutionResult:
    """Everything a resolver could learn about a name. Fields are all optional so
    partial resolvers still work; the pipeline only *requires* `inchikey` to dedupe."""
    query: str                                   # the name that was asked about
    resolved: bool = False                       # True if mapped to a single molecule
    ambiguous: bool = False                      # True if the name matched >1 distinct entity
    review_reason: Optional[str] = None          # populated when resolved=False or ambiguous=True

    # canonical identity + properties
    inchikey: Optional[str] = None               # Standard InChIKey (the identity)
    inchi: Optional[str] = None                  # Standard InChI
    cid: Optional[int] = None                    # PubChem CID
    canonical_smiles: Optional[str] = None
    isomeric_smiles: Optional[str] = None
    cas: Optional[str] = None
    formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    iupac_name: Optional[str] = None

    synonyms: List[str] = field(default_factory=list)
    # cross-references, e.g. {"CAS": ["121-33-5"], "ChEBI": ["CHEBI:18346"]}
    external_ids: Dict[str, List[str]] = field(default_factory=dict)

    source_name: str = "unknown"                 # provenance label for what resolved this

    def add_external(self, scheme: str, value: str) -> None:
        if not value:
            return
        self.external_ids.setdefault(scheme, [])
        if value not in self.external_ids[scheme]:
            self.external_ids[scheme].append(value)


class Resolver(abc.ABC):
    """Abstract name→identity resolver."""

    name: str = "base"

    @abc.abstractmethod
    def resolve(self, name: str) -> ResolutionResult:
        """Resolve a single molecule name. Must never raise for a merely-unknown
        name — return ResolutionResult(resolved=False, review_reason=...) instead.
        Network/parse failures may raise; the pipeline treats those as errors."""
        raise NotImplementedError
