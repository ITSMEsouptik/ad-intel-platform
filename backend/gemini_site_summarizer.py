"""
Novara Step 2: Site Summarizer with Fallback
Primary: Gemini 2.5 Flash (via Google AI SDK with user's API key) - cheaper
Fallback: Perplexity Sonar - more reliable JSON schema enforcement

Strategy: Try Gemini first (user's key, no budget limits), fall back to Perplexity if needed
"""

import os
import json
import logging
import time
import asyncio
import httpx
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# Gemini-compatible schema (no additionalProperties, maxLength, minItems, maxItems)
GEMINI_SCHEMA = {
    "type": "object",
    "required": ["classification", "brand_summary", "brand_dna", "offer", "conversion"],
    "properties": {
        "classification": {
            "type": "object",
            "required": ["industry", "subcategory", "niche"],
            "properties": {
                "industry": {"type": "string"},
                "subcategory": {"type": "string"},
                "niche": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}}
            }
        },
        "brand_summary": {
            "type": "object",
            "required": ["name", "one_liner", "bullets"],
            "properties": {
                "name": {"type": "string"},
                "tagline": {"type": "string"},
                "one_liner": {"type": "string"},
                "bullets": {"type": "array", "items": {"type": "string"}}
            }
        },
        "brand_dna": {
            "type": "object",
            "required": ["values", "tone_of_voice", "aesthetic", "visual_vibe"],
            "properties": {
                "values": {"type": "array", "items": {"type": "string"}},
                "tone_of_voice": {"type": "array", "items": {"type": "string"}},
                "aesthetic": {"type": "array", "items": {"type": "string"}},
                "visual_vibe": {"type": "array", "items": {"type": "string"}}
            }
        },
        "offer": {
            "type": "object",
            "required": ["value_prop", "key_benefits"],
            "properties": {
                "value_prop": {"type": "string"},
                "key_benefits": {"type": "array", "items": {"type": "string"}},
                "offer_catalog": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "price_hint": {"type": "string"}
                        }
                    }
                }
            }
        },
        "conversion": {
            "type": "object",
            "required": ["primary_action", "destination_type"],
            "properties": {
                "primary_action": {"type": "string"},
                "destination_type": {
                    "type": "string",
                    "enum": ["website", "whatsapp", "form", "app", "unknown"]
                }
            }
        }
    }
}

# Strict JSON Schema for Perplexity (enforced by the API)
PERPLEXITY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["classification", "brand_summary", "brand_dna", "offer", "conversion"],
    "properties": {
        "classification": {
            "type": "object",
            "additionalProperties": False,
            "required": ["industry", "subcategory", "niche"],
            "properties": {
                "industry": {"type": "string", "maxLength": 50},
                "subcategory": {"type": "string", "maxLength": 60},
                "niche": {"type": "string", "maxLength": 80},
                "tags": {
                    "type": "array",
                    "maxItems": 8,
                    "items": {"type": "string", "maxLength": 25}
                }
            }
        },
        "brand_summary": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "one_liner", "bullets"],
            "properties": {
                "name": {"type": "string", "maxLength": 60},
                "tagline": {"type": "string", "maxLength": 100},
                "one_liner": {"type": "string", "maxLength": 150},
                "bullets": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 5,
                    "items": {"type": "string", "maxLength": 90}
                }
            }
        },
        "brand_dna": {
            "type": "object",
            "additionalProperties": False,
            "required": ["values", "tone_of_voice", "aesthetic", "visual_vibe"],
            "properties": {
                "values": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {"type": "string", "maxLength": 25}
                },
                "tone_of_voice": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {"type": "string", "maxLength": 25}
                },
                "aesthetic": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {"type": "string", "maxLength": 25}
                },
                "visual_vibe": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {"type": "string", "maxLength": 25}
                }
            }
        },
        "offer": {
            "type": "object",
            "additionalProperties": False,
            "required": ["value_prop", "key_benefits"],
            "properties": {
                "value_prop": {"type": "string", "maxLength": 200},
                "key_benefits": {
                    "type": "array",
                    "maxItems": 5,
                    "items": {"type": "string", "maxLength": 90}
                },
                "offer_catalog": {
                    "type": "array",
                    "maxItems": 15,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string", "maxLength": 60},
                            "description": {"type": "string", "maxLength": 100},
                            "price_hint": {"type": "string", "maxLength": 30}
                        }
                    }
                }
            }
        },
        "conversion": {
            "type": "object",
            "additionalProperties": False,
            "required": ["primary_action", "destination_type"],
            "properties": {
                "primary_action": {"type": "string", "maxLength": 50},
                "destination_type": {
                    "type": "string",
                    "enum": ["website", "whatsapp", "form", "app", "unknown"]
                }
            }
        }
    }
}

SYSTEM_PROMPT = """You are a website context normalizer.
Your job: turn messy extracted website data into a clean Brand DNA summary for creative research.
Do NOT do competitor research. Do NOT write marketing strategy.
Be precise. Avoid repetition. If uncertain, use "unknown" or [].

Hard rules:
- Output VALID JSON only (no markdown, no code blocks, no explanation).
- Chips (values, tone_of_voice, aesthetic, visual_vibe) must be 1-3 words each. Examples: "Luxurious", "Bold & Modern", "Warm Friendly".
- Do not repeat the same idea across bullets/benefits.
- Prefer concrete, non-generic statements.
- If evidence is not present in input, do not invent it.
- Classification must be a meaningful 3-tier hierarchy:
  - industry: Broad (e.g., "Beauty & Wellness")
  - subcategory: Mid (e.g., "On-demand Beauty Services")
  - niche: Specific (e.g., "At-home Hair & Makeup Dubai")
  - tags[]: Optional keywords (e.g., ["bridal", "home service"])
- Niche should NOT just be the brand name or H1.

CRITICAL for brand_summary.name:
- This MUST be the clean brand name (e.g., "Instaglam", "Nike", "Airbnb").
- Do NOT use the HTML page title (e.g., "Hair & Makeup Home Service Dubai | Instaglambeauty.com").
- Do NOT include location, tagline, or domain in the name.
- Extract the brand name from the website content, logo text, or domain name.

CRITICAL for brand_summary.bullets:
- You MUST return exactly 3-5 bullets. Never return fewer than 3.
- Each bullet must be a DISTINCT fact about the business (not repeated ideas).
- Each bullet <= 90 characters.
- Good bullets are concrete and specific. Examples:
  - "Serves 500+ brides annually across Dubai and Abu Dhabi"
  - "App-based booking with real-time artist availability"
  - "Offers corporate grooming packages for teams of 10+"
  - "Partners with 200+ freelance beauty professionals"
- Bad bullets are vague/generic. Avoid: "Quality service", "Customer satisfaction", "Professional team".

CRITICAL for brand_dna:
- values: 3-5 items like "Convenience", "Empowerment", "Quality"
- tone_of_voice: 3-5 items like "Friendly", "Professional", "Modern"
- aesthetic: 3-5 items like "Clean", "Feminine", "Minimal"
- visual_vibe: 3-5 items like "Soft Pink", "White Space", "Lifestyle"

CRITICAL for offer:
- value_prop: One sentence summarizing the core value (not "unknown")
- key_benefits: 3-5 specific benefits"""


def build_user_prompt(raw_extraction: Dict, pricing: Dict) -> str:
    """Build the user prompt with extraction data"""
    
    site = raw_extraction.get('site', {})
    
    # Limit arrays to prevent token overflow
    text_chunks = raw_extraction.get('text_chunks', [])[:12]
    headings = raw_extraction.get('headings', [])[:15]
    ctas = raw_extraction.get('ctas', [])[:10]
    
    # Format pricing info
    pricing_info = "No pricing detected"
    if pricing.get('count', 0) > 0:
        pricing_info = f"""Currency: {pricing.get('currency', 'unknown')}
Range: {pricing.get('min', 0)} - {pricing.get('max', 0)}
Average: {pricing.get('avg', 0)}
Count: {pricing.get('count', 0)}"""
    
    return f"""Convert this raw website extraction into Step2Public JSON.

Requirements:
1) classification: industry, subcategory, niche, tags[] (meaningful hierarchy, not repetitive)
2) brand_summary: name, one_liner, tagline, and EXACTLY 3-5 bullets (each a distinct concrete fact)
3) brand_dna chips: values[], tone_of_voice[], aesthetic[], visual_vibe[] (3-5 items each, 1-3 words per item)
4) offer summary: value_prop (one clear sentence), key_benefits[] (3-5 items), offer_catalog[]
5) conversion cues: primary_action + destination_type

IMPORTANT: All arrays (bullets, values, tone_of_voice, aesthetic, visual_vibe, key_benefits) must have 3-5 items each. Do NOT return empty arrays.

If something is genuinely missing from the website, use "unknown" for strings but still provide reasonable inferences for arrays.

SITE INFO:
- URL: {site.get('final_url', 'unknown')}
- Title: {site.get('title', 'unknown')}
- Description: {site.get('meta_description', 'unknown')}

TEXT CONTENT:
{chr(10).join(f'- {chunk}' for chunk in text_chunks)}

HEADINGS:
{chr(10).join(f'- {h}' for h in headings)}

CALL-TO-ACTIONS:
{chr(10).join(f'- {cta}' for cta in ctas)}

PRICING:
{pricing_info}

SOCIAL LINKS:
{json.dumps(raw_extraction.get('social_links', {}), indent=2)}

Return ONLY valid JSON. No commentary or explanation."""


def _patch_missing_fields(llm_output: Dict) -> Dict:
    """Fill in missing top-level fields with sensible defaults instead of
    discarding a mostly-complete response and paying for a second LLM call."""
    defaults = {
        "classification": {"industry": "unknown", "subcategory": "", "niche": "", "tags": []},
        "brand_summary": {"name": "", "tagline": "", "one_liner": "", "bullets": []},
        "brand_dna": {"values": [], "tone_of_voice": [], "aesthetic": [], "visual_vibe": []},
        "offer": {"value_prop": "", "key_benefits": [], "offer_catalog": []},
        "conversion": {"primary_action": "Visit website", "destination_type": "website", "ctas": []},
    }
    patched = False
    for field, default in defaults.items():
        if field not in llm_output:
            llm_output[field] = default
            logger.info(f"[VALIDATE] Patched missing field '{field}' with default")
            patched = True
    return llm_output


def is_response_complete(llm_output: Dict) -> bool:
    """Check if the LLM response has enough core content to be usable.
    Missing top-level fields are patched, not rejected."""
    
    # Patch any missing top-level fields
    _patch_missing_fields(llm_output)
    
    # Check brand_summary has bullets (core content)
    bullets = llm_output.get('brand_summary', {}).get('bullets', [])
    if len(bullets) < 2:
        logger.warning(f"[VALIDATE] Too few bullets: {len(bullets)}")
        return False
    
    # Check brand_dna has content
    brand_dna = llm_output.get('brand_dna', {})
    dna_fields = ['values', 'tone_of_voice', 'aesthetic', 'visual_vibe']
    empty_dna = sum(1 for f in dna_fields if len(brand_dna.get(f, [])) == 0)
    if empty_dna >= 3:
        logger.warning(f"[VALIDATE] Brand DNA mostly empty: {empty_dna}/4 fields empty")
        return False
    
    # Check offer has value_prop
    value_prop = llm_output.get('offer', {}).get('value_prop', 'unknown')
    if value_prop == 'unknown' or not value_prop:
        logger.warning("[VALIDATE] Offer value_prop is unknown/empty")
        return False
    
    return True


async def summarize_with_gemini(user_prompt: str, api_key: str) -> Optional[Dict]:
    """Try to summarize using Gemini 3 Flash with user's own API key.
    Includes retry with backoff on 429 rate limit."""
    from google import genai
    from google.genai import types
    
    for attempt in range(2):
        try:
            if attempt == 0:
                logger.info("[STEP2-LLM] Trying Gemini 2.5 Flash (user's API key)...")
            else:
                logger.info("[STEP2-LLM] Gemini retry after backoff...")
            
            start_time = time.time()
            client = genai.Client(api_key=api_key)
            full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2000,
                    response_mime_type="application/json",
                    response_schema=GEMINI_SCHEMA,
                )
            )
            
            end_time = time.time()
            response_duration = round(end_time - start_time, 2)
            logger.info(f"[STEP2-LLM] Gemini response received in {response_duration}s")
            
            content = response.text.strip()
            if content.startswith('```'):
                lines = content.split('\n')
                lines = [line for line in lines if not line.startswith('```')]
                content = '\n'.join(lines)
            
            llm_output = json.loads(content)
            
            if not is_response_complete(llm_output):
                logger.warning("[STEP2-LLM] Gemini response incomplete, will try fallback")
                return None
            
            return {
                "llm_output": llm_output,
                "status": "success",
                "metadata": {
                    "model": "gemini-2.5-flash",
                    "response_duration_seconds": response_duration,
                    "provider": "google-ai-studio"
                }
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"[STEP2-LLM] Gemini JSON parse error: {e}")
            return None
        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                if attempt == 0:
                    logger.warning("[STEP2-LLM] Gemini 429 rate limit, retrying in 3s...")
                    await asyncio.sleep(3)
                    continue
                else:
                    logger.error("[STEP2-LLM] Gemini 429 persists after retry, falling back")
                    return None
            logger.error(f"[STEP2-LLM] Gemini error: {e}")
            return None
    return None


async def summarize_with_perplexity(user_prompt: str, api_key: str) -> Dict:
    """Fallback to Perplexity Sonar with strict JSON schema"""
    logger.info("[STEP2-LLM] Using Perplexity Sonar (fallback)...")
    
    request_payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1500,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "schema": PERPLEXITY_SCHEMA
            }
        }
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            PERPLEXITY_API_URL,
            json=request_payload,
            headers=headers
        )
        
        end_time = time.time()
        response_duration = round(end_time - start_time, 2)
        
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"[STEP2-LLM] Perplexity API error: {response.status_code} - {error_text}")
            raise Exception(f"Perplexity API error: {response.status_code}")
        
        response_data = response.json()
        content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        logger.info(f"[STEP2-LLM] Perplexity response received in {response_duration}s")
        
        llm_output = json.loads(content)
        
        # Calculate cost estimate
        usage = response_data.get('usage', {})
        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)
        
        return {
            "llm_output": llm_output,
            "status": "success",
            "metadata": {
                "model": "sonar",
                "response_duration_seconds": response_duration,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "provider": "perplexity"
            }
        }


async def summarize_website_context(
    raw_extraction: Dict,
    pricing: Dict
) -> Dict:
    """
    Summarize website context using Gemini (primary) with Perplexity fallback.
    
    Strategy:
    1. Try Gemini with user's GOOGLE_AI_STUDIO_KEY (cheaper, no budget limits)
    2. If Gemini fails or returns incomplete data, fall back to Perplexity Sonar
    
    Args:
        raw_extraction: Raw extracted data from extractor
        pricing: Parsed pricing statistics
        
    Returns:
        Dict with LLM output and metadata
    """
    user_prompt = build_user_prompt(raw_extraction, pricing)
    
    google_key = os.environ.get('GOOGLE_AI_STUDIO_KEY')
    perplexity_key = os.environ.get('PERPLEXITY_API_KEY')
    
    # Try Gemini first if we have the user's Google AI key
    if google_key:
        result = await summarize_with_gemini(user_prompt, google_key)
        if result:
            logger.info("[STEP2-LLM] Gemini succeeded (user's API key)")
            return result
        logger.warning("[STEP2-LLM] Gemini failed, falling back to Perplexity")
    
    # Fall back to Perplexity
    if not perplexity_key:
        raise ValueError("No LLM API key available (need GOOGLE_AI_STUDIO_KEY or PERPLEXITY_API_KEY)")
    
    result = await summarize_with_perplexity(user_prompt, perplexity_key)
    logger.info("[STEP2-LLM] Perplexity succeeded")
    return result
