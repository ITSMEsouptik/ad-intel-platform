"""
Novara Debug Logger
Captures granular debug information at each step of the pipeline
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import json


class LogLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class StepType(str, Enum):
    STEP1_BRIEF = "STEP1_BRIEF"
    STEP2_CRAWL = "STEP2_CRAWL"
    STEP2_EXTRACT = "STEP2_EXTRACT"
    STEP2_SCORE = "STEP2_SCORE"
    STEP3A_INPUT = "STEP3A_INPUT"
    STEP3A_PROMPT = "STEP3A_PROMPT"
    STEP3A_API = "STEP3A_API"
    STEP3A_PARSE = "STEP3A_PARSE"


@dataclass
class DebugEvent:
    """A single debug event"""
    timestamp: str
    step: str
    substep: str
    level: str
    title: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CampaignDebugLog:
    """Complete debug log for a campaign"""
    campaign_brief_id: str
    website_url: str
    created_at: str
    updated_at: str
    events: List[Dict] = field(default_factory=list)
    summary: Dict = field(default_factory=lambda: {
        "total_events": 0,
        "errors": 0,
        "warnings": 0,
        "current_step": "",
        "status": "running"
    })
    
    def to_dict(self) -> Dict:
        return asdict(self)


class DebugLogger:
    """Debug logger that collects events for a campaign"""
    
    def __init__(self, db, campaign_brief_id: str, website_url: str = ""):
        self.db = db
        self.campaign_brief_id = campaign_brief_id
        self.website_url = website_url
        self.events: List[DebugEvent] = []
        self.start_times: Dict[str, datetime] = {}
    
    async def initialize(self):
        """Create or get existing debug log document"""
        existing = await self.db.debug_logs.find_one(
            {"campaign_brief_id": self.campaign_brief_id}
        )
        
        if not existing:
            log = CampaignDebugLog(
                campaign_brief_id=self.campaign_brief_id,
                website_url=self.website_url,
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat()
            )
            await self.db.debug_logs.insert_one(log.to_dict())
    
    def start_timer(self, key: str):
        """Start a timer for duration tracking"""
        self.start_times[key] = datetime.now(timezone.utc)
    
    def get_duration(self, key: str) -> Optional[int]:
        """Get duration in milliseconds since timer started"""
        if key in self.start_times:
            delta = datetime.now(timezone.utc) - self.start_times[key]
            return int(delta.total_seconds() * 1000)
        return None
    
    async def log(
        self,
        step: str,
        substep: str,
        title: str,
        details: Dict[str, Any] = None,
        level: LogLevel = LogLevel.INFO,
        duration_key: str = None
    ):
        """Log a debug event"""
        duration_ms = None
        if duration_key:
            duration_ms = self.get_duration(duration_key)
        
        event = DebugEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            step=step,
            substep=substep,
            level=level.value,
            title=title,
            details=details or {},
            duration_ms=duration_ms
        )
        
        # Update in database
        await self.db.debug_logs.update_one(
            {"campaign_brief_id": self.campaign_brief_id},
            {
                "$push": {"events": event.to_dict()},
                "$set": {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "summary.current_step": step,
                    "summary.total_events": {"$add": ["$summary.total_events", 1]}
                },
                "$inc": {
                    "summary.total_events": 1,
                    "summary.errors": 1 if level == LogLevel.ERROR else 0,
                    "summary.warnings": 1 if level == LogLevel.WARNING else 0
                }
            }
        )
    
    async def log_step1_brief(self, brief_data: Dict):
        """Log Step 1: Campaign Brief creation"""
        await self.log(
            step="STEP1_BRIEF",
            substep="input",
            title="Raw Form Input",
            details={
                "website_url": brief_data.get("brand", {}).get("website_url"),
                "primary_goal": brief_data.get("goal", {}).get("primary_goal"),
                "success_definition": brief_data.get("goal", {}).get("success_definition"),
                "country": brief_data.get("geo", {}).get("country"),
                "city_or_region": brief_data.get("geo", {}).get("city_or_region"),
                "destination_type": brief_data.get("destination", {}).get("type"),
                "ads_intent": brief_data.get("ads_intent"),
                "budget_range": brief_data.get("budget_range_monthly"),
                "contact_name": brief_data.get("contact", {}).get("name"),
                "contact_email": brief_data.get("contact", {}).get("email")
            },
            level=LogLevel.INFO
        )
        
        await self.log(
            step="STEP1_BRIEF",
            substep="stored",
            title="Brief Stored in Database",
            details={
                "campaign_brief_id": self.campaign_brief_id,
                "track": brief_data.get("track"),
                "created_at": brief_data.get("created_at")
            },
            level=LogLevel.SUCCESS
        )
    
    async def log_crawl_start(self, url: str, max_pages: int):
        """Log crawl initialization"""
        self.start_timer("crawl")
        await self.log(
            step="STEP2_CRAWL",
            substep="init",
            title="Crawl Initialization",
            details={
                "input_url": url,
                "max_pages": max_pages,
                "timeout_per_page": "30s"
            },
            level=LogLevel.INFO
        )
    
    async def log_page_fetch(self, url: str, status: int, method: str, 
                             response_time: float, page_type: str, 
                             redirected_to: str = None):
        """Log individual page fetch"""
        await self.log(
            step="STEP2_CRAWL",
            substep="page_fetch",
            title=f"Fetched: {url.split('/')[-1] or 'homepage'}",
            details={
                "url": url,
                "status": status,
                "method": method,
                "response_time_s": round(response_time, 2),
                "page_type": page_type,
                "redirected_to": redirected_to
            },
            level=LogLevel.SUCCESS if status == 200 else LogLevel.WARNING
        )
    
    async def log_link_discovery(self, total_links: int, internal_links: int,
                                  priority_scores: List[Dict]):
        """Log link discovery and prioritization"""
        await self.log(
            step="STEP2_CRAWL",
            substep="link_discovery",
            title="Link Discovery & Prioritization",
            details={
                "total_links_found": total_links,
                "internal_links": internal_links,
                "external_links_skipped": total_links - internal_links,
                "priority_scores": priority_scores[:10]  # Top 10
            },
            level=LogLevel.INFO
        )
    
    async def log_crawl_complete(self, pages_attempted: int, pages_fetched: int,
                                  pages_failed: int, errors: List[str]):
        """Log crawl completion summary"""
        await self.log(
            step="STEP2_CRAWL",
            substep="complete",
            title="Crawl Complete",
            details={
                "pages_attempted": pages_attempted,
                "pages_fetched": pages_fetched,
                "pages_failed": pages_failed,
                "errors": errors
            },
            level=LogLevel.SUCCESS if pages_failed == 0 else LogLevel.WARNING,
            duration_key="crawl"
        )
    
    async def log_social_extraction(self, patterns_checked: List[str], 
                                     results: Dict[str, str]):
        """Log social link extraction"""
        await self.log(
            step="STEP2_EXTRACT",
            substep="social_links",
            title="Social Link Extraction",
            details={
                "patterns_checked": patterns_checked,
                "found": results,
                "platforms_found": len(results)
            },
            level=LogLevel.SUCCESS if results else LogLevel.WARNING
        )
    
    async def log_field_extraction(self, field_name: str, sources_tried: List[Dict],
                                    selected_value: Any, validation: Dict = None):
        """Log individual field extraction"""
        await self.log(
            step="STEP2_EXTRACT",
            substep=f"field_{field_name}",
            title=f"Extracted: {field_name}",
            details={
                "sources_tried": sources_tried,
                "selected_value": selected_value if not isinstance(selected_value, list) 
                                  else f"{len(selected_value)} items",
                "validation": validation
            },
            level=LogLevel.SUCCESS if selected_value else LogLevel.WARNING
        )
    
    async def log_email_extraction(self, raw_matches: List[str], 
                                    filtered_out: List[Dict],
                                    final_emails: List[str]):
        """Log email extraction with filtering details"""
        await self.log(
            step="STEP2_EXTRACT",
            substep="emails",
            title="Email Extraction",
            details={
                "raw_matches_found": len(raw_matches),
                "raw_matches": raw_matches[:10],
                "filtered_out": filtered_out[:5],
                "final_valid_emails": final_emails
            },
            level=LogLevel.SUCCESS if final_emails else LogLevel.WARNING
        )
    
    async def log_confidence_scoring(self, field_scores: Dict[str, Dict],
                                      total_score: int, threshold: int,
                                      needs_questions: bool):
        """Log confidence scoring breakdown"""
        await self.log(
            step="STEP2_SCORE",
            substep="calculate",
            title="Confidence Score Calculation",
            details={
                "field_scores": field_scores,
                "total_score": total_score,
                "threshold": threshold,
                "passed_threshold": total_score >= threshold,
                "needs_micro_questions": needs_questions
            },
            level=LogLevel.SUCCESS if total_score >= threshold else LogLevel.WARNING
        )
    
    async def log_step2_complete(self, pack_id: str, status: str, confidence: int):
        """Log Step 2 completion"""
        self.start_timer("step2")
        await self.log(
            step="STEP2_EXTRACT",
            substep="complete",
            title="Website Context Pack Complete",
            details={
                "pack_id": pack_id,
                "status": status,
                "confidence_score": confidence
            },
            level=LogLevel.SUCCESS,
            duration_key="step2"
        )
    
    async def log_step3a_input(self, brief_data: Dict, pack_data: Dict):
        """Log Step 3A input gathering"""
        self.start_timer("step3a")
        await self.log(
            step="STEP3A_INPUT",
            substep="gather",
            title="Input Data Gathered",
            details={
                "from_brief": {
                    "website_url": brief_data.get("brand", {}).get("website_url"),
                    "geo": f"{brief_data.get('geo', {}).get('country')}, {brief_data.get('geo', {}).get('city_or_region')}",
                    "goal": brief_data.get("goal", {}).get("primary_goal"),
                    "budget": brief_data.get("budget_range_monthly")
                },
                "from_pack": {
                    "brand_name": pack_data.get("brand_identity", {}).get("brand_name"),
                    "offer_type": pack_data.get("offer", {}).get("offer_type_hint"),
                    "benefits_count": len(pack_data.get("offer", {}).get("key_benefits", [])),
                    "ctas_count": len(pack_data.get("conversion", {}).get("detected_primary_ctas", [])),
                    "social_platforms": list(pack_data.get("site", {}).get("social_links", {}).keys()),
                    "confidence": pack_data.get("quality", {}).get("confidence_score_0_100")
                }
            },
            level=LogLevel.INFO
        )
    
    async def log_step3a_prompt(self, system_prompt: str, user_prompt: str,
                                 schema_fields: int):
        """Log prompt construction"""
        await self.log(
            step="STEP3A_PROMPT",
            substep="build",
            title="Prompt Constructed",
            details={
                "system_prompt_chars": len(system_prompt),
                "system_prompt_preview": system_prompt[:200] + "...",
                "user_prompt_chars": len(user_prompt),
                "user_prompt_full": user_prompt,
                "schema_fields": schema_fields
            },
            level=LogLevel.INFO
        )
    
    async def log_step3a_api_call(self, model: str, temperature: float, 
                                   max_tokens: int):
        """Log API call start"""
        self.start_timer("perplexity_api")
        await self.log(
            step="STEP3A_API",
            substep="request",
            title="Calling Perplexity API",
            details={
                "endpoint": "https://api.perplexity.ai/chat/completions",
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            level=LogLevel.INFO
        )
    
    async def log_step3a_api_response(self, status: int, prompt_tokens: int,
                                       completion_tokens: int, citations: int):
        """Log API response"""
        await self.log(
            step="STEP3A_API",
            substep="response",
            title="API Response Received",
            details={
                "status": status,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "citations_count": citations
            },
            level=LogLevel.SUCCESS if status == 200 else LogLevel.ERROR,
            duration_key="perplexity_api"
        )
    
    async def log_step3a_parse(self, parsed_data: Dict):
        """Log response parsing"""
        await self.log(
            step="STEP3A_PARSE",
            substep="extract",
            title="Response Parsed",
            details={
                "category": parsed_data.get("category", {}),
                "competitors_count": len(parsed_data.get("competitors", [])),
                "competitors": [c.get("name") for c in parsed_data.get("competitors", [])],
                "icp_segments_count": len(parsed_data.get("customer_psychology", {}).get("icp_segments", [])),
                "pains_count": len(parsed_data.get("customer_psychology", {}).get("top_pains", [])),
                "voice_traits": parsed_data.get("brand_audit_lite", {}).get("voice", {}).get("traits", []),
                "archetype": parsed_data.get("brand_audit_lite", {}).get("archetype", {}).get("primary"),
                "ui_cards_count": len(parsed_data.get("ui_summary", {}).get("cards", [])),
                "sources_count": len(parsed_data.get("sources", []))
            },
            level=LogLevel.SUCCESS
        )
    
    async def log_step3a_complete(self, intel_pack_id: str, status: str):
        """Log Step 3A completion"""
        await self.log(
            step="STEP3A_PARSE",
            substep="complete",
            title="Intel Pack Complete",
            details={
                "intel_pack_id": intel_pack_id,
                "status": status
            },
            level=LogLevel.SUCCESS,
            duration_key="step3a"
        )
    
    async def log_error(self, step: str, error_message: str, details: Dict = None):
        """Log an error"""
        await self.log(
            step=step,
            substep="error",
            title=f"Error: {error_message[:50]}",
            details={
                "error_message": error_message,
                **(details or {})
            },
            level=LogLevel.ERROR
        )
    
    async def set_status(self, status: str):
        """Set the overall status"""
        await self.db.debug_logs.update_one(
            {"campaign_brief_id": self.campaign_brief_id},
            {"$set": {"summary.status": status}}
        )
