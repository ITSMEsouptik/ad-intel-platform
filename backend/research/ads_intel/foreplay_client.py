"""
Novara Ads Intelligence: Foreplay API Client
Handles auth fallback (raw key → Bearer prefix on 401), retries, and error mapping.
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

FOREPLAY_API_KEY = os.environ.get("FOREPLAY_API_KEY", "")
FOREPLAY_BASE_URL = os.environ.get("FOREPLAY_BASE_URL", "https://public.api.foreplay.co")


class ForeplayAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        self.status_code = status_code
        super().__init__(message)


class ForeplayClient:
    """Async client for the Foreplay ad intelligence API."""

    def __init__(self, api_key: str = None, base_url: str = None, timeout: int = 30):
        self.api_key = api_key or FOREPLAY_API_KEY
        self.base_url = (base_url or FOREPLAY_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._auth_format = self._detect_auth_format()

    def _detect_auth_format(self) -> str:
        if self.api_key.startswith("Bearer "):
            return "bearer"
        return "raw"  # try raw first, fallback to Bearer on 401

    def _headers(self, use_bearer: bool = False) -> Dict[str, str]:
        token = self.api_key
        if use_bearer and not token.startswith("Bearer "):
            token = f"Bearer {token}"
        return {
            "authorization": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, params: Dict[str, Any] = None) -> Any:
        """Make request with auth fallback: raw → Bearer on 401."""
        url = f"{self.base_url}{path}"

        # Convert list values to repeated query params
        query_params = []
        if params:
            for k, v in params.items():
                if isinstance(v, list):
                    for item in v:
                        query_params.append((k, str(item)))
                elif v is not None:
                    query_params.append((k, str(v)))

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Attempt 1: use detected format
            use_bearer = self._auth_format == "bearer"
            resp = await client.request(method, url, params=query_params, headers=self._headers(use_bearer))

            # If 401 and we used raw, retry with Bearer
            if resp.status_code == 401 and not use_bearer:
                logger.info("[FOREPLAY] Raw auth got 401, retrying with Bearer prefix")
                resp = await client.request(method, url, params=query_params, headers=self._headers(use_bearer=True))
                if resp.status_code == 200:
                    self._auth_format = "bearer"  # remember for future calls

            if resp.status_code == 401:
                raise ForeplayAPIError("Authentication failed - check FOREPLAY_API_KEY", 401)
            if resp.status_code == 429:
                raise ForeplayAPIError("Rate limit exceeded", 429)
            if resp.status_code == 404:
                raise ForeplayAPIError(f"Not found: {path}", 404)
            if resp.status_code >= 400:
                raise ForeplayAPIError(f"API error {resp.status_code}: {resp.text[:300]}", resp.status_code)

            return resp.json()

    async def get_brands_by_domain(self, domain: str, limit: int = 5, order: str = "most_ranked") -> List[Dict]:
        """
        Find brands by domain.
        GET /api/brand/getBrandsByDomain?domain=...
        """
        logger.info(f"[FOREPLAY] Looking up brand for domain: {domain}")
        result = await self._request("GET", "/api/brand/getBrandsByDomain", params={
            "domain": domain,
            "limit": limit,
            "order": order,
        })
        # Foreplay wraps response in {metadata, data, error}
        if isinstance(result, dict):
            data = result.get("data", [])
            if isinstance(data, list):
                return data
            return [data] if data else []
        if isinstance(result, list):
            return result
        return []

    async def get_ads_by_brand_ids(
        self,
        brand_ids: List[str],
        limit: int = 50,
        publisher_platform: List[str] = None,
        order: str = "longest_running",
        running_duration_min_days: int = None,
        **filters,
    ) -> List[Dict]:
        """
        Fetch ads for given brand IDs, sorted by longest running (winning ads).
        GET /api/brand/getAdsByBrandId
        """
        if publisher_platform is None:
            publisher_platform = ["facebook", "instagram", "tiktok"]
        ids_str = ",".join(brand_ids) if isinstance(brand_ids, list) else str(brand_ids)
        logger.info(f"[FOREPLAY] Fetching ads for brand_ids={ids_str[:80]}, limit={limit}, order={order}")

        params = {
            "brand_ids": ids_str,
            "limit": limit,
            "publisher_platform": publisher_platform,
            "order": order,
        }
        if running_duration_min_days is not None:
            params["running_duration_min_days"] = running_duration_min_days
        for k, v in filters.items():
            if v is not None:
                params[k] = v

        result = await self._request("GET", "/api/brand/getAdsByBrandId", params=params)
        if isinstance(result, dict):
            data = result.get("data", [])
            if isinstance(data, list):
                return data
            return [data] if data else []
        if isinstance(result, list):
            return result
        return []

    async def discovery_ads(
        self,
        query: str,
        limit: int = 50,
        publisher_platform: List[str] = None,
        order: str = "longest_running",
        running_duration_min_days: int = None,
        **filters,
    ) -> List[Dict]:
        """
        Discover ads by keyword/niche, sorted by longest running (winning ads).
        GET /api/discovery/ads
        """
        if publisher_platform is None:
            publisher_platform = ["facebook", "instagram", "tiktok"]
        logger.info(f"[FOREPLAY] Discovery search: query='{query}', limit={limit}, order={order}")

        params = {
            "query": query,
            "limit": limit,
            "publisher_platform": publisher_platform,
            "order": order,
        }
        if running_duration_min_days is not None:
            params["running_duration_min_days"] = running_duration_min_days
        for k, v in filters.items():
            if v is not None:
                params[k] = v

        result = await self._request("GET", "/api/discovery/ads", params=params)
        if isinstance(result, dict):
            data = result.get("data", [])
            if isinstance(data, list):
                return data
            return [data] if data else []
        if isinstance(result, list):
            return result
        return []
