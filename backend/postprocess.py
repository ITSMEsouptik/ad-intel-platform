"""
Novara Step 2: Post-processing Rules
Cleans up LLM output to ensure quality and consistency

Rules:
1. Dedupe bullets (remove similar/duplicate items)
2. Validate chips (1-3 words only)
3. Remove nav-title benefits (garbage like "Our Services")
4. Ban unsupported claims (founding year, team size unless extracted)
5. Enforce length limits
"""

import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


# Banned phrases that indicate garbage/filler content
BANNED_PHRASES = [
    # Navigation items
    'our services', 'our products', 'our team', 'about us', 'contact us',
    'learn more', 'read more', 'view more', 'see more', 'click here',
    'home', 'menu', 'services', 'products', 'gallery', 'portfolio',
    
    # Filler phrases
    'aims to', 'bridge the gap', 'all things', 'one-stop shop',
    'wide range of', 'variety of', 'comprehensive range',
    'state of the art', 'cutting edge', 'world class', 'best in class',
    'lorem ipsum', 'placeholder', 'coming soon',
    
    # Unsupported claims (unless explicitly extracted)
    'founded in', 'established in', 'since 19', 'since 20',
    'years of experience', 'team of', 'over', 'more than',
]

# Patterns that look like navigation items
NAV_PATTERNS = [
    r'^(home|about|services|products|contact|blog|faq|pricing|team|gallery|portfolio)$',
    r'^(our|the|your)\s+(services|products|team|story|mission)$',
    r'^(get|view|see|read|learn|click)\s+',
]

# Maximum lengths for different field types
MAX_LENGTHS = {
    'bullet': 90,
    'chip': 30,
    'one_liner': 150,
    'tagline': 100,
    'value_prop': 250,
    'benefit': 90,
    'catalog_name': 60,
    'catalog_description': 120,
}


def clean_bullet(text: str) -> str:
    """Clean a single bullet point"""
    if not text:
        return ''
    
    # Remove leading/trailing whitespace and punctuation
    text = text.strip().strip('•-–—·').strip()
    
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text


def is_valid_bullet(text: str) -> bool:
    """Check if a bullet is valid (not garbage)"""
    if not text or len(text) < 5:
        return False
    
    text_lower = text.lower()
    
    # Check against banned phrases
    for banned in BANNED_PHRASES:
        if banned in text_lower:
            return False
    
    # Check against nav patterns
    for pattern in NAV_PATTERNS:
        if re.match(pattern, text_lower):
            return False
    
    # Must have at least 3 words to be meaningful
    words = text.split()
    if len(words) < 3:
        return False
    
    return True


def is_valid_chip(text: str) -> bool:
    """Check if a chip is valid (1-3 words)"""
    if not text:
        return False
    
    text = text.strip()
    words = text.split()
    
    # Must be 1-3 words
    if not (1 <= len(words) <= 3):
        return False
    
    # Each word should be reasonable length
    if any(len(w) > 15 for w in words):
        return False
    
    # Check against banned phrases
    text_lower = text.lower()
    for banned in BANNED_PHRASES:
        if banned in text_lower:
            return False
    
    return True


def dedupe_list(items: List[str], similarity_threshold: float = 0.7) -> List[str]:
    """Remove duplicates and near-duplicates from a list"""
    if not items:
        return []
    
    result = []
    seen_normalized = set()
    
    for item in items:
        # Normalize for comparison
        normalized = item.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Skip if we've seen this exact text
        if normalized in seen_normalized:
            continue
        
        # Check similarity with existing items
        is_similar = False
        for existing in seen_normalized:
            if _jaccard_similarity(normalized, existing) > similarity_threshold:
                is_similar = True
                break
        
        if not is_similar:
            seen_normalized.add(normalized)
            result.append(item)
    
    return result


def _jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts"""
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max length, preserving word boundaries"""
    if not text or len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    
    # Try to break at word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.7:
        truncated = truncated[:last_space]
    
    return truncated.rstrip('.,;:!? ')


def postprocess_step2_output(llm_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process LLM output to ensure quality.
    
    Args:
        llm_output: Raw output from LLM (matching Step2 schema structure)
        
    Returns:
        Cleaned output
    """
    result = llm_output.copy()
    
    # Process brand_summary
    if 'brand_summary' in result:
        bs = result['brand_summary']
        
        # Clean and validate bullets
        if 'bullets' in bs:
            bullets = [clean_bullet(b) for b in bs['bullets']]
            bullets = [b for b in bullets if is_valid_bullet(b)]
            bullets = dedupe_list(bullets, similarity_threshold=0.5)  # Relaxed from 0.6
            bullets = remove_repeated_language(bullets)
            bullets = [truncate_text(b, MAX_LENGTHS['bullet']) for b in bullets]
            # Ensure minimum 2 bullets survive - if aggressive filtering removed too many,
            # fall back to original cleaned bullets (without dedupe/repeat filtering)
            if len(bullets) < 2:
                fallback_bullets = [clean_bullet(b) for b in bs.get('bullets', [])]
                fallback_bullets = [b for b in fallback_bullets if b and len(b) >= 10]
                fallback_bullets = [truncate_text(b, MAX_LENGTHS['bullet']) for b in fallback_bullets]
                bullets = fallback_bullets[:5] if len(fallback_bullets) >= 2 else bullets
            bs['bullets'] = bullets[:5]  # Max 5 (strict)
        
        # Truncate one_liner and tagline
        if 'one_liner' in bs:
            bs['one_liner'] = truncate_text(bs['one_liner'], MAX_LENGTHS['one_liner'])
        if 'tagline' in bs:
            bs['tagline'] = truncate_text(bs['tagline'], MAX_LENGTHS['tagline'])
    
    # Process brand_dna (chips) - strict 1-3 words
    if 'brand_dna' in result:
        dna = result['brand_dna']
        
        for field in ['values', 'tone_of_voice', 'aesthetic', 'visual_vibe']:
            if field in dna:
                chips = [c.strip() for c in dna[field]]
                chips = [c for c in chips if is_valid_chip(c)]
                chips = validate_chip_format(chips)  # Enforce 1-3 words
                chips = dedupe_list(chips)
                dna[field] = chips[:6]  # Max 6 per category
    
    # Process classification - ensure non-repetitive
    if 'classification' in result:
        cls = result['classification']
        
        # Ensure all fields exist and aren't identical
        industry = cls.get('industry', 'unknown')
        subcategory = cls.get('subcategory', cls.get('sub_industry', 'unknown'))
        niche = cls.get('niche', 'unknown')
        
        # Remove duplication - niche shouldn't repeat industry/subcategory
        if niche.lower() == industry.lower() or niche.lower() == subcategory.lower():
            niche = 'unknown'
        if subcategory.lower() == industry.lower():
            subcategory = 'unknown'
        
        cls['industry'] = industry
        cls['subcategory'] = subcategory
        cls['niche'] = niche
        
        # Validate tags
        if 'tags' in cls:
            tags = [t.strip().lower() for t in cls['tags'] if t and len(t) < 25]
            tags = dedupe_list(tags)
            cls['tags'] = tags[:10]
    
    # Process offer
    if 'offer' in result:
        offer = result['offer']
        
        # Clean key_benefits
        if 'key_benefits' in offer:
            benefits = [clean_bullet(b) for b in offer['key_benefits']]
            benefits = [b for b in benefits if is_valid_bullet(b)]
            benefits = dedupe_list(benefits)
            benefits = remove_repeated_language(benefits)
            benefits = [truncate_text(b, MAX_LENGTHS['benefit']) for b in benefits]
            offer['key_benefits'] = benefits[:5]  # Max 5
        
        # Truncate value_prop
        if 'value_prop' in offer:
            offer['value_prop'] = truncate_text(offer['value_prop'], MAX_LENGTHS['value_prop'])
        
        # Clean offer_catalog
        if 'offer_catalog' in offer:
            catalog = []
            for item in offer['offer_catalog']:
                if isinstance(item, dict) and item.get('name'):
                    cleaned_item = {
                        'name': truncate_text(item.get('name', ''), MAX_LENGTHS['catalog_name']),
                        'description': truncate_text(item.get('description', ''), MAX_LENGTHS['catalog_description']),
                        'price_hint': item.get('price_hint', '')
                    }
                    # Skip if name looks like garbage
                    if is_valid_bullet(cleaned_item['name']) or len(cleaned_item['name'].split()) <= 3:
                        catalog.append(cleaned_item)
            offer['offer_catalog'] = catalog[:20]  # Max 20
    
    # Process conversion
    if 'conversion' in result:
        conv = result['conversion']
        
        # Validate destination_type
        valid_types = ['website', 'whatsapp', 'form', 'app', 'unknown']
        if conv.get('destination_type') not in valid_types:
            conv['destination_type'] = 'unknown'
    
    return result


def validate_chip_format(chips: List[str]) -> List[str]:
    """Ensure chips are 1-3 words only"""
    valid = []
    for chip in chips:
        words = chip.strip().split()
        if 1 <= len(words) <= 3:
            valid.append(' '.join(words))
    return valid


def remove_repeated_language(texts: List[str]) -> List[str]:
    """Remove texts that use repetitive/similar language"""
    if not texts:
        return []
    
    result = []
    used_key_phrases = set()
    
    for text in texts:
        # Extract key phrases (2-3 word combinations)
        words = text.lower().split()
        key_phrases = set()
        
        for i in range(len(words) - 1):
            phrase = ' '.join(words[i:i+2])
            key_phrases.add(phrase)
            if i < len(words) - 2:
                phrase3 = ' '.join(words[i:i+3])
                key_phrases.add(phrase3)
        
        # Check overlap with existing phrases
        overlap = key_phrases & used_key_phrases
        if len(overlap) < 2:  # Allow some overlap
            result.append(text)
            used_key_phrases.update(key_phrases)
    
    return result
