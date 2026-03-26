"""
Novara Research Foundation: Competitor Discovery Module

Provides competitor discovery using Perplexity AI
to identify direct competitors and category search terms.
"""

from .schema import (
    CompetitorSnapshot,
    CompetitorDelta,
    CompetitorInputs,
    CompetitorSource,
    Competitor,
    CompetitorRunResponse,
    CompetitorLatestResponse
)

from .service import CompetitorService

from .perplexity_competitors import call_perplexity_competitors

__all__ = [
    # Schema
    "CompetitorSnapshot",
    "CompetitorDelta",
    "CompetitorInputs",
    "CompetitorSource",
    "Competitor",
    "CompetitorRunResponse",
    "CompetitorLatestResponse",
    
    # Service
    "CompetitorService",
    
    # Perplexity
    "call_perplexity_competitors"
]
