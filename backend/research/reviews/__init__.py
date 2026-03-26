"""
Novara Research Foundation: Reviews & Reputation Module

2-call Perplexity pipeline:
  Call 1 (Discovery): Find all review platforms
  Call 2 (Analysis): Extract themes, quotes, trust signals
"""

from .schema import (
    ReviewsSnapshot,
    ReviewsDelta,
    ReviewsAudit,
    ReviewsInputs,
    ReviewPlatform,
    StrengthTheme,
    WeaknessTheme,
    SocialProofSnippet,
    CompetitorReputation,
    ReviewsSource,
    ReviewsRunResponse,
    ReviewsLatestResponse,
)

from .service import ReviewsService

__all__ = [
    # Schema
    "ReviewsSnapshot",
    "ReviewsDelta",
    "ReviewsAudit",
    "ReviewsInputs",
    "ReviewPlatform",
    "StrengthTheme",
    "WeaknessTheme",
    "SocialProofSnippet",
    "CompetitorReputation",
    "ReviewsSource",
    "ReviewsRunResponse",
    "ReviewsLatestResponse",
    # Service
    "ReviewsService",
]
