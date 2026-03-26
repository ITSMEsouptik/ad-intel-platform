"""
Novara Research Foundation: Seasonality Module

Provides seasonality analysis ("Buying Moments") using Perplexity AI
to identify specific buying windows, triggers, and audience segments.
"""

from .schema import (
    SeasonalitySnapshot,
    SeasonalityDelta,
    SeasonalityInputs,
    SeasonalityAudit,
    SeasonalitySource,
    BuyingMoment,
    WeeklyPatterns,
    SeasonalityRunResponse,
    SeasonalityLatestResponse
)

from .service import SeasonalityService

from .perplexity_seasonality import call_perplexity_seasonality

from .postprocess import postprocess_moments

__all__ = [
    # Schema
    "SeasonalitySnapshot",
    "SeasonalityDelta",
    "SeasonalityInputs",
    "SeasonalityAudit",
    "SeasonalitySource",
    "BuyingMoment",
    "WeeklyPatterns",
    "SeasonalityRunResponse",
    "SeasonalityLatestResponse",

    # Service
    "SeasonalityService",

    # Perplexity
    "call_perplexity_seasonality",

    # Post-processing
    "postprocess_moments"
]
