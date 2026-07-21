"""Resolvers turn a molecule *name* into a canonical chemical identity.

The pipeline depends only on the `Resolver` interface, so new backends
(ChEBI, HMDB, ChemSpider, KEGG, …) can be added without touching the pipeline.
"""
from .base import Resolver, ResolutionResult

__all__ = ["Resolver", "ResolutionResult"]
