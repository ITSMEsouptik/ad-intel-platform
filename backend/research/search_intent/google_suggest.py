"""
Novara Research Foundation: Google Suggest Client
FREE autocomplete suggestions via Google's unofficial endpoint

Version 1.0 - Feb 2026
"""

import httpx
import asyncio
import random
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ============== CONSTANTS ==============

GOOGLE_SUGGEST_URL = "https://suggestqueries.google.com/complete/search"

# Country name to ISO 3166-1 alpha-2 mapping (common countries)
COUNTRY_TO_ISO2 = {
    "united arab emirates": "AE",
    "uae": "AE",
    "united states": "US",
    "usa": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "canada": "CA",
    "australia": "AU",
    "india": "IN",
    "germany": "DE",
    "france": "FR",
    "spain": "ES",
    "italy": "IT",
    "netherlands": "NL",
    "singapore": "SG",
    "saudi arabia": "SA",
    "qatar": "QA",
    "kuwait": "KW",
    "bahrain": "BH",
    "oman": "OM",
    "egypt": "EG",
    "south africa": "ZA",
    "nigeria": "NG",
    "kenya": "KE",
    "pakistan": "PK",
    "bangladesh": "BD",
    "malaysia": "MY",
    "indonesia": "ID",
    "philippines": "PH",
    "thailand": "TH",
    "vietnam": "VN",
    "japan": "JP",
    "south korea": "KR",
    "china": "CN",
    "hong kong": "HK",
    "taiwan": "TW",
    "brazil": "BR",
    "mexico": "MX",
    "argentina": "AR",
    "colombia": "CO",
    "chile": "CL",
    "peru": "PE",
    "new zealand": "NZ",
    "ireland": "IE",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "poland": "PL",
    "turkey": "TR",
    "russia": "RU",
    "ukraine": "UA",
    "israel": "IL",
    "jordan": "JO",
    "lebanon": "LB",
}


@dataclass
class SuggestResult:
    """Result from a single suggest query"""
    seed: str
    suggestions: List[str]
    success: bool
    error: Optional[str] = None


class GoogleSuggestClient:
    """
    Async client for Google Autocomplete suggestions.
    
    Features:
    - Concurrent requests with rate limiting
    - Jitter delays to avoid rate limits
    - Retry logic with exponential backoff
    - Country/language localization
    """
    
    def __init__(
        self,
        concurrency_limit: int = 5,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        jitter_min_ms: int = 50,
        jitter_max_ms: int = 150
    ):
        self.concurrency_limit = concurrency_limit
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.jitter_min_ms = jitter_min_ms
        self.jitter_max_ms = jitter_max_ms
        self._semaphore = asyncio.Semaphore(concurrency_limit)
    
    def get_country_code(self, country: str) -> Optional[str]:
        """Convert country name to ISO 3166-1 alpha-2 code"""
        if not country:
            return None
        
        country_lower = country.lower().strip()
        
        # Direct match
        if country_lower in COUNTRY_TO_ISO2:
            return COUNTRY_TO_ISO2[country_lower]
        
        # Check if already a 2-letter code
        if len(country_lower) == 2:
            return country_lower.upper()
        
        # Partial match
        for name, code in COUNTRY_TO_ISO2.items():
            if country_lower in name or name in country_lower:
                return code
        
        return None
    
    async def _fetch_single(
        self,
        client: httpx.AsyncClient,
        query: str,
        language: str = "en",
        country: Optional[str] = None
    ) -> SuggestResult:
        """Fetch suggestions for a single query with retry logic"""
        
        params = {
            "client": "firefox",  # Returns clean JSON
            "q": query,
            "hl": language
        }
        
        if country:
            country_code = self.get_country_code(country)
            if country_code:
                params["gl"] = country_code
        
        for attempt in range(self.max_retries + 1):
            try:
                # Add jitter delay
                jitter = random.randint(self.jitter_min_ms, self.jitter_max_ms) / 1000
                await asyncio.sleep(jitter)
                
                response = await client.get(
                    GOOGLE_SUGGEST_URL,
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Response format: [query, [suggestion1, suggestion2, ...]]
                    if isinstance(data, list) and len(data) >= 2:
                        suggestions = data[1] if isinstance(data[1], list) else []
                        return SuggestResult(
                            seed=query,
                            suggestions=suggestions,
                            success=True
                        )
                    return SuggestResult(seed=query, suggestions=[], success=True)
                
                elif response.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Rate limited on '{query}', waiting {wait_time:.1f}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                
                else:
                    logger.warning(f"Unexpected status {response.status_code} for '{query}'")
                    return SuggestResult(
                        seed=query,
                        suggestions=[],
                        success=False,
                        error=f"HTTP {response.status_code}"
                    )
                    
            except httpx.TimeoutException:
                logger.warning(f"Timeout for '{query}' (attempt {attempt + 1})")
                if attempt == self.max_retries:
                    return SuggestResult(
                        seed=query,
                        suggestions=[],
                        success=False,
                        error="Timeout"
                    )
            except Exception as e:
                logger.error(f"Error fetching suggestions for '{query}': {e}")
                return SuggestResult(
                    seed=query,
                    suggestions=[],
                    success=False,
                    error=str(e)
                )
        
        return SuggestResult(seed=query, suggestions=[], success=False, error="Max retries exceeded")
    
    async def _fetch_with_semaphore(
        self,
        client: httpx.AsyncClient,
        query: str,
        language: str,
        country: Optional[str]
    ) -> SuggestResult:
        """Fetch with semaphore for concurrency control"""
        async with self._semaphore:
            return await self._fetch_single(client, query, language, country)
    
    async def fetch_suggestions(
        self,
        seeds: List[str],
        language: str = "en",
        country: Optional[str] = None
    ) -> List[SuggestResult]:
        """
        Fetch suggestions for multiple seed queries concurrently.
        
        Args:
            seeds: List of seed queries to expand
            language: Language code (e.g., "en", "ar")
            country: Country name or ISO code for localization
        
        Returns:
            List of SuggestResult objects
        """
        if not seeds:
            return []
        
        logger.info(f"Fetching suggestions for {len(seeds)} seeds (lang={language}, country={country})")
        
        async with httpx.AsyncClient() as client:
            tasks = [
                self._fetch_with_semaphore(client, seed, language, country)
                for seed in seeds
            ]
            results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in results if r.success)
        total_suggestions = sum(len(r.suggestions) for r in results)
        
        logger.info(f"Fetched {total_suggestions} suggestions from {success_count}/{len(seeds)} successful queries")
        
        return results
    
    async def fetch_all_suggestions(
        self,
        seeds: List[str],
        language: str = "en",
        country: Optional[str] = None
    ) -> List[str]:
        """
        Convenience method to fetch and flatten all suggestions.
        
        Returns:
            Flat list of all unique suggestions (deduplicated)
        """
        results = await self.fetch_suggestions(seeds, language, country)
        
        all_suggestions = []
        seen = set()
        
        for result in results:
            for suggestion in result.suggestions:
                suggestion_lower = suggestion.lower().strip()
                if suggestion_lower not in seen:
                    seen.add(suggestion_lower)
                    all_suggestions.append(suggestion)
        
        return all_suggestions
