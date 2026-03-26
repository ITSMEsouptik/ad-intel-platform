"""
Novara Research Foundation: Customer Intel Module
Version 1.1 - Feb 2026

Lean, high-signal customer intelligence:
- Max 3 SegmentCards grounded in offers + search phrases
- TriggerMap + LanguageBank
- No personas, decision speed, or CTA-per-trigger
"""

from .service import CustomerIntelService
from .schema import (
    CustomerIntelSnapshot,
    SegmentCard,
    TriggerMap,
    LanguageBank,
    CustomerIntelAudit,
    CustomerIntelDelta,
    CustomerIntelSource,
)
from .postprocess import postprocess_customer_intel

__all__ = [
    "CustomerIntelService",
    "CustomerIntelSnapshot",
    "SegmentCard",
    "TriggerMap",
    "LanguageBank",
    "CustomerIntelAudit",
    "CustomerIntelDelta",
    "CustomerIntelSource",
    "postprocess_customer_intel",
]
