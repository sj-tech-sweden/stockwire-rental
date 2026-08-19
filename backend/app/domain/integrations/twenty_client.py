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

    async def provision_schema(self, webhook_url: str | None = None, webhook_secret: str | None = None) -> dict[str, Any]:
        """Create custom fields, objects, and webhooks in Twenty via Metadata API.

        Returns a summary of what was created/already existed.
        """
        results: dict[str, Any] = {"custom_fields_created": [], "custom_objects_created": [], "webhooks_created": [], "errors": []}

        # ── Company fields ────────────────────────────────────────────────
        company_fields = [
            ("stockwireUrl", "LINKS", "Stockwire URL"),
            ("stockwireId", "NUMBER", "Stockwire ID"),
            ("stockwireNotes", "TEXT", "Stockwire Notes"),
            ("phoneSecondary", "PHONE", "Secondary Phone"),
        ]
        for field_name, field_type, label in company_fields:
            try:
                await self._ensure_custom_field("company", field_name, field_type, label)
                results["custom_fields_created"].append(f"company.{field_name}")
            except Exception as exc:
                results["errors"].append(f"company.{field_name}: {exc}")

        # ── Opportunity fields ────────────────────────────────────────────
        opportunity_fields = [
            ("stockwireUrl", "LINKS", "Stockwire URL"),
            ("stockwireId", "NUMBER", "Stockwire ID"),
            ("stockwireJobCode", "TEXT", "Job Code"),
            ("stockwireStartDate", "DATE", "Rental Start Date"),
            ("stockwireEndDate", "DATE", "Rental End Date"),
            ("stockwireStatus", "TEXT", "Rental Status"),
        ]
        for field_name, field_type, label in opportunity_fields:
            try:
                await self._ensure_custom_field("opportunity", field_name, field_type, label)
                results["custom_fields_created"].append(f"opportunity.{field_name}")
            except Exception as exc:
                results["errors"].append(f"opportunity.{field_name}: {exc}")

        # ── Person fields ─────────────────────────────────────────────────
        person_fields = [
            ("stockwireUrl", "LINKS", "Stockwire URL"),
            ("stockwireId", "NUMBER", "Stockwire ID"),
        ]
        for field_name, field_type, label in person_fields:
            try:
                await self._ensure_custom_field("person", field_name, field_type, label)
                results["custom_fields_created"].append(f"person.{field_name}")
            except Exception as exc:
                results["errors"].append(f"person.{field_name}: {exc}")

        # ── Rental Job custom object ──────────────────────────────────────
        try:
            await self._ensure_custom_object("rentalJob", "Rental Job", [
                {"name": "jobStatus", "type": "TEXT", "label": "Job Status"},
                {"name": "jobCode", "type": "TEXT", "label": "Job Code"},
                {"name": "customerName", "type": "TEXT", "label": "Customer Name"},
                {"name": "startDate", "type": "DATE", "label": "Start Date"},
                {"name": "endDate", "type": "DATE", "label": "End Date"},
                {"name": "totalAmount", "type": "NUMBER", "label": "Total Amount"},
                {"name": "currency", "type": "TEXT", "label": "Currency"},
                {"name": "stockwireJobUrl", "type": "LINKS", "label": "Stockwire Job URL"},
                {"name": "stockwireJobId", "type": "NUMBER", "label": "Stockwire Job ID"},
                {"name": "description", "type": "TEXT", "label": "Description"},
            ])
            results["custom_objects_created"].append("rentalJob")
        except Exception as exc:
            results["errors"].append(f"rentalJob: {exc}")

        # ── Webhooks ──────────────────────────────────────────────────────
        if webhook_url:
            try:
                existing_hooks = await self.list_webhooks()
                existing_urls = {h.get("targetUrl") for h in existing_hooks if isinstance(h, dict)}

                webhook_events = [
                    ("company.created", "company"),
                    ("company.updated", "company"),
                    ("opportunity.updated", "opportunity"),
                ]
                for event, object_type in webhook_events:
                    if webhook_url not in existing_urls:
                        hook = await self.create_webhook(webhook_url, event, object_type, webhook_secret)
                        hook_id = hook.get("data", hook).get("id", "unknown")
                        results["webhooks_created"].append(f"{event} → {webhook_url}")
                        logger.info("Created Twenty webhook: %s (id=%s)", event, hook_id)
            except Exception as exc:
                results["errors"].append(f"webhooks: {exc}")
                logger.warning("Could not provision webhooks: %s", exc)

        return results

    async def _resolve_object_metadata_id(self, name_singular: str) -> str:
        """Look up the UUID for an object by its nameSingular via GraphQL."""
        query = '''
        query GetObject($nameSingular: String!) {
          objects(filter: { nameSingular: { eq: $nameSingular } }) {
            edges {
              node {
                id
                nameSingular
              }
            }
          }
        }
        '''
        result = await self.graphql(query, {"nameSingular": name_singular})
        edges = result.get("data", {}).get("objects", {}).get("edges", [])
        if not edges:
            raise ValueError(f"Object '{name_singular}' not found in Twenty workspace")
        return edges[0]["node"]["id"]

    async def _ensure_custom_field(self, object_name: str, field_name: str, field_type: str, label: str) -> None:
        """Create a custom field on an object via GraphQL if it doesn't already exist.

        field_type must be a valid Twenty FieldMetadataType enum value:
        TEXT, NUMBER, BOOLEAN, DATE, DATE_TIME, LINKS, PHONE, EMAILS,
        CURRENCY, SELECT, MULTI_SELECT, RELATION, etc.
        """
        object_metadata_id = await self._resolve_object_metadata_id(object_name)

        # Check if field already exists via introspection
        query = '{ %s { fields { name } } }' % object_name
        try:
            result = await self.graphql(query)
            fields_data = result.get("data", {}).get(object_name, {})
            existing_fields = [f.get("name", "") for f in fields_data.get("fields", [])]
            if field_name in existing_fields:
                return
        except Exception as exc:
            logger.debug("Could not introspect fields for %s, proceeding with creation: %s", object_name, exc)

        # Create the field via GraphQL mutation
        mutation = '''
        mutation CreateOneField($input: CreateOneFieldMetadataInput!) {
          createOneField(input: $input) {
            field {
              id
              name
              type
              label
            }
          }
        }
        '''
        resp = await self.graphql(mutation, {
            "input": {
                "field": {
                    "objectMetadataId": object_metadata_id,
                    "name": field_name,
                    "type": field_type,
                    "label": label,
                }
            }
        })
        errors = resp.get("errors")
        if errors:
            msg = errors[0].get("message", str(errors))
            raise RuntimeError(f"createOneField failed: {msg}")

    async def _ensure_custom_object(self, object_name: str, label: str, fields: list[dict[str, Any]]) -> None:
        """Create a custom object with fields via GraphQL if it doesn't already exist.

        If the object already exists, still create any missing fields on it.
        """
        object_exists = False
        try:
            await self._resolve_object_metadata_id(object_name)
            object_exists = True
        except Exception:
            pass

        if not object_exists:
            mutation = '''
            mutation CreateOneObject($input: CreateOneObjectMetadataInput!) {
              createOneObject(input: $input) {
                objectMetadata {
                  id
                  nameSingular
                }
              }
            }
            '''
            resp = await self.graphql(mutation, {
                "input": {
                    "object": {
                        "nameSingular": object_name,
                        "labelSingular": label,
                        "namePlural": object_name + "s",
                        "labelPlural": label + "s",
                        "isCustom": True,
                    }
                }
            })
            errors = resp.get("errors")
            if errors:
                msg = errors[0].get("message", str(errors))
                raise RuntimeError(f"createOneObject failed: {msg}")

        # Create any fields on the object
        for field in fields:
            try:
                await self._ensure_custom_field(object_name, field["name"], field["type"], field["label"])
            except Exception as exc:
                logger.debug("Could not ensure field %s.%s: %s", object_name, field["name"], exc)

    async def sync_job_to_twenty(self, job_id: int, job_data: dict[str, Any], deep_link: str) -> str | None:
        """Upsert a Rental Job custom object in Twenty and return its ID."""
        existing_id = job_data.get("twenty_rental_job_id")
        payload = {
            "jobStatus": job_data.get("status", "draft"),
            "jobCode": job_data.get("job_code", ""),
            "customerName": job_data.get("customer_name", ""),
            "startDate": job_data.get("start_date"),
            "endDate": job_data.get("end_date"),
            "totalAmount": job_data.get("sales_price", 0),
            "currency": job_data.get("currency", "SEK"),
            "stockwireJobUrl": deep_link,
            "stockwireJobId": job_id,
            "description": job_data.get("description", ""),
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

    async def list_webhooks(self) -> list[dict[str, Any]]:
        """List existing webhooks in the Twenty workspace."""
        resp = await self._request_with_retry("GET", f"{self.base_url}/rest/webhooks")
        if not resp.is_success:
            return []
        data = resp.json()
        # Handle various response shapes: {data: [...]}, {data: {webhooks: [...]}}, or [...]
        items = data.get("data", data) if isinstance(data, dict) else data
        if isinstance(items, dict):
            # Try common nested keys
            for key in ("webhooks", "edges", "nodes"):
                if key in items and isinstance(items[key], list):
                    items = items[key]
                    break
            else:
                items = []
        if not isinstance(items, list):
            items = []
        # Filter to only dicts (skip any non-dict entries)
        return [h for h in items if isinstance(h, dict)]

    async def create_webhook(self, target_url: str, event: str, object_type: str | None = None, secret: str | None = None) -> dict[str, Any]:
        """Create a webhook in Twenty CRM."""
        payload: dict[str, Any] = {
            "targetUrl": target_url,
            "event": event,
            "isActive": True,
        }
        if object_type:
            payload["objectType"] = object_type
        if secret:
            payload["secret"] = secret
        resp = await self._request_with_retry("POST", f"{self.base_url}/rest/webhooks", json=payload)
        if not resp.is_success:
            logger.error("Twenty create webhook failed %s: %s", resp.status_code, resp.text[:300])
            resp.raise_for_status()
        return resp.json()

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook from Twenty CRM."""
        resp = await self._request_with_retry("DELETE", f"{self.base_url}/rest/webhooks/{webhook_id}")
        return resp.is_success
