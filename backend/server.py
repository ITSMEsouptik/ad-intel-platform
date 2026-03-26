from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import httpx
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== ENUMS ==============

class GoalType(str, Enum):
    SALES_ORDERS = "sales_orders"
    BOOKINGS_LEADS = "bookings_leads"
    BRAND_AWARENESS = "brand_awareness"
    EVENT_LAUNCH = "event_launch"

class DestinationType(str, Enum):
    WEBSITE = "website"
    WHATSAPP = "whatsapp"
    BOOKING_LINK = "booking_link"
    APP = "app"
    DM = "dm"
    OTHER = "other"

class AdsIntent(str, Enum):
    YES = "yes"
    NOT_YET = "not_yet"
    UNSURE = "unsure"

class BudgetRange(str, Enum):
    UNDER_300 = "<300"
    RANGE_300_1000 = "300-1000"
    RANGE_1000_5000 = "1000-5000"
    OVER_5000 = "5000+"
    NOT_SURE = "not_sure"

class Track(str, Enum):
    PILOT = "pilot"
    FOUNDATION = "foundation"

# ============== MODELS ==============

# Contact info
class Contact(BaseModel):
    name: str = ""
    email: str = ""

# Brand info
class Brand(BaseModel):
    website_url: str

# Goal info
class Goal(BaseModel):
    primary_goal: GoalType
    success_definition: str = Field(..., max_length=120)

# Geo info
class Geo(BaseModel):
    country: str
    city_or_region: str

# Destination info
class Destination(BaseModel):
    type: DestinationType

# Campaign Brief Create (input from wizard - minimal)
class CampaignBriefCreate(BaseModel):
    website_url: str
    country: str
    # Optional fields - can be filled later during BuildingPack
    city_or_region: Optional[str] = ""
    primary_goal: Optional[GoalType] = None
    success_definition: Optional[str] = Field(default="", max_length=120)
    destination_type: Optional[DestinationType] = None
    ads_intent: Optional[AdsIntent] = None
    budget_range_monthly: Optional[BudgetRange] = None
    name: Optional[str] = ""
    email: Optional[str] = ""

# Campaign Brief (full document)
class CampaignBrief(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    campaign_brief_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    track: Track
    user_id: Optional[str] = None  # Linked after auth
    contact: Contact
    brand: Brand
    goal: Goal
    geo: Geo
    destination: Destination
    ads_intent: AdsIntent
    budget_range_monthly: BudgetRange
    raw_intake: dict

# User model (for auth)
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============== HELPER FUNCTIONS ==============

def compute_track(ads_intent: AdsIntent) -> Track:
    """Compute track based on routing rules"""
    if ads_intent == AdsIntent.YES:
        return Track.PILOT
    elif ads_intent == AdsIntent.NOT_YET:
        return Track.FOUNDATION
    else:  # UNSURE - default to pilot
        return Track.PILOT

async def get_current_user(request: Request) -> Optional[User]:
    """Extract user from session token cookie or Authorization header"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        return None
    
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        return None
    
    # Check expiry with timezone awareness
    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    
    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        return None
    
    return User(**user_doc)

# ============== AUTH ROUTES ==============

@api_router.post("/auth/session")
async def exchange_session(request: Request, response: Response):
    """Exchange session_id for session_token and set httpOnly cookie"""
    # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # Exchange session_id with Emergent Auth
    async with httpx.AsyncClient() as http_client:
        try:
            auth_response = await http_client.get(
                os.environ.get("AUTH_SESSION_EXCHANGE_URL", "https://your-auth-provider.com/auth/session-data"),
                headers={"X-Session-ID": session_id}
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            auth_data = auth_response.json()
        except Exception as e:
            logger.error(f"Auth exchange error: {e}")
            raise HTTPException(status_code=401, detail="Auth exchange failed")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    session_token = auth_data.get("session_token")
    email = auth_data.get("email")
    name = auth_data.get("name")
    picture = auth_data.get("picture")
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}}
        )
    else:
        # Create new user
        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc)
    
    # Create session
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture
    }

@api_router.get("/auth/me")
async def get_me(request: Request):
    """Get current authenticated user"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture
    }

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout and clear session"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=True,
        samesite="none"
    )
    
    return {"message": "Logged out"}

# ============== CAMPAIGN BRIEF ROUTES ==============

@api_router.post("/campaign-briefs", response_model=CampaignBrief)
async def create_campaign_brief(brief_input: CampaignBriefCreate, request: Request):
    """Create a new campaign brief (anonymous or authenticated)"""
    
    # Compute track based on ads_intent (default to pilot)
    track = compute_track(brief_input.ads_intent) if brief_input.ads_intent else Track.PILOT
    
    # Get current user if authenticated
    user = await get_current_user(request)
    
    # Normalize website URL - add https:// if missing
    website_url = brief_input.website_url.strip()
    if not website_url.startswith(('http://', 'https://')):
        website_url = f'https://{website_url}'
    
    # Auto-fill contact from authenticated user
    contact_name = brief_input.name or (user.name if user else "")
    contact_email = brief_input.email or (user.email if user else "")
    
    # Build the canonical CampaignBrief
    brief = CampaignBrief(
        track=track,
        user_id=user.user_id if user else None,
        contact=Contact(name=contact_name, email=contact_email),
        brand=Brand(website_url=website_url),
        goal=Goal(
            primary_goal=brief_input.primary_goal or GoalType.BOOKINGS_LEADS,
            success_definition=brief_input.success_definition or ""
        ),
        geo=Geo(
            country=brief_input.country,
            city_or_region=brief_input.city_or_region or ""
        ),
        destination=Destination(
            type=brief_input.destination_type or DestinationType.WEBSITE
        ),
        ads_intent=brief_input.ads_intent or AdsIntent.YES,
        budget_range_monthly=brief_input.budget_range_monthly or BudgetRange.NOT_SURE,
        raw_intake=brief_input.model_dump()
    )
    
    # Convert to dict for MongoDB
    doc = brief.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.campaign_briefs.insert_one(doc)
    
    return brief

@api_router.get("/campaign-briefs/{campaign_brief_id}")
async def get_campaign_brief(campaign_brief_id: str):
    """Get a campaign brief by ID"""
    
    doc = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    if not doc:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    return doc


class CampaignBriefUpdate(BaseModel):
    """Partial update for campaign brief - used during BuildingPack"""
    city_or_region: Optional[str] = None
    primary_goal: Optional[GoalType] = None
    success_definition: Optional[str] = None
    destination_type: Optional[DestinationType] = None

@api_router.patch("/campaign-briefs/{campaign_brief_id}")
async def update_campaign_brief(campaign_brief_id: str, update: CampaignBriefUpdate):
    """Update optional fields on a campaign brief (during build)"""
    updates = {}
    if update.city_or_region is not None:
        updates["geo.city_or_region"] = update.city_or_region
    if update.primary_goal is not None:
        updates["goal.primary_goal"] = update.primary_goal.value
    if update.success_definition is not None:
        updates["goal.success_definition"] = update.success_definition
    if update.destination_type is not None:
        updates["destination.type"] = update.destination_type.value

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.campaign_briefs.update_one(
        {"campaign_brief_id": campaign_brief_id},
        {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    return {"status": "updated"}

@api_router.get("/campaign-briefs")
async def list_campaign_briefs(request: Request):
    """List campaign briefs for authenticated user, enriched with pack status"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    cursor = db.campaign_briefs.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1)
    
    briefs = await cursor.to_list(100)
    
    # Enrich with pack status for each brief
    brief_ids = [b["campaign_brief_id"] for b in briefs]
    if brief_ids:
        packs_cursor = db.website_context_packs.find(
            {"campaign_brief_id": {"$in": brief_ids}},
            {"_id": 0, "campaign_brief_id": 1, "status": 1, "step2.brand_summary.name": 1}
        )
        packs = await packs_cursor.to_list(100)
        pack_map = {p["campaign_brief_id"]: p for p in packs}
        
        for brief in briefs:
            bid = brief["campaign_brief_id"]
            pack = pack_map.get(bid)
            if pack:
                raw_status = pack.get("status") or "processing"
                # Normalize 'running' to 'processing' for frontend consistency
                brief["pack_status"] = "processing" if raw_status == "running" else raw_status
                brief["brand_name"] = pack.get("step2", {}).get("brand_summary", {}).get("name")
            else:
                brief["pack_status"] = "none"
                brief["brand_name"] = None
    
    return briefs

@api_router.post("/campaign-briefs/link")
async def link_briefs_to_user(request: Request):
    """Link anonymous campaign briefs to authenticated user by email"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find briefs with matching email but no user_id
    result = await db.campaign_briefs.update_many(
        {
            "contact.email": user.email,
            "user_id": None
        },
        {
            "$set": {
                "user_id": user.user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"linked_count": result.modified_count}

# ============== HEALTH CHECK ==============

@api_router.get("/")
async def root():
    return {"message": "Novara API", "status": "healthy"}


# ============== STEP 2: ORCHESTRATION & WEBSITE CONTEXT ==============

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    NEEDS_USER_INPUT = "needs_user_input"
    COMPLETED = "completed"
    FAILED = "failed"

class MicroInputSubmit(BaseModel):
    primary_offer_summary: Optional[str] = None
    primary_action: Optional[str] = None
    primary_action_text: Optional[str] = None
    trust_signal: Optional[str] = None
    trust_signal_text: Optional[str] = None


@api_router.post("/orchestrations/{campaign_brief_id}/start")
async def start_orchestration(campaign_brief_id: str):
    """Start orchestration for a campaign brief (triggers Step 2)"""
    
    # Verify brief exists
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    # Check if orchestration already exists
    existing = await db.orchestration_runs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if existing:
        return existing
    
    # Create orchestration run
    orchestration_id = str(uuid.uuid4())
    orchestration_doc = {
        "orchestration_id": orchestration_id,
        "campaign_brief_id": campaign_brief_id,
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.orchestration_runs.insert_one(orchestration_doc)
    
    # Create Step 2 run
    step2_run_id = str(uuid.uuid4())
    step2_doc = {
        "step_run_id": step2_run_id,
        "orchestration_id": orchestration_id,
        "campaign_brief_id": campaign_brief_id,
        "step_key": "STEP2_WEBSITE_CONTEXT",
        "status": "pending",
        "progress": {
            "events": []
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.step_runs.insert_one(step2_doc)
    
    # Create placeholder website context pack
    pack_id = str(uuid.uuid4())
    pack_doc = {
        "website_context_pack_id": pack_id,
        "campaign_brief_id": campaign_brief_id,
        "status": "running",
        "confidence_score": 0,
        "data": None,
        "questions": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.website_context_packs.insert_one(pack_doc)
    
    # Start Step 2 in background
    import asyncio
    asyncio.create_task(run_step2(campaign_brief_id, pack_id, step2_run_id))
    
    return {
        "orchestration_id": orchestration_id,
        "campaign_brief_id": campaign_brief_id,
        "website_context_pack_id": pack_id,
        "status": "running"
    }








async def run_step2(campaign_brief_id: str, pack_id: str, step_run_id: str):
    """Orchestrates the Step 2 website context extraction pipeline.

    Calls pure data-processing stages from step2_pipeline.py,
    handles DB writes, event firing, and error recovery.
    """
    website_url = ""
    try:
        from step2_pipeline import (
            stage_crawl, stage_extract_raw, stage_enrich_with_jina,
            stage_extract_spa_services,
            stage_extract_brand_identity, stage_extract_assets,
            stage_parse_pricing, stage_extract_channels,
            stage_llm_summarize, stage_build_output,
        )

        logger.info(f"[STEP2] Starting extraction for brief={campaign_brief_id}")

        brief = await db.campaign_briefs.find_one(
            {"campaign_brief_id": campaign_brief_id}, {"_id": 0}
        )
        website_url = brief["brand"]["website_url"]
        logger.info(f"[STEP2] Target: {website_url}")
        await update_step_event(step_run_id, "STEP2_STARTED")

        # Stage 1: Crawl
        await update_step_event(step_run_id, "CRAWL_START")
        crawl_result = await stage_crawl(website_url)
        await update_step_event(step_run_id, "CRAWL_DONE", {
            "pages_fetched": crawl_result.pages_fetched,
            "fetch_method": crawl_result.fetch_method
        })

        # Save screenshot early
        if crawl_result.screenshot_base64:
            await db.website_context_packs.update_one(
                {"website_context_pack_id": pack_id},
                {"$set": {"screenshot": crawl_result.screenshot_base64}}
            )

        # Stage 2: Extract raw text
        await update_step_event(step_run_id, "EXTRACT_TEXT_START")
        raw_extraction = stage_extract_raw(crawl_result)
        await update_step_event(step_run_id, "EXTRACT_TEXT_DONE")

        # Stage 2A: Jina enrichment for JS-heavy SPAs with sparse crawl results
        raw_extraction = await stage_enrich_with_jina(raw_extraction, crawl_result, website_url)

        # Stage 2B: SPA service extraction (Playwright → Jina fallback)
        await update_step_event(step_run_id, "SPA_SERVICES_START")
        spa_services = await stage_extract_spa_services(crawl_result, raw_extraction)
        if spa_services:
            await update_step_event(step_run_id, "SPA_SERVICES_DONE", {
                "services_count": spa_services["services_count"],
                "categories": spa_services["categories"],
                "method": spa_services["method"],
            })

        # Stage 3+4+5: Brand identity, Assets, Pricing (all sync, run together)
        await update_step_event(step_run_id, "EXTRACT_IDENTITY_START")
        brand_identity = stage_extract_brand_identity(crawl_result)
        assets = stage_extract_assets(crawl_result)
        pricing = stage_parse_pricing(raw_extraction)
        await update_step_event(step_run_id, "EXTRACT_IDENTITY_DONE", {
            "fonts_count": len(brand_identity.get('fonts', [])),
            "colors_count": len(brand_identity.get('colors', []))
        })

        # Stage 5B+6: Channels + LLM run IN PARALLEL (independent of each other)
        await update_step_event(step_run_id, "LLM_SUMMARIZE_START")
        channels_task = asyncio.create_task(
            stage_extract_channels(crawl_result, raw_extraction, website_url)
        )
        llm_task = asyncio.create_task(
            stage_llm_summarize(raw_extraction, pricing)
        )
        channels, (llm_output, llm_metadata) = await asyncio.gather(
            channels_task, llm_task
        )

        if llm_output:
            await update_step_event(step_run_id, "LLM_SUMMARIZE_DONE", {
                "model": llm_metadata.get('model') if llm_metadata else '',
                "duration_seconds": llm_metadata.get('response_duration_seconds') if llm_metadata else 0
            })
        else:
            await update_step_event(step_run_id, "LLM_SUMMARIZE_FAILED")

        # Stage 7: Build final output
        await update_step_event(step_run_id, "FINALIZE_START")
        step2_data, step2_internal, confidence, status = stage_build_output(
            website_url=website_url,
            crawl_result=crawl_result,
            raw_extraction=raw_extraction,
            brand_identity=brand_identity,
            assets=assets,
            pricing=pricing,
            channels=channels,
            llm_output=llm_output,
            llm_metadata=llm_metadata,
            spa_services=spa_services,
        )

        # Save to DB
        await db.website_context_packs.update_one(
            {"website_context_pack_id": pack_id},
            {"$set": {
                "status": status,
                "confidence_score": confidence,
                "step2": step2_data,
                "step2_internal": step2_internal,
                "screenshot": crawl_result.screenshot_base64,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        await update_step_status(step_run_id, "COMPLETED" if status in ['success', 'partial'] else "FAILED")
        await update_step_event(step_run_id, "FINALIZE_DONE", {"status": status, "confidence": confidence})
        logger.info(f"[STEP2] Done: confidence={confidence}, status={status}")

    except Exception as e:
        logger.exception(f"[STEP2] EXCEPTION for {campaign_brief_id}: {str(e)}")
        await db.website_context_packs.update_one(
            {"website_context_pack_id": pack_id},
            {"$set": {
                "status": "failed",
                "step2": {"site": {"input_url": website_url, "final_url": website_url, "title": "unknown", "meta_description": "unknown", "language": "en"}},
                "step2_internal": {"analysis_quality": {"confidence_score_0_100": 0, "warnings": [str(e)], "missing_fields": []}},
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        await update_step_status(step_run_id, "FAILED")
        await update_step_event(step_run_id, "STEP2_FAILED", {"error": str(e)})


async def update_step_event(step_run_id: str, event: str, payload: dict = None):
    """Add event to step run progress"""
    event_doc = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {}
    }
    await db.step_runs.update_one(
        {"step_run_id": step_run_id},
        {
            "$push": {"progress.events": event_doc},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )


async def update_step_status(step_run_id: str, status: str):
    """Update step run status"""
    await db.step_runs.update_one(
        {"step_run_id": step_run_id},
        {"$set": {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )


@api_router.get("/orchestrations/{campaign_brief_id}/status")
async def get_orchestration_status(campaign_brief_id: str):
    """Get orchestration status with all step progress (for polling)"""
    
    orchestration = await db.orchestration_runs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    if not orchestration:
        raise HTTPException(status_code=404, detail="Orchestration not found")
    
    # Get step runs
    step_runs = await db.step_runs.find(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    ).to_list(10)
    
    # Get website context pack
    pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    # Get intel pack
    intel_pack = await db.perplexity_intel_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    return {
        "orchestration": orchestration,
        "steps": step_runs,
        "website_context_pack": pack,
        "perplexity_intel_pack": intel_pack
    }


@api_router.get("/website-context-packs/by-campaign/{campaign_brief_id}")
async def get_website_context_pack(campaign_brief_id: str):
    """Get website context pack by campaign brief ID"""
    
    pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    if not pack:
        raise HTTPException(status_code=404, detail="Website context pack not found")
    
    # Return both old format (data) and new format (step2) for compatibility
    # Frontend should prefer step2 if available
    return pack


@api_router.post("/website-context-packs/{pack_id}/micro-input")
async def submit_micro_input(pack_id: str, user_input: MicroInputSubmit):
    """Submit micro input answers and resume Step 2"""
    
    # Get pack
    pack_doc = await db.website_context_packs.find_one(
        {"website_context_pack_id": pack_id},
        {"_id": 0}
    )
    
    if not pack_doc:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    if pack_doc["status"] != "needs_user_input":
        raise HTTPException(status_code=400, detail="Pack does not need user input")
    
    # Apply user input
    from confidence import ConfidenceScorer
    
    pack_data = pack_doc["data"]
    scorer = ConfidenceScorer()
    
    updated_pack = scorer.apply_user_input(pack_data, user_input.model_dump())
    
    # Recompute confidence
    confidence_result = scorer.score(updated_pack)
    
    updated_pack['quality']['confidence_score_0_100'] = confidence_result.score
    updated_pack['quality']['missing_fields'] = confidence_result.missing_fields
    
    # Update status
    new_status = 'success' if confidence_result.score >= 60 else 'partial'
    updated_pack['status'] = new_status
    
    # Save to DB
    await db.website_context_packs.update_one(
        {"website_context_pack_id": pack_id},
        {"$set": {
            "status": new_status,
            "confidence_score": confidence_result.score,
            "data": updated_pack,
            "questions": [],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update step run
    step_run = await db.step_runs.find_one(
        {"campaign_brief_id": pack_doc["campaign_brief_id"], "step_key": "STEP2_WEBSITE_CONTEXT"},
        {"_id": 0}
    )
    
    if step_run:
        await update_step_event(step_run["step_run_id"], "STEP2_PATCHED_WITH_USER_INPUT")
        await update_step_event(step_run["step_run_id"], "STEP2_COMPLETED", {
            "status": new_status,
            "score": confidence_result.score
        })
        await update_step_status(step_run["step_run_id"], "COMPLETED")
    
    return {
        "status": new_status,
        "confidence_score": confidence_result.score,
        "pack": updated_pack
    }


# ============== STEP 3A: PERPLEXITY INTEL ==============

@api_router.post("/orchestrations/{campaign_brief_id}/step-3a/start")
async def start_step3a(campaign_brief_id: str):
    """Start Step 3A - Perplexity Intel Pack generation"""
    
    # Verify brief exists
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    # Get website context pack
    pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not pack:
        raise HTTPException(status_code=400, detail="Website context pack not found. Complete Step 2 first.")
    
    # Check if intel pack already exists
    existing = await db.perplexity_intel_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if existing and existing.get("status") == "success":
        return existing
    
    # Create intel pack placeholder
    intel_pack_id = str(uuid.uuid4())
    intel_doc = {
        "intel_pack_id": intel_pack_id,
        "campaign_brief_id": campaign_brief_id,
        "status": "running",
        "data": None,
        "search_results": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    if existing:
        await db.perplexity_intel_packs.update_one(
            {"campaign_brief_id": campaign_brief_id},
            {"$set": intel_doc}
        )
    else:
        await db.perplexity_intel_packs.insert_one(intel_doc)
    
    # Create Step 3A run
    step3a_run_id = str(uuid.uuid4())
    step3a_doc = {
        "step_run_id": step3a_run_id,
        "orchestration_id": None,  # Could link to orchestration
        "campaign_brief_id": campaign_brief_id,
        "step_key": "STEP3A_INTEL_PERPLEXITY",
        "status": "pending",
        "progress": {"events": []},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.step_runs.insert_one(step3a_doc)
    
    # Start Step 3A in background
    import asyncio
    asyncio.create_task(run_step3a(campaign_brief_id, intel_pack_id, step3a_run_id, brief, pack))
    
    return {
        "intel_pack_id": intel_pack_id,
        "campaign_brief_id": campaign_brief_id,
        "status": "running"
    }


async def run_step3a(campaign_brief_id: str, intel_pack_id: str, step_run_id: str, brief: dict, pack: dict):
    """Background task to run Step 3A - Perplexity Intel"""
    try:
        from perplexity_intel import PerplexityIntelClient
        
        logger.info(f"[STEP3A] Starting intel generation for brief={campaign_brief_id}")
        
        await update_step_event(step_run_id, "STEP3A_INTEL_STARTED")
        
        # Initialize client
        client = PerplexityIntelClient()
        
        await update_step_event(step_run_id, "STEP3A_INTEL_SEARCHING")
        
        # Generate intel pack
        result = await client.generate_intel_pack(
            campaign_brief=brief,
            website_context_pack=pack,
            intel_pack_id=intel_pack_id
        )
        
        await update_step_event(step_run_id, "STEP3A_INTEL_PARSING")
        
        intel_data = result["intel_pack"]
        search_results = result["search_results"]
        raw_api_response = result.get("raw_api_response", {})
        raw_content = result.get("raw_content", "")
        status = result["status"]
        
        logger.info(f"[STEP3A] Intel pack generated: status={status}")
        logger.info(f"[STEP3A] Category: {intel_data.get('category', {}).get('industry', 'N/A')}")
        logger.info(f"[STEP3A] Competitors found: {len(intel_data.get('competitors', []))}")
        
        # Save to DB (including raw API response for debugging)
        await db.perplexity_intel_packs.update_one(
            {"intel_pack_id": intel_pack_id},
            {"$set": {
                "status": status,
                "data": intel_data,
                "search_results": search_results,
                "raw_api_response": raw_api_response,
                "raw_content": raw_content,
                "api_metadata": {
                    "model": raw_api_response.get("model", "unknown"),
                    "usage": raw_api_response.get("usage", {}),
                    "citations_count": len(raw_api_response.get("citations", [])),
                    "response_timestamp": raw_api_response.get("timestamp")
                },
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        await update_step_event(step_run_id, "STEP3A_INTEL_COMPLETED", {
            "status": status,
            "competitors_count": len(intel_data.get('competitors', []))
        })
        await update_step_status(step_run_id, "COMPLETED")
        
        logger.info(f"[STEP3A] Intel pack saved: {intel_pack_id}")
        
    except Exception as e:
        logger.exception(f"[STEP3A] EXCEPTION for {campaign_brief_id}: {str(e)}")
        
        await db.perplexity_intel_packs.update_one(
            {"intel_pack_id": intel_pack_id},
            {"$set": {
                "status": "failed",
                "data": {"quality": {"errors": [str(e)]}},
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        await update_step_event(step_run_id, "STEP3A_INTEL_FAILED", {"error": str(e)})
        await update_step_status(step_run_id, "FAILED")


@api_router.get("/perplexity-intel-packs/by-campaign/{campaign_brief_id}")
async def get_perplexity_intel_pack(campaign_brief_id: str):
    """Get Perplexity Intel Pack by campaign brief ID"""
    
    pack = await db.perplexity_intel_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    if not pack:
        raise HTTPException(status_code=404, detail="Intel pack not found")
    
    return pack


# ============== DEBUG DASHBOARD API ==============

@api_router.get("/debug/campaigns")
async def get_debug_campaigns():
    """Get list of all campaigns with debug logs"""
    
    # Get recent campaigns with their status
    campaigns = []
    
    cursor = db.campaign_briefs.find(
        {},
        {"_id": 0, "campaign_brief_id": 1, "brand.website_url": 1, "created_at": 1, "contact.name": 1}
    ).sort("created_at", -1).limit(20)
    
    async for brief in cursor:
        brief_id = brief["campaign_brief_id"]
        
        # Get debug log summary
        debug_log = await db.debug_logs.find_one(
            {"campaign_brief_id": brief_id},
            {"_id": 0, "summary": 1, "updated_at": 1}
        )
        
        # Get orchestration status
        orch = await db.orchestration_runs.find_one(
            {"campaign_brief_id": brief_id},
            {"_id": 0, "status": 1}
        )
        
        # Get pack statuses
        website_pack = await db.website_context_packs.find_one(
            {"campaign_brief_id": brief_id},
            {"_id": 0, "status": 1, "confidence_score": 1}
        )
        intel_pack = await db.perplexity_intel_packs.find_one(
            {"campaign_brief_id": brief_id},
            {"_id": 0, "status": 1}
        )
        
        campaigns.append({
            "campaign_brief_id": brief_id,
            "website_url": brief.get("brand", {}).get("website_url", ""),
            "contact_name": brief.get("contact", {}).get("name", "Anonymous"),
            "created_at": brief.get("created_at"),
            "orchestration_status": orch.get("status") if orch else "not_started",
            "step2_status": website_pack.get("status") if website_pack else "not_started",
            "step2_confidence": website_pack.get("confidence_score") if website_pack else None,
            "step3a_status": intel_pack.get("status") if intel_pack else "not_started",
            "debug_events": debug_log.get("summary", {}).get("total_events", 0) if debug_log else 0,
            "has_errors": debug_log.get("summary", {}).get("errors", 0) > 0 if debug_log else False
        })
    
    return {"campaigns": campaigns}


@api_router.get("/debug/campaign/{campaign_brief_id}")
async def get_debug_log(campaign_brief_id: str):
    """Get full debug log for a campaign"""
    
    # Get the brief
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get website context pack
    website_pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    # Get intel pack
    intel_pack = await db.perplexity_intel_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    # Get debug log
    debug_log = await db.debug_logs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    # Get orchestration and step runs
    orch = await db.orchestration_runs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    step_runs = []
    cursor = db.step_runs.find(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    ).sort("created_at", 1)
    async for step in cursor:
        step_runs.append(step)
    
    # Build comprehensive debug data
    return {
        "campaign_brief_id": campaign_brief_id,
        "step1": {
            "title": "Campaign Brief",
            "status": "success" if brief else "not_found",
            "data": {
                "input": {
                    "website_url": brief.get("brand", {}).get("website_url"),
                    "primary_goal": brief.get("goal", {}).get("primary_goal"),
                    "success_definition": brief.get("goal", {}).get("success_definition"),
                    "country": brief.get("geo", {}).get("country"),
                    "city_or_region": brief.get("geo", {}).get("city_or_region"),
                    "destination_type": brief.get("destination", {}).get("type"),
                    "ads_intent": brief.get("ads_intent"),
                    "budget_range": brief.get("budget_range_monthly"),
                    "contact_name": brief.get("contact", {}).get("name"),
                    "contact_email": brief.get("contact", {}).get("email")
                },
                "computed": {
                    "track": brief.get("track"),
                    "created_at": brief.get("created_at")
                }
            }
        } if brief else None,
        "step2": {
            "title": "Website Context Extraction",
            "status": website_pack.get("status") if website_pack else "not_started",
            "confidence_score": website_pack.get("confidence_score") if website_pack else None,
            "data": website_pack.get("data") if website_pack else None
        } if website_pack else {"title": "Website Context Extraction", "status": "not_started"},
        "step3a": {
            "title": "Perplexity Intel",
            "status": intel_pack.get("status") if intel_pack else "not_started",
            "data": intel_pack.get("data") if intel_pack else None
        } if intel_pack else {"title": "Perplexity Intel", "status": "not_started"},
        "debug_events": debug_log.get("events", []) if debug_log else [],
        "orchestration": orch,
        "step_runs": step_runs
    }


@api_router.get("/debug/campaign/{campaign_brief_id}/prompt")
async def get_debug_prompt(campaign_brief_id: str):
    """Get the exact prompt that was/would be sent to Perplexity"""
    from perplexity_intel import build_user_prompt, SYSTEM_PROMPT, INTEL_PACK_SCHEMA
    
    # Get the brief
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get website context pack
    pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    if not pack:
        raise HTTPException(status_code=404, detail="Website pack not found - Step 2 not complete")
    
    # Build the prompt
    user_prompt = build_user_prompt(brief, pack)
    
    return {
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": user_prompt,
        "system_prompt_chars": len(SYSTEM_PROMPT),
        "user_prompt_chars": len(user_prompt),
        "schema_fields": len(INTEL_PACK_SCHEMA.get("properties", {})),
        "api_config": {
            "model": "sonar-pro",
            "temperature": 0.2,
            "max_tokens": 4000,
            "endpoint": "https://api.perplexity.ai/chat/completions"
        }
    }


@api_router.get("/debug/campaign/{campaign_brief_id}/raw-response")
async def get_debug_raw_response(campaign_brief_id: str):
    """Get the raw API response from Perplexity"""
    
    # Get intel pack with raw response
    intel_pack = await db.perplexity_intel_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    
    if not intel_pack:
        raise HTTPException(status_code=404, detail="Intel pack not found - Step 3A not complete")
    
    return {
        "campaign_brief_id": campaign_brief_id,
        "intel_pack_id": intel_pack.get("intel_pack_id"),
        "status": intel_pack.get("status"),
        "raw_api_response": intel_pack.get("raw_api_response", {}),
        "raw_content": intel_pack.get("raw_content", ""),
        "api_metadata": intel_pack.get("api_metadata", {}),
        "search_results": intel_pack.get("search_results", [])
    }


# ============== RESEARCH FOUNDATION: SEARCH INTENT ==============


# ============== CUSTOMER INTEL MODULE ==============

@api_router.post("/research/{campaign_brief_id}/customer-intel/run")
async def run_customer_intel(campaign_brief_id: str):
    """
    Run Customer Intel analysis for a campaign.
    
    Uses Perplexity sonar with inputs from Step 1+2 + available research modules.
    Runs with partial inputs — never blocks on missing modules.
    """
    from research.customer_intel import CustomerIntelService
    
    # Verify campaign exists
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    try:
        service = CustomerIntelService(db)
        result = await service.run(campaign_brief_id)
        
        return {
            "campaign_id": campaign_brief_id,
            "status": result["status"],
            "snapshot": result["snapshot"],
            "message": result["message"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[CUSTOMER_INTEL] Run failed: {e}")
        raise HTTPException(status_code=500, detail=f"Customer Intel failed: {str(e)}")


@api_router.get("/research/{campaign_brief_id}/customer-intel/latest")
async def get_customer_intel_latest(campaign_brief_id: str):
    """Get latest Customer Intel snapshot for a campaign"""
    from research.customer_intel import CustomerIntelService
    from datetime import datetime, timezone
    
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    service = CustomerIntelService(db)
    snapshot = await service.get_latest(campaign_brief_id)
    
    if not snapshot:
        return {
            "has_data": False,
            "status": "not_run",
            "latest": None,
            "refresh_due_in_days": None
        }
    
    now = datetime.now(timezone.utc)
    refresh_due = snapshot.refresh_due_at
    if refresh_due.tzinfo is None:
        refresh_due = refresh_due.replace(tzinfo=timezone.utc)
    
    days_until_refresh = max(0, (refresh_due - now).days)
    status = "fresh" if days_until_refresh > 0 else "stale"
    
    return {
        "has_data": True,
        "status": status,
        "latest": snapshot.model_dump(mode="json"),
        "refresh_due_in_days": days_until_refresh
    }


@api_router.get("/research/{campaign_brief_id}/customer-intel/history")
async def get_customer_intel_history(campaign_brief_id: str):
    """Get Customer Intel history for a campaign"""
    from research.customer_intel import CustomerIntelService
    
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    service = CustomerIntelService(db)
    history = await service.get_history(campaign_brief_id)
    
    return {
        "campaign_id": campaign_brief_id,
        "history": [s.model_dump(mode="json") for s in history]
    }



@api_router.post("/research/{campaign_brief_id}/search-intent/run")
async def run_search_intent(campaign_brief_id: str):
    """
    Run search intent analysis for a campaign (v2).
    
    Builds a SearchIntentSnapshot using:
    - Seeds from Step 1/2 data + Competitors module
    - Google Suggest for real autocomplete queries
    - Relevance gate with scoring
    - Bucketing into price/trust/urgency/comparison/general
    - Optional LLM curation (Perplexity sonar)
    - Derived outputs for ad keywords and forum queries
    """
    from research.search_intent import SearchIntentService
    
    # Get campaign brief (Step 1)
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    # Get website context pack (Step 2)
    website_pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not website_pack:
        raise HTTPException(status_code=400, detail="Website context pack not found. Complete Step 2 first.")
    
    # Run search intent service v2 (fetches competitors internally)
    service = SearchIntentService(db)
    result = await service.run(
        campaign_id=campaign_brief_id,
        campaign_brief=brief,
        website_context_pack=website_pack
    )
    
    return {
        "campaign_id": campaign_brief_id,
        "status": result["status"],
        "snapshot": result["snapshot"],
        "message": result["message"]
    }


@api_router.get("/research/{campaign_brief_id}/search-intent/latest")
async def get_search_intent_latest(campaign_brief_id: str):
    """Get latest search intent snapshot for a campaign"""
    from research.search_intent import SearchIntentService
    from datetime import datetime, timezone
    
    # Verify campaign exists
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    service = SearchIntentService(db)
    snapshot = await service.get_latest(campaign_brief_id)
    
    if not snapshot:
        return {
            "has_data": False,
            "status": "not_run",
            "latest": None,
            "refresh_due_in_days": None
        }
    
    # Calculate status
    now = datetime.now(timezone.utc)
    refresh_due = snapshot.refresh_due_at
    if refresh_due.tzinfo is None:
        refresh_due = refresh_due.replace(tzinfo=timezone.utc)
    
    days_until_refresh = max(0, (refresh_due - now).days)
    status = "fresh" if days_until_refresh > 0 else "stale"
    
    return {
        "has_data": True,
        "status": status,
        "latest": snapshot.model_dump(mode="json"),
        "refresh_due_in_days": days_until_refresh
    }


@api_router.get("/research/{campaign_brief_id}/search-intent/history")
async def get_search_intent_history(campaign_brief_id: str):
    """Get search intent snapshot history for a campaign"""
    from research.search_intent import SearchIntentService
    
    # Verify campaign exists
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    service = SearchIntentService(db)
    
    # Get latest and history
    latest = await service.get_latest(campaign_brief_id)
    history = await service.get_history(campaign_brief_id)
    
    # Combine: latest + history
    all_snapshots = []
    if latest:
        all_snapshots.append(latest.model_dump(mode="json"))
    for snap in history:
        all_snapshots.append(snap.model_dump(mode="json"))
    
    return {
        "campaign_id": campaign_brief_id,
        "snapshots": all_snapshots,
        "total_count": len(all_snapshots)
    }


@api_router.get("/research/{campaign_brief_id}")
async def get_research_pack(campaign_brief_id: str):
    """Get full research pack for a campaign (all sources)"""
    
    # Verify campaign exists
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    # Get research pack
    pack = await db.research_packs.find_one(
        {"campaign_id": campaign_brief_id},
        {"_id": 0}
    )
    
    if not pack:
        return {
            "campaign_id": campaign_brief_id,
            "has_data": False,
            "sources": {}
        }
    
    return {
        "campaign_id": campaign_brief_id,
        "has_data": True,
        "research_pack_id": pack.get("research_pack_id"),
        "sources": pack.get("sources", {}),
        "created_at": pack.get("created_at"),
        "updated_at": pack.get("updated_at")
    }


# ============== RESEARCH FOUNDATION: SEASONALITY ==============

@api_router.post("/research/{campaign_brief_id}/seasonality/run")
async def run_seasonality(campaign_brief_id: str):
    """
    Run seasonality analysis for a campaign.
    
    Uses Perplexity to identify key calendar moments, buying triggers,
    and seasonal patterns specific to the business location and niche.
    """
    from research.seasonality import SeasonalityService
    
    # Get campaign brief (Step 1)
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    # Get website context pack (Step 2)
    website_pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not website_pack:
        raise HTTPException(status_code=400, detail="Website context pack not found. Complete Step 2 first.")
    
    # Run seasonality service
    service = SeasonalityService(db)
    result = await service.run(
        campaign_id=campaign_brief_id,
        campaign_brief=brief,
        website_context_pack=website_pack
    )
    
    return {
        "campaign_id": campaign_brief_id,
        "status": result["status"],
        "snapshot": result["snapshot"],
        "message": result["message"]
    }


@api_router.get("/research/{campaign_brief_id}/seasonality/latest")
async def get_seasonality_latest(campaign_brief_id: str):
    """Get latest seasonality snapshot for a campaign"""
    from research.seasonality import SeasonalityService
    from datetime import datetime, timezone
    
    # Verify campaign exists
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    service = SeasonalityService(db)
    snapshot = await service.get_latest(campaign_brief_id)
    
    if not snapshot:
        return {
            "has_data": False,
            "status": "not_run",
            "latest": None,
            "refresh_due_in_days": None
        }
    
    # Calculate status
    now = datetime.now(timezone.utc)
    refresh_due = snapshot.refresh_due_at
    if refresh_due.tzinfo is None:
        refresh_due = refresh_due.replace(tzinfo=timezone.utc)
    
    days_until_refresh = max(0, (refresh_due - now).days)
    status = "fresh" if days_until_refresh > 0 else "stale"
    
    return {
        "has_data": True,
        "status": status,
        "latest": snapshot.model_dump(mode="json"),
        "refresh_due_in_days": days_until_refresh
    }


@api_router.get("/research/{campaign_brief_id}/seasonality/history")
async def get_seasonality_history(campaign_brief_id: str):
    """Get seasonality snapshot history for a campaign"""
    from research.seasonality import SeasonalityService
    
    # Verify campaign exists
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    service = SeasonalityService(db)
    
    # Get latest and history
    latest = await service.get_latest(campaign_brief_id)
    history = await service.get_history(campaign_brief_id)
    
    # Combine: latest + history
    all_snapshots = []
    if latest:
        all_snapshots.append(latest.model_dump(mode="json"))
    for snap in history:
        all_snapshots.append(snap.model_dump(mode="json"))
    
    return {
        "campaign_id": campaign_brief_id,
        "snapshots": all_snapshots,
        "total_count": len(all_snapshots)
    }


# ============== RESEARCH FOUNDATION: COMPETITOR DISCOVERY ==============

@api_router.post("/research/{campaign_brief_id}/competitors/run")
async def run_competitors(campaign_brief_id: str):
    """
    Run competitor discovery for a campaign.
    
    Uses Perplexity to identify 2-3 direct competitors with:
    - Website and social presence
    - Positioning summary
    - Category search terms for downstream use
    """
    from research.competitors import CompetitorService
    
    # Get campaign brief (Step 1)
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    # Get website context pack (Step 2)
    website_pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not website_pack:
        raise HTTPException(status_code=400, detail="Website context pack not found. Complete Step 2 first.")
    
    # Run competitor service
    service = CompetitorService(db)
    result = await service.run(
        campaign_id=campaign_brief_id,
        campaign_brief=brief,
        website_context_pack=website_pack
    )
    
    return {
        "campaign_id": campaign_brief_id,
        "status": result["status"],
        "snapshot": result["snapshot"],
        "message": result["message"]
    }


@api_router.get("/research/{campaign_brief_id}/competitors/latest")
async def get_competitors_latest(campaign_brief_id: str):
    """Get latest competitor snapshot for a campaign"""
    from research.competitors import CompetitorService
    from datetime import datetime, timezone
    
    # Verify campaign exists
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    service = CompetitorService(db)
    snapshot = await service.get_latest(campaign_brief_id)
    
    if not snapshot:
        return {
            "has_data": False,
            "status": "not_run",
            "latest": None,
            "refresh_due_in_days": None
        }
    
    # Calculate status
    now = datetime.now(timezone.utc)
    refresh_due = snapshot.refresh_due_at
    if refresh_due.tzinfo is None:
        refresh_due = refresh_due.replace(tzinfo=timezone.utc)
    
    days_until_refresh = max(0, (refresh_due - now).days)
    status = "fresh" if days_until_refresh > 0 else "stale"
    
    return {
        "has_data": True,
        "status": status,
        "latest": snapshot.model_dump(mode="json"),
        "refresh_due_in_days": days_until_refresh
    }


@api_router.get("/research/{campaign_brief_id}/competitors/history")
async def get_competitors_history(campaign_brief_id: str):
    """Get competitor snapshot history for a campaign"""
    from research.competitors import CompetitorService
    
    # Verify campaign exists
    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")
    
    service = CompetitorService(db)
    
    # Get latest and history
    latest = await service.get_latest(campaign_brief_id)
    history = await service.get_history(campaign_brief_id)
    
    # Combine: latest + history
    all_snapshots = []
    if latest:
        all_snapshots.append(latest.model_dump(mode="json"))
    for snap in history:
        all_snapshots.append(snap.model_dump(mode="json"))
    
    return {
        "campaign_id": campaign_brief_id,
        "snapshots": all_snapshots,
        "total_count": len(all_snapshots)
    }


# ============== REVIEWS & REPUTATION ==============

@api_router.post("/research/{campaign_brief_id}/reviews/run")
async def run_reviews(campaign_brief_id: str):
    """
    Run reviews & reputation analysis for a campaign.

    2-call Perplexity pipeline:
    1. Discovery: Find all review platforms
    2. Analysis: Extract themes, quotes, trust signals
    """
    from research.reviews import ReviewsService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    website_pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not website_pack:
        raise HTTPException(status_code=400, detail="Website context pack not found. Complete Step 2 first.")

    service = ReviewsService(db)
    result = await service.run(
        campaign_id=campaign_brief_id,
        campaign_brief=brief,
        website_context_pack=website_pack
    )

    return {
        "campaign_id": campaign_brief_id,
        "status": result["status"],
        "snapshot": result["snapshot"],
        "message": result["message"]
    }


@api_router.get("/research/{campaign_brief_id}/reviews/latest")
async def get_reviews_latest(campaign_brief_id: str):
    """Get latest reviews snapshot for a campaign"""
    from research.reviews import ReviewsService
    from datetime import datetime, timezone

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = ReviewsService(db)
    snapshot = await service.get_latest(campaign_brief_id)

    if not snapshot:
        return {
            "has_data": False,
            "status": "not_run",
            "latest": None,
            "refresh_due_in_days": None
        }

    now = datetime.now(timezone.utc)
    refresh_due = snapshot.refresh_due_at
    if refresh_due.tzinfo is None:
        refresh_due = refresh_due.replace(tzinfo=timezone.utc)

    days_until_refresh = max(0, (refresh_due - now).days)
    status = "fresh" if days_until_refresh > 0 else "stale"

    return {
        "has_data": True,
        "status": status,
        "latest": snapshot.model_dump(mode="json"),
        "refresh_due_in_days": days_until_refresh
    }


@api_router.get("/research/{campaign_brief_id}/reviews/history")
async def get_reviews_history(campaign_brief_id: str):
    """Get reviews snapshot history for a campaign"""
    from research.reviews import ReviewsService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = ReviewsService(db)
    latest = await service.get_latest(campaign_brief_id)
    history = await service.get_history(campaign_brief_id)

    all_snapshots = []
    if latest:
        all_snapshots.append(latest.model_dump(mode="json"))
    for snap in history:
        all_snapshots.append(snap.model_dump(mode="json"))

    return {
        "campaign_id": campaign_brief_id,
        "snapshots": all_snapshots,
        "total_count": len(all_snapshots)
    }


# ============== COMMUNITY ENDPOINTS ==============

@api_router.post("/research/{campaign_brief_id}/community/run")
async def run_community(campaign_brief_id: str):
    """
    Run community intelligence analysis for a campaign.

    2-call Perplexity pipeline:
    1. Discovery: Find real forum threads
    2. Synthesis: Extract themes, language bank, audience notes
    """
    from research.community import CommunityService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    website_pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not website_pack:
        raise HTTPException(status_code=400, detail="Website context pack not found. Complete Step 2 first.")

    service = CommunityService(db)
    result = await service.run(
        campaign_id=campaign_brief_id,
        campaign_brief=brief,
        website_context_pack=website_pack
    )

    return {
        "campaign_id": campaign_brief_id,
        "status": result["status"],
        "snapshot": result["snapshot"],
        "message": result["message"]
    }


@api_router.get("/research/{campaign_brief_id}/community/latest")
async def get_community_latest(campaign_brief_id: str):
    """Get latest community intelligence snapshot for a campaign"""
    from research.community import CommunityService
    from datetime import datetime, timezone

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = CommunityService(db)
    snapshot = await service.get_latest(campaign_brief_id)

    if not snapshot:
        return {
            "has_data": False,
            "status": "not_run",
            "latest": None,
            "refresh_due_in_days": None
        }

    now = datetime.now(timezone.utc)
    refresh_due = snapshot.refresh_due_at
    if refresh_due.tzinfo is None:
        refresh_due = refresh_due.replace(tzinfo=timezone.utc)

    days_until_refresh = max(0, (refresh_due - now).days)
    status = "fresh" if days_until_refresh > 0 else "stale"

    return {
        "has_data": True,
        "status": status,
        "latest": snapshot.model_dump(mode="json"),
        "refresh_due_in_days": days_until_refresh
    }


@api_router.get("/research/{campaign_brief_id}/community/history")
async def get_community_history(campaign_brief_id: str):
    """Get community intelligence snapshot history for a campaign"""
    from research.community import CommunityService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = CommunityService(db)
    latest = await service.get_latest(campaign_brief_id)
    history = await service.get_history(campaign_brief_id)

    all_snapshots = []
    if latest:
        all_snapshots.append(latest.model_dump(mode="json"))
    for snap in history:
        all_snapshots.append(snap.model_dump(mode="json"))

    return {
        "campaign_id": campaign_brief_id,
        "snapshots": all_snapshots,
        "total_count": len(all_snapshots)
    }


# ============== PRESS & MEDIA ENDPOINTS ==============

@api_router.post("/research/{campaign_brief_id}/press-media/run")
async def run_press_media(campaign_brief_id: str):
    """
    Run press & media intelligence analysis for a campaign.

    2-call Perplexity pipeline:
    1. Discovery: Find press articles, news, blog posts
    2. Analysis: Extract narratives, key quotes, coverage gaps
    """
    from research.press_media import PressMediaService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    website_pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not website_pack:
        raise HTTPException(status_code=400, detail="Website context pack not found. Complete Step 2 first.")

    service = PressMediaService(db)
    result = await service.run(
        campaign_id=campaign_brief_id,
        campaign_brief=brief,
        website_context_pack=website_pack
    )

    return {
        "campaign_id": campaign_brief_id,
        "status": result["status"],
        "snapshot": result["snapshot"],
        "message": result["message"]
    }


@api_router.get("/research/{campaign_brief_id}/press-media/latest")
async def get_press_media_latest(campaign_brief_id: str):
    """Get latest press & media snapshot for a campaign"""
    from research.press_media import PressMediaService
    from datetime import datetime, timezone

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = PressMediaService(db)
    snapshot = await service.get_latest(campaign_brief_id)

    if not snapshot:
        return {
            "has_data": False,
            "status": "not_run",
            "latest": None,
            "refresh_due_in_days": None
        }

    now = datetime.now(timezone.utc)
    refresh_due = snapshot.refresh_due_at
    if refresh_due.tzinfo is None:
        refresh_due = refresh_due.replace(tzinfo=timezone.utc)

    days_until_refresh = max(0, (refresh_due - now).days)
    status = "fresh" if days_until_refresh > 0 else "stale"

    return {
        "has_data": True,
        "status": status,
        "latest": snapshot.model_dump(mode="json"),
        "refresh_due_in_days": days_until_refresh
    }


@api_router.get("/research/{campaign_brief_id}/press-media/history")
async def get_press_media_history(campaign_brief_id: str):
    """Get press & media snapshot history for a campaign"""
    from research.press_media import PressMediaService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = PressMediaService(db)
    latest = await service.get_latest(campaign_brief_id)
    history = await service.get_history(campaign_brief_id)

    all_snapshots = []
    if latest:
        all_snapshots.append(latest.model_dump(mode="json"))
    for snap in history:
        all_snapshots.append(snap.model_dump(mode="json"))

    return {
        "campaign_id": campaign_brief_id,
        "snapshots": all_snapshots,
        "total_count": len(all_snapshots)
    }



# ============== SOCIAL TRENDS ENDPOINTS ==============

@api_router.post("/research/{campaign_brief_id}/social-trends/run")
async def run_social_trends(campaign_brief_id: str, background_tasks: BackgroundTasks):
    """
    Run social trends intelligence for a campaign.
    Starts as background task and returns immediately.
    Poll /latest for results.
    """
    from research.social_trends import SocialTrendsService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    website_pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not website_pack:
        raise HTTPException(status_code=400, detail="Website context pack not found. Complete Step 2 first.")

    async def _run_pipeline():
        service = SocialTrendsService(db)
        await service.run(
            campaign_id=campaign_brief_id,
            campaign_brief=brief,
            website_context_pack=website_pack
        )

    import asyncio
    asyncio.create_task(_run_pipeline())

    return {
        "campaign_id": campaign_brief_id,
        "status": "running",
        "snapshot": None,
        "message": "Social trends pipeline started. Poll /latest for results."
    }


@api_router.get("/research/{campaign_brief_id}/social-trends/latest")
async def get_social_trends_latest(campaign_brief_id: str):
    """Get latest social trends snapshot for a campaign"""
    from research.social_trends import SocialTrendsService
    from datetime import datetime, timezone

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = SocialTrendsService(db)
    snapshot = await service.get_latest(campaign_brief_id)

    if not snapshot:
        return {
            "has_data": False,
            "status": "not_run",
            "latest": None,
            "refresh_due_in_days": None
        }

    now = datetime.now(timezone.utc)
    refresh_due = snapshot.refresh_due_at
    if refresh_due.tzinfo is None:
        refresh_due = refresh_due.replace(tzinfo=timezone.utc)

    days_until_refresh = max(0, (refresh_due - now).days)
    status = "fresh" if days_until_refresh > 0 else "stale"

    return {
        "has_data": True,
        "status": status,
        "latest": snapshot.model_dump(mode="json"),
        "refresh_due_in_days": days_until_refresh
    }


@api_router.get("/research/{campaign_brief_id}/social-trends/history")
async def get_social_trends_history(campaign_brief_id: str):
    """Get social trends snapshot history for a campaign"""
    from research.social_trends import SocialTrendsService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = SocialTrendsService(db)
    latest = await service.get_latest(campaign_brief_id)
    history = await service.get_history(campaign_brief_id)

    all_snapshots = []
    if latest:
        all_snapshots.append(latest.model_dump(mode="json"))
    for snap in history:
        all_snapshots.append(snap.model_dump(mode="json"))

    return {
        "campaign_id": campaign_brief_id,
        "snapshots": all_snapshots,
        "total_count": len(all_snapshots)
    }


# ============== ADS INTELLIGENCE (FOREPLAY) ==============

@api_router.post("/research/{campaign_brief_id}/ads-intel/run")
async def run_ads_intel(campaign_brief_id: str):
    """
    Run Ads Intelligence analysis for a campaign.
    Uses Foreplay API to find competitor + category winning ads.
    """
    from research.ads_intel import AdsIntelService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    website_pack = await db.website_context_packs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0}
    )
    if not website_pack:
        raise HTTPException(status_code=400, detail="Website context pack not found. Complete Step 2 first.")

    async def _run_pipeline():
        service = AdsIntelService(db)
        await service.run(campaign_id=campaign_brief_id)

    import asyncio
    asyncio.create_task(_run_pipeline())

    return {
        "campaign_id": campaign_brief_id,
        "status": "running",
        "snapshot": None,
        "message": "Ads intelligence pipeline started. Poll /latest for results."
    }


@api_router.get("/research/{campaign_brief_id}/ads-intel/latest")
async def get_ads_intel_latest(campaign_brief_id: str):
    """Get latest Ads Intel snapshot for a campaign"""
    from research.ads_intel import AdsIntelService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = AdsIntelService(db)
    snapshot = await service.get_latest(campaign_brief_id)

    if not snapshot:
        return {
            "has_data": False,
            "status": "not_run",
            "latest": None,
            "refresh_due_in_days": None
        }

    now = datetime.now(timezone.utc)
    refresh_due = snapshot.refresh_due_at
    if refresh_due.tzinfo is None:
        refresh_due = refresh_due.replace(tzinfo=timezone.utc)

    days_until_refresh = max(0, (refresh_due - now).days)
    status = "fresh" if days_until_refresh > 0 else "stale"

    return {
        "has_data": True,
        "status": status,
        "latest": snapshot.model_dump(mode="json"),
        "refresh_due_in_days": days_until_refresh
    }


@api_router.get("/research/{campaign_brief_id}/ads-intel/history")
async def get_ads_intel_history(campaign_brief_id: str):
    """Get Ads Intel snapshot history for a campaign"""
    from research.ads_intel import AdsIntelService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = AdsIntelService(db)
    latest = await service.get_latest(campaign_brief_id)
    history = await service.get_history(campaign_brief_id)

    all_snapshots = []
    if latest:
        all_snapshots.append(latest.model_dump(mode="json"))
    for snap in history:
        all_snapshots.append(snap.model_dump(mode="json"))

    return {
        "campaign_id": campaign_brief_id,
        "snapshots": all_snapshots,
        "total_count": len(all_snapshots)
    }


# ============================================================
# CREATIVE ANALYSIS ENDPOINTS
# ============================================================

@api_router.post("/research/{campaign_brief_id}/creative-analysis/run")
async def run_creative_analysis(campaign_brief_id: str):
    """
    Trigger creative analysis pipeline for a campaign.
    Analyzes winning ads and top TikTok posts using multimodal LLM.
    Runs async — poll /latest for results.
    """
    from research.creative_analysis import CreativeAnalysisService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    # Check prerequisites: need ads_intel or social_trends data
    pack = await db.research_packs.find_one(
        {"campaign_id": campaign_brief_id},
        {"_id": 0, "sources.ads_intel.latest": 1, "sources.social_trends.latest": 1}
    )
    if not pack:
        raise HTTPException(status_code=400, detail="No research data. Run Ads Intel or Social Trends first.")

    has_ads = bool(pack.get("sources", {}).get("ads_intel", {}).get("latest"))
    has_social = bool(pack.get("sources", {}).get("social_trends", {}).get("latest"))
    if not has_ads and not has_social:
        raise HTTPException(status_code=400, detail="Run Ads Intel or Social Trends first.")

    async def _run_pipeline():
        service = CreativeAnalysisService(db)
        await service.run(campaign_id=campaign_brief_id)

    import asyncio
    asyncio.create_task(_run_pipeline())

    return {
        "campaign_id": campaign_brief_id,
        "status": "running",
        "snapshot": None,
        "message": "Creative analysis pipeline started. Poll /latest for results.",
    }


@api_router.get("/research/{campaign_brief_id}/creative-analysis/latest")
async def get_creative_analysis_latest(campaign_brief_id: str):
    """Get latest creative analysis snapshot for a campaign."""
    from research.creative_analysis import CreativeAnalysisService
    from datetime import datetime, timezone

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = CreativeAnalysisService(db)
    snapshot = await service.get_latest(campaign_brief_id)

    if not snapshot:
        return {
            "has_data": False,
            "status": "no_data",
            "latest": None,
            "refresh_due_in_days": None,
        }

    now = datetime.now(timezone.utc)
    days_until_refresh = max(0, (snapshot.refresh_due_at - now).days)

    return {
        "has_data": True,
        "status": snapshot.status,
        "latest": snapshot.model_dump(mode="json"),
        "refresh_due_in_days": days_until_refresh,
    }


@api_router.get("/research/{campaign_brief_id}/creative-analysis/history")
async def get_creative_analysis_history(campaign_brief_id: str):
    """Get creative analysis history for a campaign."""
    from research.creative_analysis import CreativeAnalysisService

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0, "campaign_brief_id": 1}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    service = CreativeAnalysisService(db)
    history = await service.get_history(campaign_brief_id)

    return {
        "campaign_id": campaign_brief_id,
        "snapshots": [s.model_dump(mode="json") for s in history],
        "total_count": len(history),
    }


# ============================================================
# MEDIA CACHE ENDPOINTS
# ============================================================

@api_router.get("/media/thumb/{video_id}")
async def get_cached_thumbnail(video_id: str):
    """Serve a cached thumbnail image."""
    from media_cache import get_thumb_path, thumb_exists
    from fastapi.responses import FileResponse

    if not thumb_exists(video_id):
        raise HTTPException(status_code=404, detail="Thumbnail not cached")

    return FileResponse(
        get_thumb_path(video_id),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@api_router.get("/media/video/{video_id}")
async def get_cached_video(video_id: str, request: Request):
    """Serve a cached video file with Range request support."""
    from media_cache import get_video_path, video_exists
    from fastapi.responses import StreamingResponse
    import os

    if not video_exists(video_id):
        raise HTTPException(status_code=404, detail="Video not cached")

    path = get_video_path(video_id)
    file_size = os.path.getsize(path)

    range_header = request.headers.get("range")
    if range_header:
        # Parse Range: bytes=START-END
        range_val = range_header.replace("bytes=", "").strip()
        parts = range_val.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        end = min(end, file_size - 1)
        content_length = end - start + 1

        def ranged_file():
            with open(path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(65536, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            ranged_file(),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=86400",
            },
        )
    else:
        def stream_file():
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk

        return StreamingResponse(
            stream_file(),
            media_type="video/mp4",
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=86400",
            },
        )


@api_router.post("/media/cache-video/{video_id}")
async def cache_video_on_demand(video_id: str, request: Request):
    """Cache a video on-demand (triggered when user clicks play)."""
    from media_cache import download_video, video_exists

    if video_exists(video_id):
        return {"status": "already_cached", "video_id": video_id}

    body = await request.json()
    video_url = body.get("video_url", "")
    if not video_url:
        raise HTTPException(status_code=400, detail="video_url required")

    success = await download_video(video_url, video_id)
    if success:
        return {"status": "cached", "video_id": video_id}
    else:
        raise HTTPException(status_code=502, detail="Failed to download video")


@api_router.get("/media/stats")
async def get_media_cache_stats():
    """Get cache statistics."""
    from media_cache import get_cache_stats
    return get_cache_stats()


# ============== PDF REPORT EXPORT ==============

@api_router.get("/research/{campaign_brief_id}/export/pdf")
async def export_pdf_report(campaign_brief_id: str):
    """Generate and return a PDF intelligence report for the campaign."""
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    brief = await db.campaign_briefs.find_one(
        {"campaign_brief_id": campaign_brief_id}, {"_id": 0}
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Campaign brief not found")

    pack = await db.research_packs.find_one(
        {"campaign_id": campaign_brief_id}, {"_id": 0}
    )
    sources = pack.get("sources", {}) if pack else {}

    brand = brief.get("brand_name") or brief.get("website_url", "Unknown")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)

    dark = HexColor("#0A0A0A")
    muted = HexColor("#666666")

    title_style = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=22, textColor=dark, spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", fontName="Helvetica", fontSize=10, textColor=muted, spaceAfter=16)
    h2_style = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=14, textColor=dark, spaceBefore=18, spaceAfter=8)
    h3_style = ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=11, textColor=dark, spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.5, textColor=HexColor("#333333"), leading=14, spaceAfter=3)
    bullet_style = ParagraphStyle("Bullet", fontName="Helvetica", fontSize=9.5, textColor=HexColor("#333333"), leading=14, leftIndent=12, spaceAfter=2, bulletIndent=0, bulletFontSize=9)
    meta_style = ParagraphStyle("Meta", fontName="Helvetica", fontSize=8, textColor=muted)

    elements = []

    # Title
    elements.append(Paragraph("NOVARA Intelligence Report", title_style))
    elements.append(Paragraph(f"{brand} &mdash; Generated {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E0E0E0"), spaceAfter=12))

    def safe_text(t):
        if not t:
            return ""
        import re
        return re.sub(r'[\[\]【】†‡\d+]', '', str(t)).strip()

    def add_list(items, label=None):
        if label:
            elements.append(Paragraph(label, h3_style))
        for item in (items or [])[:15]:
            txt = safe_text(item if isinstance(item, str) else item.get("name") or item.get("query") or item.get("moment") or str(item))
            if txt:
                elements.append(Paragraph(f"\u2022 {txt}", bullet_style))

    # --- Customer Intel ---
    ci = sources.get("customer_intel", {}).get("latest", {})
    if ci:
        elements.append(Paragraph("Audience Intelligence", h2_style))
        segments = ci.get("segments") or ci.get("icp_segments") or []
        for seg in segments:
            seg_name = seg.get("segment_name") or seg.get("name", "Segment")
            elements.append(Paragraph(seg_name, h3_style))
            jtbd = seg.get("jtbd") or seg.get("job_to_be_done")
            if jtbd:
                elements.append(Paragraph(f"<i>{safe_text(jtbd)}</i>", body_style))
            for key, label in [("core_motives", "Motives"), ("top_pains", "Pains"), ("top_objections", "Objections")]:
                items = seg.get(key, [])
                if items:
                    elements.append(Paragraph(label, ParagraphStyle("SubH", fontName="Helvetica-Bold", fontSize=9, textColor=muted, spaceBefore=4, spaceAfter=2)))
                    for it in items[:5]:
                        elements.append(Paragraph(f"\u2022 {safe_text(it)}", bullet_style))

    # --- Search Demand ---
    si = sources.get("search_intent", {}).get("latest", {})
    if si:
        elements.append(Paragraph("Search Demand", h2_style))
        add_list(si.get("top_10_queries"), "Top Queries")
        buckets = {}
        for q in si.get("ad_keyword_queries", []):
            b = q.get("bucket", "general") if isinstance(q, dict) else "general"
            buckets.setdefault(b, []).append(q.get("query", str(q)) if isinstance(q, dict) else str(q))
        for bucket, queries in buckets.items():
            elements.append(Paragraph(f"{bucket.capitalize()} Intent ({len(queries)})", h3_style))
            for q in queries[:8]:
                elements.append(Paragraph(f"\u2022 {safe_text(q)}", bullet_style))

    # --- Seasonality ---
    sea = sources.get("seasonality", {}).get("latest", {})
    if sea:
        elements.append(Paragraph("Seasonality & Timing", h2_style))
        for m in (sea.get("key_moments") or [])[:10]:
            name = m.get("moment") or m.get("name", "")
            demand = m.get("demand", "")
            window = m.get("window") or m.get("time_window", "")
            elements.append(Paragraph(f"\u2022 <b>{safe_text(name)}</b> ({demand}) \u2014 {safe_text(window)}", bullet_style))

    # --- Competitors ---
    comp = sources.get("competitors", {}).get("latest", {})
    if comp:
        elements.append(Paragraph("Competitive Landscape", h2_style))
        for c in (comp.get("competitors") or []):
            elements.append(Paragraph(c.get("name", "Competitor"), h3_style))
            if c.get("website_url"):
                elements.append(Paragraph(c["website_url"], meta_style))
            add_list(c.get("strengths") or c.get("competitive_advantages"), "Strengths")
            add_list(c.get("weaknesses") or c.get("competitive_weaknesses"), "Weaknesses")

    # --- Reviews ---
    rev = sources.get("reviews", {}).get("latest", {})
    if rev:
        elements.append(Paragraph("Customer Reviews", h2_style))
        add_list(rev.get("strength_themes"), "Strength Themes")
        add_list(rev.get("weakness_themes"), "Weakness Themes")

    # --- Community ---
    comm = sources.get("community", {}).get("latest", {})
    if comm:
        elements.append(Paragraph("Community Intelligence", h2_style))
        threads = comm.get("threads") or []
        if threads:
            for t in threads[:8]:
                title = t.get("title") or t.get("topic", "")
                elements.append(Paragraph(f"\u2022 {safe_text(title)}", bullet_style))

    # --- Press & Media ---
    pm = sources.get("press_media", {}).get("latest", {})
    if pm:
        elements.append(Paragraph("Press & Media", h2_style))
        if pm.get("coverage_summary"):
            elements.append(Paragraph(safe_text(pm["coverage_summary"]), body_style))
        for n in (pm.get("narratives") or []):
            elements.append(Paragraph(f"\u2022 <b>{safe_text(n.get('narrative',''))}</b> ({n.get('sentiment','')})", bullet_style))

    # --- Social Trends ---
    st = sources.get("social_trends", {}).get("latest", {})
    if st:
        elements.append(Paragraph("Social Trends", h2_style))
        shortlist = st.get("shortlist", {})
        tt = shortlist.get("tiktok", [])
        ig = shortlist.get("instagram", [])
        elements.append(Paragraph(f"{len(tt)} TikTok posts, {len(ig)} Instagram posts curated", body_style))

    # --- Ads Intel ---
    ai_data = sources.get("ads_intel", {}).get("latest", {})
    if ai_data:
        elements.append(Paragraph("Ad Intelligence", h2_style))
        cw = ai_data.get("competitor_winners", {}).get("ads", [])
        cat = ai_data.get("category_winners", {}).get("ads", [])
        elements.append(Paragraph(f"{len(cw)} competitor ads, {len(cat)} category ads analyzed", body_style))

    # Footer
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E0E0E0"), spaceBefore=12))
    elements.append(Paragraph("Generated by Novara Intelligence Platform", ParagraphStyle("Footer", fontName="Helvetica", fontSize=8, textColor=muted, alignment=TA_CENTER)))

    doc.build(elements)
    buf.seek(0)
    filename = f"novara-report-{brand.lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ============== MODULE RUN PROGRESS ==============

@api_router.get("/research/{campaign_brief_id}/{module}/progress")
async def get_module_progress(campaign_brief_id: str, module: str):
    """Get real-time progress for a running module."""
    module_map = {
        "customer-intel": "customer_intel",
        "search-intent": "search_intent",
        "seasonality": "seasonality",
        "competitors": "competitors",
        "reviews": "reviews",
        "community": "community",
        "press-media": "press_media",
        "social-trends": "social_trends",
        "ads-intel": "ads_intel",
        "creative-analysis": "creative_analysis",
    }
    module_map.get(module, module)

    step_run = await db.step_runs.find_one(
        {"campaign_brief_id": campaign_brief_id},
        {"_id": 0},
        sort=[("created_at", -1)]
    )

    if not step_run:
        return {"status": "not_found", "events": [], "progress_pct": 0}

    events = step_run.get("progress", {}).get("events", [])
    status = step_run.get("status", "unknown")
    total_events = max(len(events), 1)
    progress_pct = min(100, int((total_events / 8) * 100)) if status == "running" else (100 if status == "COMPLETED" else 0)

    return {
        "status": status,
        "step_key": step_run.get("step_key"),
        "events": [{"event": e.get("event"), "timestamp": e.get("timestamp")} for e in events[-10:]],
        "progress_pct": progress_pct,
    }


# ============== HISTORY COMPARISON ==============

@api_router.get("/research/{campaign_brief_id}/{module}/compare")
async def compare_module_runs(campaign_brief_id: str, module: str):
    """Compare latest vs previous run for a module, returning delta highlights."""
    module_map = {
        "customer-intel": "customer_intel",
        "search-intent": "search_intent",
        "seasonality": "seasonality",
        "competitors": "competitors",
        "reviews": "reviews",
        "community": "community",
        "press-media": "press_media",
        "social-trends": "social_trends",
        "ads-intel": "ads_intel",
        "creative-analysis": "creative_analysis",
    }
    source_key = module_map.get(module, module)

    pack = await db.research_packs.find_one(
        {"campaign_id": campaign_brief_id}, {"_id": 0}
    )
    if not pack:
        raise HTTPException(status_code=404, detail="No research pack found")

    source = pack.get("sources", {}).get(source_key, {})
    latest = source.get("latest")
    history = source.get("history", [])

    if not latest:
        return {"has_comparison": False, "message": "No current data to compare"}
    if not history:
        return {"has_comparison": False, "message": "Only one run available - no comparison possible yet"}

    previous = history[0] if isinstance(history, list) else history

    def count_items(data):
        counts = {}
        if not isinstance(data, dict):
            return counts
        for key, val in data.items():
            if isinstance(val, list):
                counts[key] = len(val)
            elif isinstance(val, dict):
                for sk, sv in val.items():
                    if isinstance(sv, list):
                        counts[f"{key}.{sk}"] = len(sv)
        return counts

    latest_counts = count_items(latest)
    prev_counts = count_items(previous)

    deltas = []
    all_keys = set(list(latest_counts.keys()) + list(prev_counts.keys()))
    for k in sorted(all_keys):
        lc = latest_counts.get(k, 0)
        pc = prev_counts.get(k, 0)
        diff = lc - pc
        if diff != 0:
            deltas.append({
                "field": k,
                "current": lc,
                "previous": pc,
                "change": diff,
                "direction": "up" if diff > 0 else "down"
            })

    return {
        "has_comparison": True,
        "module": source_key,
        "deltas": deltas,
        "latest_timestamp": source.get("updated_at") or source.get("created_at"),
        "previous_timestamp": previous.get("created_at") if isinstance(previous, dict) else None,
    }


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[
        "http://localhost:3000",
        "https://storage.googleapis.com",
        # Add your deployed frontend URLs here:
        # "https://<your-gcs-staging-bucket>.storage.googleapis.com",
        # "https://<your-gcs-prod-bucket>.storage.googleapis.com",
        # "https://<your-firebase-project>.web.app",
        # "https://<your-firebase-project>.firebaseapp.com",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
