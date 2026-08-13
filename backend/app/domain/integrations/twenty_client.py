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
        params: dict[str, Any] = {
            "limit": limit,
            "orderBy": '[{"createdAt":"DescNullsFirst"}]',
        }
        if offset:
            params["offset"] = offset
        resp = await self._request_with_retry(
            "GET",
            f"{self.base_url}/rest/{object_name}",
            params=params,
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

    async def provision_schema(self) -> dict[str, Any]:
        """Create custom fields and objects in Twenty via Metadata API.

        Returns a summary of what was created/already existed.
        """
        results: dict[str, Any] = {"custom_fields_created": [], "custom_objects_created": [], "errors": []}

        # Create stockwire_url field on Company
        try:
            await self._ensure_custom_field("company", "stockwire_url", "url", "Stockwire URL")
            results["custom_fields_created"].append("company.stockwire_url")
        except Exception as exc:
            results["errors"].append(f"company.stockwire_url: {exc}")

        # Create stockwire_url field on Opportunity
        try:
            await self._ensure_custom_field("opportunity", "stockwire_url", "url", "Stockwire URL")
            results["custom_fields_created"].append("opportunity.stockwire_url")
        except Exception as exc:
            results["errors"].append(f"opportunity.stockwire_url: {exc}")

        # Create Rental Job custom object
        try:
            await self._ensure_custom_object("rentalJob", "Rental Job", [
                {"name": "jobStatus", "type": "text", "label": "Job Status"},
                {"name": "startDate", "type": "date", "label": "Start Date"},
                {"name": "endDate", "type": "date", "label": "End Date"},
                {"name": "totalAmount", "type": "number", "label": "Total Amount"},
                {"name": "stockwireJobUrl", "type": "url", "label": "Stockwire Job URL"},
            ])
            results["custom_objects_created"].append("rentalJob")
        except Exception as exc:
            results["errors"].append(f"rentalJob: {exc}")

        return results

    async def _ensure_custom_field(self, object_name: str, field_name: str, field_type: str, label: str) -> None:
        """Create a custom field on an object if it doesn't already exist."""
        # Check if field exists
        query = '{ %s { fields { name } } }' % object_name
        try:
            result = await self.graphql(query)
            existing_fields = [f.get("name", "") for f in result.get("data", {}).get(object_name, {}).get("fields", [])]
            if field_name in existing_fields:
                return
        except Exception as exc:
            logger.debug("Could not introspect fields for %s, proceeding with creation: %s", object_name, exc)

        # Create the field via metadata API
        await self._request_with_retry(
            "POST",
            f"{self.base_url}/rest/metadata/objectFields",
            json={
                "objectName": object_name,
                "name": field_name,
                "type": field_type,
                "label": label,
                "isCustom": True,
            },
        )

    async def _ensure_custom_object(self, object_name: str, label: str, fields: list[dict[str, Any]]) -> None:
        """Create a custom object with fields if it doesn't already exist."""
        # Check if object exists
        try:
            resp = await self._request_with_retry("GET", f"{self.base_url}/rest/{object_name}?limit=1")
            if resp.status_code == 200:
                return
        except Exception as exc:
            logger.debug("Could not check existence of %s, proceeding with creation: %s", object_name, exc)

        # Create the custom object via metadata API
        await self._request_with_retry(
            "POST",
            f"{self.base_url}/rest/metadata/object",
            json={
                "name": object_name,
                "label": label,
                "fields": fields,
            },
        )

    async def sync_job_to_twenty(self, job_id: int, job_data: dict[str, Any], deep_link: str) -> str | None:
        """Upsert a Rental Job custom object in Twenty and return its ID."""
        existing_id = job_data.get("twenty_rental_job_id")
        payload = {
            "jobStatus": job_data.get("status", "draft"),
            "startDate": job_data.get("start_date"),
            "endDate": job_data.get("end_date"),
            "totalAmount": job_data.get("sales_price", 0),
            "stockwireJobUrl": deep_link,
        }

        if existing_id:
            await self.update_object("rentalJob", existing_id, payload)
            return existing_id

        result = await self.create_object("rentalJob", payload)
        twenty_id = result.get("data", {}).get("createRentalJob", {}).get("id")
        return twenty_id

    async def post_activity_note(self, twenty_entity_id: str, entity_type: str, text: str) -> bool:
        """Post a note/activity on a Twenty record (Company or Opportunity)."""
        try:
            await self._request_with_retry(
                "POST",
                f"{self.base_url}/rest/{entity_type}/{twenty_entity_id}/notes",
                json={"body": text},
            )
            return True
        except Exception as exc:
            logger.error("Failed to post note to %s/%s: %s", entity_type, twenty_entity_id, exc)
            return False
