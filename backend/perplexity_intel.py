"""
Novara Step 3A: Perplexity Intel Pack
Market intelligence gathering using Perplexity API with structured JSON output
"""

import os
import httpx
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# JSON Schema for PerplexityIntelPack v1 (modified for 3 competitors)
INTEL_PACK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "PerplexityIntelPackV1",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "category",
        "geo_context",
        "customer_psychology",
        "trust_builders",
        "competitors",
        "foreplay_search_blueprint",
        "angle_seeds",
        "positioning_diagnosis",
        "offer_scorecard_and_quick_wins",
        "channel_and_format_fit",
        "compliance_and_risk_flags",
        "open_questions_for_founder",
        "brand_audit_lite",
        "ui_summary",
        "sources",
        "quality"
    ],
    "properties": {
        "category": {
            "type": "object",
            "additionalProperties": False,
            "required": ["industry", "subcategory", "confidence_0_100", "notes"],
            "properties": {
                "industry": {"type": "string", "maxLength": 60},
                "subcategory": {"type": "string", "maxLength": 80},
                "confidence_0_100": {"type": "integer", "minimum": 0, "maximum": 100},
                "notes": {"type": "string", "maxLength": 180}
            }
        },
        "geo_context": {
            "type": "object",
            "additionalProperties": False,
            "required": ["primary_market", "seasonality_or_moments", "local_behavior_notes"],
            "properties": {
                "primary_market": {"type": "string", "maxLength": 80},
                "seasonality_or_moments": {
                    "type": "array",
                    "maxItems": 8,
                    "items": {"type": "string", "maxLength": 40}
                },
                "local_behavior_notes": {
                    "type": "array",
                    "maxItems": 8,
                    "items": {"type": "string", "maxLength": 90}
                }
            }
        },
        "customer_psychology": {
            "type": "object",
            "additionalProperties": False,
            "required": ["icp_segments", "top_pains", "top_objections", "buying_triggers"],
            "properties": {
                "icp_segments": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "description", "top_motivations", "preferred_proof", "cta_style_notes"],
                        "properties": {
                            "name": {"type": "string", "maxLength": 50},
                            "description": {"type": "string", "maxLength": 90},
                            "top_motivations": {
                                "type": "array",
                                "maxItems": 5,
                                "items": {"type": "string", "maxLength": 60}
                            },
                            "preferred_proof": {
                                "type": "array",
                                "maxItems": 5,
                                "items": {"type": "string", "maxLength": 40}
                            },
                            "cta_style_notes": {
                                "type": "array",
                                "maxItems": 4,
                                "items": {"type": "string", "maxLength": 60}
                            }
                        }
                    }
                },
                "top_pains": {"type": "array", "minItems": 3, "maxItems": 6, "items": {"type": "string", "maxLength": 70}},
                "top_objections": {"type": "array", "minItems": 3, "maxItems": 6, "items": {"type": "string", "maxLength": 70}},
                "buying_triggers": {"type": "array", "minItems": 2, "maxItems": 5, "items": {"type": "string", "maxLength": 70}}
            }
        },
        "trust_builders": {
            "type": "object",
            "additionalProperties": False,
            "required": ["most_credible_proof_types", "category_specific_trust_signals", "risk_reducers"],
            "properties": {
                "most_credible_proof_types": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 40}},
                "category_specific_trust_signals": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 60}},
                "risk_reducers": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 60}}
            }
        },
        "competitors": {
            "type": "array",
            "minItems": 2,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "website", "instagram", "tiktok", "positioning_summary"],
                "properties": {
                    "name": {"type": "string", "maxLength": 60},
                    "website": {"type": "string", "maxLength": 200},
                    "instagram": {"type": "string", "maxLength": 200},
                    "tiktok": {"type": "string", "maxLength": 200},
                    "positioning_summary": {"type": "string", "maxLength": 90}
                }
            }
        },
        "foreplay_search_blueprint": {
            "type": "object",
            "additionalProperties": False,
            "required": ["competitor_queries", "keyword_queries", "angle_queries", "negative_filters", "notes"],
            "properties": {
                "competitor_queries": {"type": "array", "minItems": 3, "maxItems": 6, "items": {"type": "string", "maxLength": 40}},
                "keyword_queries": {"type": "array", "minItems": 3, "maxItems": 6, "items": {"type": "string", "maxLength": 40}},
                "angle_queries": {"type": "array", "minItems": 3, "maxItems": 6, "items": {"type": "string", "maxLength": 40}},
                "negative_filters": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 30}},
                "notes": {"type": "string", "maxLength": 180}
            }
        },
        "angle_seeds": {
            "type": "object",
            "additionalProperties": False,
            "required": ["hook_families", "trust_themes", "conversion_angles"],
            "properties": {
                "hook_families": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 40}},
                "trust_themes": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 40}},
                "conversion_angles": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 40}}
            }
        },
        "positioning_diagnosis": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "current_promise_one_liner",
                "who_its_for_inferred",
                "differentiation_strength_0_10",
                "generic_claims_found",
                "potential_whitespace_gaps",
                "evidence_snippets",
                "confidence_0_100"
            ],
            "properties": {
                "current_promise_one_liner": {"type": "string", "maxLength": 90},
                "who_its_for_inferred": {"type": "string", "maxLength": 70},
                "differentiation_strength_0_10": {"type": "integer", "minimum": 0, "maximum": 10},
                "generic_claims_found": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 50}},
                "potential_whitespace_gaps": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 60}},
                "evidence_snippets": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 60}},
                "confidence_0_100": {"type": "integer", "minimum": 0, "maximum": 100}
            }
        },
        "offer_scorecard_and_quick_wins": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "offer_clarity_score_0_10",
                "what_is_clear",
                "what_is_unclear_or_missing",
                "conversion_friction_hypotheses",
                "quick_wins_copy",
                "quick_wins_proof",
                "quick_wins_structure",
                "evidence_snippets",
                "confidence_0_100"
            ],
            "properties": {
                "offer_clarity_score_0_10": {"type": "integer", "minimum": 0, "maximum": 10},
                "what_is_clear": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 70}},
                "what_is_unclear_or_missing": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 70}},
                "conversion_friction_hypotheses": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 80}},
                "quick_wins_copy": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 90}},
                "quick_wins_proof": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 90}},
                "quick_wins_structure": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 90}},
                "evidence_snippets": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 60}},
                "confidence_0_100": {"type": "integer", "minimum": 0, "maximum": 100}
            }
        },
        "channel_and_format_fit": {
            "type": "object",
            "additionalProperties": False,
            "required": ["channel_rankings", "format_rankings", "budget_tight_notes", "confidence_0_100"],
            "properties": {
                "channel_rankings": {
                    "type": "array",
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["channel", "why"],
                        "properties": {
                            "channel": {"type": "string", "enum": ["meta", "google_search", "tiktok", "youtube", "linkedin", "other"]},
                            "why": {"type": "string", "maxLength": 90}
                        }
                    }
                },
                "format_rankings": {
                    "type": "array",
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["format", "why"],
                        "properties": {
                            "format": {
                                "type": "string",
                                "enum": [
                                    "ugc_talking_head",
                                    "before_after",
                                    "text_on_screen",
                                    "founder_story",
                                    "testimonial",
                                    "product_demo",
                                    "static_carousel",
                                    "other"
                                ]
                            },
                            "why": {"type": "string", "maxLength": 90}
                        }
                    }
                },
                "budget_tight_notes": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 90}},
                "confidence_0_100": {"type": "integer", "minimum": 0, "maximum": 100}
            }
        },
        "compliance_and_risk_flags": {
            "type": "object",
            "additionalProperties": False,
            "required": ["claim_risks", "policy_sensitivities", "safe_claim_alternatives", "confidence_0_100"],
            "properties": {
                "claim_risks": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 70}},
                "policy_sensitivities": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 70}},
                "safe_claim_alternatives": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 80}},
                "confidence_0_100": {"type": "integer", "minimum": 0, "maximum": 100}
            }
        },
        "open_questions_for_founder": {
            "type": "array",
            "minItems": 3,
            "maxItems": 6,
            "items": {"type": "string", "maxLength": 90}
        },
        "brand_audit_lite": {
            "type": "object",
            "additionalProperties": False,
            "required": ["voice", "archetype", "visual_vibe", "brand_gaps"],
            "properties": {
                "voice": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["traits", "do_list", "dont_list", "cta_style_notes", "evidence_snippets", "confidence_0_100"],
                    "properties": {
                        "traits": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 24}},
                        "do_list": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 90}},
                        "dont_list": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 90}},
                        "cta_style_notes": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 60}},
                        "evidence_snippets": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 60}},
                        "confidence_0_100": {"type": "integer", "minimum": 0, "maximum": 100}
                    }
                },
                "archetype": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["primary", "secondary", "confidence_0_100", "evidence_snippets"],
                    "properties": {
                        "primary": {
                            "type": "string",
                            "enum": ["caregiver", "ruler", "creator", "everyman", "explorer", "sage", "hero", "lover", "jester", "magician", "innocent", "outlaw", "unknown"]
                        },
                        "secondary": {
                            "type": "string",
                            "enum": ["caregiver", "ruler", "creator", "everyman", "explorer", "sage", "hero", "lover", "jester", "magician", "innocent", "outlaw", "unknown"]
                        },
                        "confidence_0_100": {"type": "integer", "minimum": 0, "maximum": 100},
                        "evidence_snippets": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 60}}
                    }
                },
                "visual_vibe": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["vibe_keywords", "imagery_style_notes", "visual_constraints", "ad_style_fit_notes", "evidence_snippets", "confidence_0_100"],
                    "properties": {
                        "vibe_keywords": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 24}},
                        "imagery_style_notes": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 80}},
                        "visual_constraints": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 80}},
                        "ad_style_fit_notes": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 80}},
                        "evidence_snippets": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 60}},
                        "confidence_0_100": {"type": "integer", "minimum": 0, "maximum": 100}
                    }
                },
                "brand_gaps": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["what_brand_signals_today", "clarity_gaps", "consistency_gaps", "confidence_0_100"],
                    "properties": {
                        "what_brand_signals_today": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 80}},
                        "clarity_gaps": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 80}},
                        "consistency_gaps": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 80}},
                        "confidence_0_100": {"type": "integer", "minimum": 0, "maximum": 100}
                    }
                }
            }
        },
        "ui_summary": {
            "type": "object",
            "additionalProperties": False,
            "required": ["cards"],
            "properties": {
                "cards": {
                    "type": "array",
                    "minItems": 5,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "title", "chips", "bullets"],
                        "properties": {
                            "id": {"type": "string", "enum": ["category", "competitors", "customer_reality", "brand_vibe", "quick_wins"]},
                            "title": {"type": "string", "maxLength": 30},
                            "chips": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 24}},
                            "bullets": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 90}}
                        }
                    }
                }
            }
        },
        "sources": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "url"],
                "properties": {
                    "title": {"type": "string", "maxLength": 120},
                    "url": {"type": "string", "maxLength": 300}
                }
            }
        },
        "quality": {
            "type": "object",
            "additionalProperties": False,
            "required": ["warnings", "errors"],
            "properties": {
                "warnings": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 120}},
                "errors": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 120}}
            }
        }
    }
}

SYSTEM_PROMPT = """You are a Market Intelligence Analyst for an advertising and growth platform.
You are gathering market + competitor intelligence and auditing brand signals.
You are NOT producing a marketing strategy or plan yet.

Primary objective:
Return an INSIGHT PACK that is structured, skimmable, and usable for:
(1) competitor discovery + ad library search queries, and
(2) later synthesis into hypotheses and creatives.

Hard output rules:
- Output MUST be valid JSON that matches the provided JSON Schema.
- Output ONLY JSON. No markdown, no commentary, no extra keys.
- Prefer arrays/lists over paragraphs. No long blocks of text.
- Chips must be 1–3 words each.
- Bullets must be short and direct (<= 90 characters).
- Use simple, concrete language. Avoid jargon.

Evidence & accuracy rules:
- Do not invent facts. If unknown or not supported, use "unknown" or [] and lower confidence.
- Include confidence_0_100 where the schema asks.
- evidence_snippets must be short phrases (<= 12 words), grounded in:
  (a) provided brand context, and/or (b) web search results.

Competitor discovery rules:
- Find 2-3 true competitors (same category + similar offer).
- Avoid directories/marketplaces/aggregators unless they are dominant direct alternatives.
- Include official websites and social handles only when reasonably confident.

Search blueprint rules (for ad libraries):
- Queries must be short (2–7 words).
- Include competitor-name queries + keyword queries + angle/format queries.
- Provide negative_filters to reduce irrelevant results.

Scope rules:
- Allowed: market patterns, competitor list, category norms, proof types, channel/format tendencies,
  brand voice/vibe audit, gaps/diagnosis, open questions to reduce uncertainty.
- Not allowed: budgets, exact campaign plans, hypotheses, creative scripts, or final recommendations.

If there is any ambiguity, choose the most conservative interpretation and set confidence lower."""


def build_user_prompt(brief: Dict, pack: Dict) -> str:
    """Build the user prompt from CampaignBrief and WebsiteContextPack"""
    
    # Extract from brief
    website_url = brief.get('brand', {}).get('website_url', 'unknown')
    geo_country = brief.get('geo', {}).get('country', 'unknown')
    geo_city = brief.get('geo', {}).get('city_or_region', 'unknown')
    primary_goal = brief.get('goal', {}).get('primary_goal', 'unknown')
    success_definition = brief.get('goal', {}).get('success_definition', 'unknown')
    budget_range = brief.get('budget_range_monthly', 'unknown')
    destination_type = brief.get('destination', {}).get('type', 'unknown')
    
    # Extract from website context pack - support both new (step2) and old (data) formats
    step2 = pack.get('step2', {}) if pack else {}
    pack_data = pack.get('data', {}) if pack else {}
    
    # Use new format if available, else fall back to old format
    if step2:
        brand_summary = step2.get('brand_summary', {})
        offer = step2.get('offer', {})
        conversion = step2.get('conversion', {})
        site = step2.get('site', {})
        
        brand_name = brand_summary.get('name', 'unknown')
        offer_summary = offer.get('value_prop', 'unknown')
        key_benefits = ', '.join(offer.get('key_benefits', [])) or 'none found'
        differentiators = 'none found'  # Not in new schema
        pricing_mentions = 'none found'  # Pricing is structured in new schema
        detected_ctas = ', '.join(conversion.get('ctas', [])) or 'none found'
        primary_action = conversion.get('primary_action', 'unknown')
        trust_signals = 'none found'  # Not in new schema
        social_links = json.dumps(step2.get('channels', {}).get('social', []))
    else:
        brand_identity = pack_data.get('brand_identity', {})
        offer = pack_data.get('offer', {})
        conversion = pack_data.get('conversion', {})
        proof = pack_data.get('proof', {})
        site = pack_data.get('site', {})
        
        brand_name = brand_identity.get('brand_name', 'unknown')
        offer_summary = offer.get('primary_offer_summary', 'unknown')
        key_benefits = ', '.join(offer.get('key_benefits', [])) or 'none found'
        differentiators = ', '.join(offer.get('differentiators', [])) or 'none found'
        pricing_mentions = ', '.join(offer.get('pricing_mentions', [])) or 'none found'
        detected_ctas = ', '.join(conversion.get('detected_primary_ctas', [])) or 'none found'
        primary_action = conversion.get('primary_action', 'unknown')
        trust_signals = ', '.join(proof.get('trust_signals', [])) or 'none found'
        social_links = json.dumps(site.get('social_links', {}))
    
    return f"""Return the PerplexityIntelPack JSON object matching the provided JSON Schema.

Brand context:
- Website: {website_url}
- Geo: {geo_country}, {geo_city}
- Goal: {primary_goal}
- Success definition: {success_definition}
- Monthly budget range: {budget_range}
- Destination type: {destination_type}

Known brand facts (from website extraction):
- Brand name: {brand_name}
- Offer summary: {offer_summary}
- Key benefits: {key_benefits}
- Differentiators: {differentiators}
- Pricing mentions: {pricing_mentions}
- Detected CTAs: {detected_ctas}
- Primary action: {primary_action}
- Trust signals found: {trust_signals}
- Social links: {social_links}

Tasks (follow the schema):
1) Validate industry + subcategory with confidence.
2) Customer psychology: ICP segments (2-4), pains, objections, triggers.
3) Trust builders: credible proof types, trust signals, risk reducers.
4) Competitors (2-3): include website + IG/TikTok when available.
5) Foreplay search blueprint:
   - competitor_queries, keyword_queries, angle_queries, negative_filters
   - each query must be 2–7 words
6) Brand audit lite (grounded in website cues):
   - voice traits + do/don't
   - archetype only if confidence >= 60 else "unknown"
   - visual vibe descriptors + brand gaps
7) Open questions for founder (3-6): uncertainty reducers only.
8) Populate ui_summary.cards (5 cards total).
   - bullets <= 90 chars
   - chips 1–3 words

Output ONLY JSON matching the schema."""


class PerplexityIntelClient:
    """Client for Perplexity API to generate Intel Packs"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('PERPLEXITY_API_KEY')
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY is required")
    
    async def generate_intel_pack(
        self,
        campaign_brief: Dict,
        website_context_pack: Dict,
        intel_pack_id: str,
        retry_on_failure: bool = True
    ) -> Dict:
        """Generate PerplexityIntelPack using Perplexity API"""
        
        user_prompt = build_user_prompt(campaign_brief, website_context_pack)
        
        request_payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 4000,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "schema": INTEL_PACK_SCHEMA
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info("[STEP3A] Calling Perplexity API...")
        
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                # Track start time for duration measurement
                import time
                start_time = time.time()
                
                response = await client.post(
                    PERPLEXITY_API_URL,
                    json=request_payload,
                    headers=headers
                )
                
                # Calculate response duration
                end_time = time.time()
                response_duration_seconds = round(end_time - start_time, 2)
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"[STEP3A] Perplexity API error: {response.status_code} - {error_text}")
                    raise Exception(f"Perplexity API error: {response.status_code}")
                
                response_data = response.json()
                
                # Store raw API response for debugging
                raw_api_response = {
                    "status_code": response.status_code,
                    "response_body": response_data,
                    "response_duration_seconds": response_duration_seconds,
                    "request_timestamp": datetime.now(timezone.utc).isoformat(),
                    "model": response_data.get('model', 'unknown'),
                    "usage": response_data.get('usage', {}),
                    "citations": response_data.get('citations', [])
                }
                
                logger.info(f"[STEP3A] Response received in {response_duration_seconds}s")
                
                # Extract content and search results
                content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                search_results = response_data.get('search_results', [])
                
                logger.info(f"[STEP3A] Received response, parsing JSON...")
                
                # Parse JSON
                try:
                    intel_data = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"[STEP3A] JSON parse error: {e}")
                    if retry_on_failure:
                        logger.info("[STEP3A] Retrying with repair prompt...")
                        return await self._retry_with_repair(campaign_brief, website_context_pack, intel_pack_id)
                    raise
                
                # Add server-side fields
                intel_data['intel_pack_id'] = intel_pack_id
                intel_data['campaign_brief_id'] = campaign_brief.get('campaign_brief_id', '')
                intel_data['created_at'] = datetime.now(timezone.utc).isoformat()
                
                # Merge search results into sources if available
                if search_results:
                    intel_data['sources'] = [
                        {"title": sr.get('title', ''), "url": sr.get('url', '')}
                        for sr in search_results[:10]
                    ]
                
                logger.info(f"[STEP3A] Intel pack generated successfully")
                
                return {
                    "intel_pack": intel_data,
                    "search_results": search_results,
                    "raw_api_response": raw_api_response,
                    "raw_content": content,
                    "status": "success"
                }
                
            except httpx.TimeoutException:
                logger.error("[STEP3A] Perplexity API timeout")
                raise Exception("Perplexity API timeout")
    
    async def _retry_with_repair(
        self,
        campaign_brief: Dict,
        website_context_pack: Dict,
        intel_pack_id: str
    ) -> Dict:
        """Retry with a repair prompt"""
        
        user_prompt = build_user_prompt(campaign_brief, website_context_pack)
        user_prompt += "\n\nIMPORTANT: Your last output failed JSON schema validation. Output valid JSON only."
        
        request_payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "schema": INTEL_PACK_SCHEMA
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                PERPLEXITY_API_URL,
                json=request_payload,
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Perplexity API retry failed: {response.status_code}")
            
            response_data = response.json()
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            search_results = response_data.get('search_results', [])
            
            intel_data = json.loads(content)
            intel_data['intel_pack_id'] = intel_pack_id
            intel_data['campaign_brief_id'] = campaign_brief.get('campaign_brief_id', '')
            intel_data['created_at'] = datetime.now(timezone.utc).isoformat()
            
            if search_results:
                intel_data['sources'] = [
                    {"title": sr.get('title', ''), "url": sr.get('url', '')}
                    for sr in search_results[:10]
                ]
            
            return {
                "intel_pack": intel_data,
                "search_results": search_results,
                "status": "success"
            }
