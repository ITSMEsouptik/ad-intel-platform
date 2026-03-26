"""
Novara Step 2: Pricing Parser (Updated)
Parses price strings and computes min/max/avg stats with currency detection
Now includes observed_prices with source_url for tracking
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import logging
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class ObservedPrice:
    """Single observed price with source"""
    value: float
    currency: str
    raw: str
    source_url: str = "unknown"
    
    def to_dict(self) -> Dict:
        return {
            "value": self.value,
            "currency": self.currency,
            "raw": self.raw,
            "source_url": self.source_url
        }


@dataclass
class PricingResult:
    """Parsed pricing statistics with observed prices"""
    currency: str = "unknown"
    count: int = 0
    min: float = 0
    avg: float = 0
    max: float = 0
    observed_prices: List[ObservedPrice] = field(default_factory=list)
    notes: str = "unknown"
    
    def to_dict(self) -> Dict:
        return {
            "currency": self.currency,
            "count": self.count,
            "min": self.min,
            "avg": self.avg,
            "max": self.max,
            "observed_prices": [op.to_dict() for op in self.observed_prices],
            "notes": self.notes
        }


class PricingParser:
    """
    Parses price strings from website text and computes statistics.
    
    Supported currencies:
    - USD ($)
    - EUR (€)
    - GBP (£)
    - INR (₹)
    - AED (AED, د.إ)
    """
    
    # Currency patterns with their canonical names
    CURRENCY_PATTERNS = {
        'USD': [r'\$', r'USD', r'US\$'],
        'EUR': [r'€', r'EUR'],
        'GBP': [r'£', r'GBP'],
        'INR': [r'₹', r'INR', r'Rs\.?'],
        'AED': [r'AED', r'د\.إ', r'Dhs?\.?'],
    }
    
    # Patterns to extract numeric values with currency context
    PRICE_EXTRACTION_PATTERNS = [
        # Currency symbol before number: $100, €50, £200
        (r'([\$€£₹])\s*([\d,]+(?:\.\d{1,2})?)', 'symbol_prefix'),
        # Currency code before number: AED 100, USD 50
        (r'(AED|USD|EUR|GBP|INR|SAR|Dhs?)\s*([\d,]+(?:\.\d{1,2})?)', 'code_prefix'),
        # Number before currency: 100 AED, 50 USD
        (r'([\d,]+(?:\.\d{1,2})?)\s*(AED|USD|EUR|GBP|INR|SAR)', 'code_suffix'),
        # Written currency: 950 UAE dirhams, 100 dollars, 50 euros
        (r'([\d,]+(?:\.\d{1,2})?)\s*(?:UAE\s+)?(?:dirhams?|dollars?|euros?|pounds?|rupees?)', 'written_suffix'),
        # Rupee pattern: Rs. 100 or Rs 100
        (r'Rs\.?\s*([\d,]+(?:\.\d{1,2})?)', 'rupee'),
        # Dirham pattern: د.إ 100
        (r'د\.إ\s*([\d,]+(?:\.\d{1,2})?)', 'dirham'),
        # Starting at patterns: from $100, starting at €50
        (r'(?:from|starting\s+at|only)\s*([\$€£₹])\s*([\d,]+(?:\.\d{1,2})?)', 'starting_at'),
    ]
    
    # Symbol to currency mapping
    SYMBOL_TO_CURRENCY = {
        '$': 'USD',
        '€': 'EUR',
        '£': 'GBP',
        '₹': 'INR',
    }
    
    CODE_TO_CURRENCY = {
        'AED': 'AED',
        'USD': 'USD',
        'EUR': 'EUR',
        'GBP': 'GBP',
        'INR': 'INR',
        'Dhs': 'AED',
        'Dh': 'AED',
    }
    
    def parse_with_sources(
        self, 
        price_data: List[Dict],  # List of {text: str, source_url: str}
        full_text: str = ""
    ) -> PricingResult:
        """
        Parse prices with source URL tracking.
        
        Args:
            price_data: List of dicts with 'text' and 'source_url' keys
            full_text: Full text content for currency detection fallback
            
        Returns:
            PricingResult with observed_prices including source URLs
        """
        observed_prices = []
        detected_currencies = []
        
        # Detect primary currency from full text
        primary_currency = self._detect_primary_currency(full_text)
        
        # Extract prices from each source
        for item in price_data:
            text = item.get('text', '')
            source_url = item.get('source_url', 'unknown')
            
            extracted = self._extract_from_text(text)
            for value, currency, raw in extracted:
                if currency:
                    detected_currencies.append(currency)
                
                observed_prices.append(ObservedPrice(
                    value=value,
                    currency=currency or primary_currency or "unknown",
                    raw=raw[:120],  # Limit raw string length
                    source_url=source_url
                ))
        
        # Deduplicate by value (keep first occurrence)
        seen_values = set()
        unique_prices = []
        for op in observed_prices:
            if op.value not in seen_values:
                seen_values.add(op.value)
                unique_prices.append(op)
        
        # Filter out likely non-price values
        filtered_prices = [op for op in unique_prices if 1 <= op.value <= 1_000_000]
        
        # Determine primary currency
        if detected_currencies:
            currency_counts = Counter(detected_currencies)
            primary_currency = currency_counts.most_common(1)[0][0]
        
        # Compute stats
        values = [op.value for op in filtered_prices]
        if values:
            min_val = min(values)
            max_val = max(values)
            avg_val = round(sum(values) / len(values), 2)
        else:
            min_val = 0
            max_val = 0
            avg_val = 0
        
        # Generate notes
        notes = self._generate_notes(filtered_prices, full_text)
        
        return PricingResult(
            currency=primary_currency or "unknown",
            count=len(filtered_prices),
            min=min_val,
            avg=avg_val,
            max=max_val,
            observed_prices=filtered_prices[:200],  # Limit to 200
            notes=notes
        )
    
    def parse(self, price_strings: List[str], full_text: str = "") -> Dict:
        """
        Legacy parse method for backward compatibility.
        Returns dict matching the old format.
        """
        # Convert to new format
        price_data = [{'text': s, 'source_url': 'unknown'} for s in price_strings]
        result = self.parse_with_sources(price_data, full_text)
        
        # Return in old format for compatibility
        return {
            "currency": result.currency,
            "values_numeric": [op.value for op in result.observed_prices],
            "min": result.min if result.count > 0 else None,
            "max": result.max if result.count > 0 else None,
            "avg": result.avg if result.count > 0 else None,
            "count": result.count,
            "pricing_notes": result.notes
        }
    
    def _extract_from_text(self, text: str) -> List[Tuple[float, Optional[str], str]]:
        """Extract prices from text, returning (value, currency, raw_match)"""
        results = []
        
        for pattern, pattern_type in self.PRICE_EXTRACTION_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    raw_match = match.group(0)
                    
                    if pattern_type == 'symbol_prefix':
                        symbol = match.group(1)
                        value_str = match.group(2)
                        currency = self.SYMBOL_TO_CURRENCY.get(symbol)
                        
                    elif pattern_type == 'code_prefix':
                        code = match.group(1).upper()
                        value_str = match.group(2)
                        currency = self.CODE_TO_CURRENCY.get(code, code)
                        
                    elif pattern_type == 'code_suffix':
                        value_str = match.group(1)
                        code = match.group(2).upper()
                        currency = self.CODE_TO_CURRENCY.get(code, code)
                        
                    elif pattern_type == 'rupee':
                        value_str = match.group(1)
                        currency = 'INR'
                        
                    elif pattern_type == 'dirham':
                        value_str = match.group(1)
                        currency = 'AED'
                        
                    elif pattern_type == 'written_suffix':
                        value_str = match.group(1)
                        raw_lower = raw_match.lower()
                        if 'dirham' in raw_lower or 'uae' in raw_lower:
                            currency = 'AED'
                        elif 'dollar' in raw_lower:
                            currency = 'USD'
                        elif 'euro' in raw_lower:
                            currency = 'EUR'
                        elif 'pound' in raw_lower:
                            currency = 'GBP'
                        elif 'rupee' in raw_lower:
                            currency = 'INR'
                        else:
                            currency = None
                        
                    elif pattern_type == 'starting_at':
                        symbol = match.group(1)
                        value_str = match.group(2)
                        currency = self.SYMBOL_TO_CURRENCY.get(symbol)
                    else:
                        continue
                    
                    value = float(value_str.replace(',', ''))
                    results.append((value, currency, raw_match))
                    
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse price: {e}")
                    continue
        
        return results
    
    def _detect_primary_currency(self, text: str) -> str:
        """Detect the primary currency used in text"""
        currency_counts = {}
        
        for currency, patterns in self.CURRENCY_PATTERNS.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, text, re.IGNORECASE))
            currency_counts[currency] = count
        
        if currency_counts:
            max_currency = max(currency_counts, key=currency_counts.get)
            if currency_counts[max_currency] > 0:
                return max_currency
        
        return "unknown"
    
    def _generate_notes(self, prices: List[ObservedPrice], full_text: str) -> str:
        """Generate pricing notes"""
        notes = []
        text_lower = full_text.lower()
        
        if len(prices) >= 3:
            notes.append(f"{len(prices)} price points detected")
        
        if any(x in text_lower for x in ['starting', 'from', 'starting at']):
            notes.append("'starting at' pricing")
        
        if any(x in text_lower for x in ['per ', '/hr', '/hour', '/month', '/session']):
            notes.append("per-unit pricing")
        
        if any(x in text_lower for x in ['discount', 'off', 'save', 'sale']):
            notes.append("discounts mentioned")
        
        if any(x in text_lower for x in ['package', 'bundle', 'tier']):
            notes.append("package pricing")
        
        return '; '.join(notes) if notes else "unknown"


def parse_pricing(price_strings: List[str], full_text: str = "") -> Dict:
    """
    Convenience function for backward compatibility.
    """
    parser = PricingParser()
    return parser.parse(price_strings, full_text)


def parse_pricing_with_sources(price_data: List[Dict], full_text: str = "") -> Dict:
    """
    Parse pricing with source URL tracking.
    
    Args:
        price_data: List of dicts with 'text' and 'source_url' keys
        full_text: Full text for currency detection
        
    Returns:
        Dictionary with pricing stats and observed_prices
    """
    parser = PricingParser()
    result = parser.parse_with_sources(price_data, full_text)
    return result.to_dict()
