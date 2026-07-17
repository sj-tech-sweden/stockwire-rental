import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TwentyClient:
    def __init__(self, api_key: str, base_url: str = "https://api.twenty.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/metadata",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_objects(self, object_name: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/rest/{object_name}",
                headers=self.headers,
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
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/rest/{object_name}/{record_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_object(self, object_name: str, data: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/rest/{object_name}",
                headers=self.headers,
                json=data,
            )
            if not resp.is_success:
                logger.error("Twenty create %s failed %s: %s", object_name, resp.status_code, resp.text)
                resp.raise_for_status()
            return resp.json()

    async def update_object(self, object_name: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.patch(
                f"{self.base_url}/rest/{object_name}/{record_id}",
                headers=self.headers,
                json=data,
            )
            if not resp.is_success:
                logger.error("Twenty update %s/%s failed %s: %s", object_name, record_id, resp.status_code, resp.text)
                resp.raise_for_status()
            return resp.json()

    async def delete_object(self, object_name: str, record_id: str) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                f"{self.base_url}/rest/{object_name}/{record_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return True

    async def search_people(self, email: str | None = None, name: str | None = None) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            body: dict[str, Any] = {"filter": {}, "limit": 10, "offset": 0}
            if email:
                body["filter"]["emails"] = {"contains": email}
            if name:
                body["filter"]["name"] = {"contains": name}
            resp = await client.post(
                f"{self.base_url}/rest/people",
                headers=self.headers,
                json=body,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def search_companies(self, name: str | None = None, domain: str | None = None) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            body: dict[str, Any] = {"filter": {}, "limit": 10, "offset": 0}
            if name:
                body["filter"]["name"] = {"contains": name}
            if domain:
                body["filter"]["domainName"] = {"contains": domain}
            resp = await client.post(
                f"{self.base_url}/rest/companies",
                headers=self.headers,
                json=body,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def search_opportunities(self, name: str | None = None, stage: str | None = None) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            body: dict[str, Any] = {"filter": {}, "limit": 10, "offset": 0}
            if name:
                body["filter"]["name"] = {"contains": name}
            if stage:
                body["filter"]["stage"] = {"eq": stage}
            resp = await client.post(
                f"{self.base_url}/rest/opportunities",
                headers=self.headers,
                json=body,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
