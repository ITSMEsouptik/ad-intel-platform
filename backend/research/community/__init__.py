"""
Novara Research Foundation: Community Intelligence Module

2-call Perplexity pipeline:
  Call 1 (Discovery): Find real forum threads
  Call 2 (Synthesis): Extract themes, language bank, audience notes
"""

from .schema import (
    CommunitySnapshot,
    CommunityDelta,
    CommunityAudit,
    CommunityInputs,
    CommunityThread,
    CommunityTheme,
    CommunityLanguageBank,
    CommunitySource,
)

from .service import CommunityService

__all__ = [
    "CommunitySnapshot",
    "CommunityDelta",
    "CommunityAudit",
    "CommunityInputs",
    "CommunityThread",
    "CommunityTheme",
    "CommunityLanguageBank",
    "CommunitySource",
    "CommunityService",
]
