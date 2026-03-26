"""
Novara Research Foundation: Social Trends — Budget Controls
Version 1.0 - Feb 2026

Hard caps per run to control Shofo API costs.
"""


# ============== PER-RUN CAPS ==============

MAX_RAW_RECORDS_TOTAL = 1200  # across both platforms + both lenses

# Brand + Competitors lens
MAX_PER_HANDLE = 30  # max posts fetched per IG/TikTok handle

# Category lens
MAX_PER_HASHTAG_IG = 40  # max posts per Instagram hashtag query
MAX_PER_HASHTAG_TT = 40  # max posts per TikTok hashtag/SQL query
MAX_PER_SQL_QUERY = 100  # max rows per smart SQL query

# Profile scraping
MAX_PROFILES_TOTAL = 12  # max profile lookups (brand + competitors)

# Final shortlist
SHORTLIST_MIN_PER_PLATFORM = 30
SHORTLIST_MAX_PER_PLATFORM = 60

# Query counts
MAX_IG_HASHTAGS = 10  # max hashtag queries for IG category lens
MAX_TT_KEYWORDS = 8  # max keyword/hashtag queries for TikTok category lens (reduced for speed)
MAX_SQL_QUERIES = 4  # max smart SQL queries for TikTok category lens

# Cost per record (base, no add-ons)
COST_PER_RECORD = 0.0005
COST_PER_PROFILE = 0.001

# Transcript/Comments (OFF by default)
INCLUDE_TRANSCRIPT = False
INCLUDE_COMMENTS = False


class BudgetTracker:
    """Track records fetched per run and enforce caps."""

    def __init__(self):
        self.total_records = 0
        self.by_source: dict = {}  # source_query -> count
        self.profile_lookups = 0
        self.request_ids: list = []

    @property
    def remaining(self) -> int:
        return max(0, MAX_RAW_RECORDS_TOTAL - self.total_records)

    @property
    def cost_estimate(self) -> float:
        return (self.total_records * COST_PER_RECORD) + (self.profile_lookups * COST_PER_PROFILE)

    def can_fetch(self, count: int) -> bool:
        return self.total_records + count <= MAX_RAW_RECORDS_TOTAL

    def record_fetch(self, source_query: str, count: int, request_id: str = ""):
        self.total_records += count
        self.by_source[source_query] = self.by_source.get(source_query, 0) + count
        if request_id:
            self.request_ids.append(request_id)

    def record_profile(self, request_id: str = ""):
        self.profile_lookups += 1
        if request_id:
            self.request_ids.append(request_id)

    def cap_for_source(self, source_type: str) -> int:
        """Return the max records to request for a given source type."""
        if source_type == "ig_handle":
            return min(MAX_PER_HANDLE, self.remaining)
        elif source_type == "tt_handle":
            return min(MAX_PER_HANDLE, self.remaining)
        elif source_type == "ig_hashtag":
            return min(MAX_PER_HASHTAG_IG, self.remaining)
        elif source_type == "tt_keyword":
            return min(MAX_PER_HASHTAG_TT, self.remaining)
        elif source_type == "tt_sql":
            return min(MAX_PER_SQL_QUERY, self.remaining)
        return min(40, self.remaining)

    def summary(self) -> dict:
        return {
            "total_records": self.total_records,
            "by_source_query_counts": self.by_source,
            "profile_lookups": self.profile_lookups,
            "cost_estimate": round(self.cost_estimate, 4),
            "request_ids": self.request_ids[:20],
            "budget_remaining": self.remaining,
        }
