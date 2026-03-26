"""
Novara Step 2: Perplexity Site Summarizer (Final Spec)
Light LLM call to normalize and summarize extracted website signals

Model: Perplexity 'sonar' (light model, cheaper than sonar-pro)
Step 3A uses 'sonar-pro' for richer market intel

Final Spec Feb 2026:
- Updated classification with tags[]
- Strict 2-5 bullets, each <= 90 chars
- 1-3 word chips ONLY for brand_dna
- No testimonials
- No repeated language
"""

import os
import httpx
import json
import logging
from typing import Dict, Optional, Any
import time

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# JSON Schema for LLM output (enforced by Perplexity)
STEP2_LLM_SCHEMA = {
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
- Output VALID JSON only (no markdown).
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

CRITICAL for brand_summary.bullets:
- You MUST return exactly 3-5 bullets. Never return fewer than 3.
- Each bullet must be a DISTINCT fact about the business (not repeated ideas).
- Each bullet <= 90 characters.
- Good bullets are concrete and specific. Examples:
  - "Serves 500+ brides annually across Dubai and Abu Dhabi"
  - "App-based booking with real-time artist availability"
  - "Offers corporate grooming packages for teams of 10+"
  - "Partners with 200+ freelance beauty professionals"
- Bad bullets are vague/generic. Avoid: "Quality service", "Customer satisfaction", "Professional team"."""


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
2) brand_summary: name, one_liner, tagline, and EXACTLY 3-5 bullets (each a distinct concrete fact, no vague/generic statements)
3) brand_dna chips: values[], tone_of_voice[], aesthetic[], visual_vibe[] (1-3 words ONLY)
4) offer summary: value_prop, key_benefits[] (max 5), offer_catalog[]
5) conversion cues: primary_action + destination_type

IMPORTANT: brand_summary.bullets MUST have 3-5 items. Each bullet should be a specific, concrete fact about the business.

If something is missing, return "unknown" or [].

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


class PerplexitySiteSummarizer:
    """
    Client for Perplexity API to summarize website extraction data.
    Uses 'sonar' model (lighter than 'sonar-pro' used in Step 3A).
    """
    
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 2):
        self.api_key = api_key or os.environ.get('PERPLEXITY_API_KEY')
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY is required")
        self.max_retries = max_retries
    
    async def summarize(
        self,
        raw_extraction: Dict,
        pricing: Dict
    ) -> Dict:
        """
        Summarize extracted website data using Perplexity API.
        
        Args:
            raw_extraction: Raw extracted data from extractor
            pricing: Parsed pricing statistics
            
        Returns:
            Dict with normalized data and metadata
        """
        user_prompt = build_user_prompt(raw_extraction, pricing)
        
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
                    "schema": STEP2_LLM_SCHEMA
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[STEP2-LLM] Calling Perplexity sonar (attempt {attempt}/{self.max_retries})...")
                
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
                        logger.error(f"[STEP2-LLM] API error: {response.status_code} - {error_text}")
                        last_error = f"API error: {response.status_code}"
                        continue
                    
                    response_data = response.json()
                    
                    # Extract content
                    content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    logger.info(f"[STEP2-LLM] Response received in {response_duration}s")
                    
                    # Parse JSON
                    try:
                        llm_output = json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"[STEP2-LLM] JSON parse error: {e}")
                        last_error = f"JSON parse error: {e}"
                        continue
                    
                    # Calculate cost estimate
                    usage = response_data.get('usage', {})
                    input_tokens = usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('completion_tokens', 0)
                    # Sonar pricing: ~$0.001 per 1K tokens
                    total_cost = (input_tokens + output_tokens) * 0.001 / 1000
                    
                    # Success - return result
                    return {
                        "llm_output": llm_output,
                        "status": "success",
                        "metadata": {
                            "model": "sonar",
                            "response_duration_seconds": response_duration,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_cost": round(total_cost, 5),
                            "attempt": attempt
                        }
                    }
                    
            except httpx.TimeoutException:
                logger.error(f"[STEP2-LLM] Timeout on attempt {attempt}")
                last_error = "API timeout"
                continue
            except Exception as e:
                logger.exception(f"[STEP2-LLM] Exception on attempt {attempt}: {e}")
                last_error = str(e)
                continue
        
        # All retries failed
        logger.error(f"[STEP2-LLM] All {self.max_retries} attempts failed. Last error: {last_error}")
        raise Exception(f"Step 2 LLM summarization failed after {self.max_retries} attempts: {last_error}")


async def summarize_website_context(
    raw_extraction: Dict,
    pricing: Dict
) -> Dict:
    """
    Convenience function to summarize website context.
    
    Args:
        raw_extraction: Raw extracted data from extractor
        pricing: Parsed pricing statistics
        
    Returns:
        Dict with LLM output and metadata
    """
    summarizer = PerplexitySiteSummarizer()
    return await summarizer.summarize(raw_extraction, pricing)
