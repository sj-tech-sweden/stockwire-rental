import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = [0.5, 1.0, 2.0]


def _mask_url(url: str) -> str:
    if "/rest/" in url or "/graphql" in url:
        return url
    return url


def _mask_headers(headers: dict) -> dict:
    masked = {}
    for key, value in headers.items():
        if key.lower() == "authorization" and isinstance(value, str) and len(value) > 20:
            masked[key] = value[:15] + "..." + value[-5:]
        else:
            masked[key] = value
    return masked


class TwentyClient:
    def __init__(self, api_key: str, base_url: str = "https://api.twenty.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.request(method, url, headers=self.headers, **kwargs)
                    if resp.status_code >= 500 and attempt < MAX_RETRIES - 1:
                        logger.warning(
                            "Twenty %s %s returned %d, retrying in %.1fs",
                            method, url.split("/")[-1], resp.status_code,
                            RETRY_BACKOFF[attempt],
                        )
                        await asyncio.sleep(RETRY_BACKOFF[attempt])
                        continue
                    return resp
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "Twenty %s %s connection error, retrying in %.1fs: %s",
                        method, url.split("/")[-1], RETRY_BACKOFF[attempt], exc,
                    )
                    await asyncio.sleep(RETRY_BACKOFF[attempt])
                    continue
                raise
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"Twenty {method} {url} failed after {MAX_RETRIES} retries")

    async def test_connection(self) -> dict[str, Any]:
        resp = await self._request_with_retry("GET", f"{self.base_url}/metadata")
        resp.raise_for_status()
        return resp.json()

    async def list_objects(self, object_name: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        resp = await self._request_with_retry(
            "POST",
            f"{self.base_url}/rest/{object_name}",
            json={
                "filter": {},
                "orderBy": [{"createdAt": "DescNullsFirst"}],
                "limit": limit,
                "offset": offset,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def get_object(self, object_name: str, record_id: str) -> dict[str, Any]:
        resp = await self._request_with_retry(
            "GET",
            f"{self.base_url}/rest/{object_name}/{record_id}",
        )
        resp.raise_for_status()
        return resp.json()

    async def create_object(self, object_name: str, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self._request_with_retry(
            "POST",
            f"{self.base_url}/rest/{object_name}",
            json=data,
        )
        if not resp.is_success:
            logger.error("Twenty create %s failed %s: %s", object_name, resp.status_code, resp.text[:500])
            resp.raise_for_status()
        return resp.json()

    async def update_object(self, object_name: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self._request_with_retry(
            "PATCH",
            f"{self.base_url}/rest/{object_name}/{record_id}",
            json=data,
        )
        if not resp.is_success:
            logger.error("Twenty update %s/%s failed %s: %s", object_name, record_id, resp.status_code, resp.text[:500])
            resp.raise_for_status()
        return resp.json()

    async def delete_object(self, object_name: str, record_id: str) -> bool:
        resp = await self._request_with_retry(
            "DELETE",
            f"{self.base_url}/rest/{object_name}/{record_id}",
        )
        resp.raise_for_status()
        return True

    async def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = variables
        resp = await self._request_with_retry(
            "POST",
            f"{self.base_url}/graphql",
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    async def search_people(self, email: str | None = None, name: str | None = None) -> list[dict[str, Any]]:
        filters = []
        if email:
            filters.append('{emails: {primaryEmail: {eq: "%s"}}}' % email)
        if name:
            filters.append('{name: {firstName: {contains: "%s"}}}' % name)
        filter_str = ", ".join(filters) if filters else "{}"
        query = '{ people(filter: %s) { edges { node { id name { firstName lastName } emails { primaryEmail } company { id } } } } }' % filter_str
        result = await self.graphql(query)
        return result.get("data", {}).get("people", {}).get("edges", [])

    async def search_companies(self, name: str | None = None, domain: str | None = None) -> list[dict[str, Any]]:
        filters = []
        if name:
            filters.append('{name: {contains: "%s"}}' % name)
        if domain:
            filters.append('{domainName: {primaryLinkUrl: {contains: "%s"}}}' % domain)
        filter_str = ", ".join(filters) if filters else "{}"
        query = '{ companies(filter: %s) { edges { node { id name } } } }' % filter_str
        result = await self.graphql(query)
        return result.get("data", {}).get("companies", {}).get("edges", [])

    async def search_opportunities(self, name: str | None = None, stage: str | None = None) -> list[dict[str, Any]]:
        filters = []
        if name:
            filters.append('{name: {contains: "%s"}}' % name)
        if stage:
            filters.append('{stage: {eq: "%s"}}' % stage)
        filter_str = ", ".join(filters) if filters else "{}"
        query = '{ opportunities(filter: %s) { edges { node { id name stage } } } }' % filter_str
        result = await self.graphql(query)
        return result.get("data", {}).get("opportunities", {}).get("edges", [])
