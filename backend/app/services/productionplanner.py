import logging
import httpx
from typing import Optional, List, Dict, Any, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


def batch_task_labels(labels: List[str], max_items: int = 10, max_chars: int = 400) -> List[str]:
    batches: List[str] = []
    current: List[str] = []
    current_length = 0
    separator = "; "

    for raw_label in labels:
        label = str(raw_label or "").strip()
        if not label:
            continue
        if len(label) > max_chars:
            logger.warning("batch_task_labels: label truncated from %d to %d chars", len(label), max_chars)
            label = label[:max_chars]
        next_length = current_length + (len(separator) if current else 0) + len(label)
        if current and (len(current) >= max_items or next_length > max_chars):
            batches.append(separator.join(current))
            current = [label]
            current_length = len(label)
            continue
        current.append(label)
        current_length = next_length

    if current:
        batches.append(separator.join(current))
    return batches


class ProductionPlannerClient:
    def __init__(self, api_key: str = "", base_url: str = ""):
        normalized_base_url = str(base_url or settings.productionplanner_base_url).strip().rstrip("/")
        self.base_url = f"{normalized_base_url}/"
        self.api_key = api_key or settings.productionplanner_api_key
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "ProductionPlannerClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        if response.status_code >= 400:
            raw_text = ""
            try:
                raw_text = response.text[:500]
            except UnicodeDecodeError:
                logger.debug("ProductionPlanner API error body could not be decoded as text")
            logger.debug(
                "ProductionPlanner API error: status=%d body=%r",
                response.status_code,
                raw_text,
            )
            try:
                error_data = response.json()
            except ValueError:
                error_data = None
            if isinstance(error_data, dict):
                message = (
                    error_data.get("message")
                    or error_data.get("detail")
                    or error_data.get("error")
                    or error_data.get("errorMessage")
                    or error_data.get("msg")
                )
            elif isinstance(error_data, str):
                message = error_data
            else:
                message = raw_text.strip() or None
            raise ProductionPlannerError(message or f"API error: {response.status_code}", response.status_code)
        if response.status_code == 204 or not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}

    async def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        request_kwargs = dict(kwargs)
        extra_headers = request_kwargs.pop("headers", None) or {}
        auth_variants: List[Dict[str, str]] = [{}]
        if self.api_key:
            auth_variants = [
                {"Authorization": f"Bearer {self.api_key}", "X-API-Key": self.api_key},
                {"X-API-Key": self.api_key},
                {"Authorization": f"Bearer {self.api_key}"},
            ]
        last_response: Optional[httpx.Response] = None
        try:
            for index, auth_headers in enumerate(auth_variants):
                headers = {**auth_headers, **extra_headers} if (auth_headers or extra_headers) else None
                response = await self.client.request(method, path, headers=headers, **request_kwargs)
                if response.status_code < 400:
                    return self._handle_response(response)
                last_response = response
                # Retry only likely auth/header compatibility failures.
                if index == 0 and response.status_code not in {401, 403, 500}:
                    break
        except httpx.HTTPError as exc:
            raise ProductionPlannerError(f"Failed to communicate with ProductionPlanner: {exc}", 502) from exc
        if last_response is None:
            raise ProductionPlannerError("Failed to communicate with ProductionPlanner", 502)
        return self._handle_response(last_response)

    async def get_info(self) -> Dict[str, Any]:
        return await self._request("GET", "info")

    async def list_projects(self) -> List[Dict[str, Any]]:
        data = await self._request("GET", "projects")
        return data.get("data", [])

    async def create_project(self, name: str, description: str = "", timezone: str = "UTC") -> Dict[str, Any]:
        payload = {"name": name, "description": description, "timezone": timezone}
        return await self._request("POST", "projects", json=payload)

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"projects/{project_id}")

    async def update_project(self, project_id: str, **kwargs) -> Dict[str, Any]:
        return await self._request("PATCH", f"projects/{project_id}", json=kwargs)

    async def add_date(self, project_id: str, date_str: str, label: str = "") -> Dict[str, Any]:
        payload = {"date": date_str, "label": label}
        return await self._request("POST", f"projects/{project_id}/dates", json=payload)

    @staticmethod
    def _extract_existing_date_keys(project_payload: Dict[str, Any]) -> set[Tuple[str, str]]:
        existing_dates = project_payload.get("dates")
        if not isinstance(existing_dates, list):
            return set()
        existing_keys: set[Tuple[str, str]] = set()
        for entry in existing_dates:
            if not isinstance(entry, dict):
                continue
            raw_date = str(entry.get("date") or "").strip()
            normalized_date = raw_date.split("T", 1)[0] if raw_date else ""
            if not normalized_date:
                continue
            label = str(entry.get("label") or "").strip().lower()
            existing_keys.add((normalized_date, label))
        return existing_keys

    async def sync_project_dates(self, project_id: str, date_entries: List[Tuple[str, str]]) -> None:
        if not date_entries:
            return
        existing_keys: set[Tuple[str, str]] = set()
        try:
            project = await self.get_project(project_id)
            if isinstance(project, dict):
                project_payload = project.get("data")
                if isinstance(project_payload, dict):
                    existing_keys = self._extract_existing_date_keys(project_payload)
        except ProductionPlannerError:
            logger.debug("Could not fetch ProductionPlanner project dates before sync", exc_info=True)

        for date_str, label in date_entries:
            key = (date_str, label.strip().lower())
            if key in existing_keys:
                continue
            try:
                await self.add_date(project_id, date_str, label)
                existing_keys.add(key)
            except ProductionPlannerError as exc:
                message = str(exc.message or "").lower()
                if exc.status_code in {400, 409} and ("already" in message or "exist" in message or "duplicate" in message):
                    existing_keys.add(key)
                    continue
                raise

    async def add_schedule_item(
        self,
        project_id: str,
        date_str: str,
        time: str = "",
        duration: int = 0,
        activity: str = "",
        type_: str = "",
    ) -> Dict[str, Any]:
        payload = {"time": time, "duration": duration, "activity": activity, "type": type_}
        payload = {k: v for k, v in payload.items() if v not in (None, "")}
        return await self._request("POST", f"projects/{project_id}/schedule/{date_str}", json=payload)

    async def add_team_member(
        self,
        project_id: str,
        name: str,
        role: str = "",
        email: str = "",
    ) -> Dict[str, Any]:
        payload = {"name": name, "role": role, "email": email}
        payload = {k: v for k, v in payload.items() if v not in (None, "")}
        return await self._request("POST", f"projects/{project_id}/team", json=payload)

    async def add_task(self, project_id: str, label: str) -> Dict[str, Any]:
        payload = {"label": label}
        return await self._request("POST", f"projects/{project_id}/tasks", json=payload)

    async def add_budget_item(
        self,
        project_id: str,
        name: str,
        category: str = "other",
        description: str = "",
        estimated_cost: float = 0,
        actual_cost: float = 0,
    ) -> Dict[str, Any]:
        payload = {
            "name": name,
            "category": category,
            "description": description,
            "estimatedCost": estimated_cost,
            "actualCost": actual_cost,
        }
        return await self._request("POST", f"projects/{project_id}/budget", json=payload)

    async def add_location(
        self,
        project_id: str,
        name: str,
        type_: str = "physical",
        details: str = "",
    ) -> Dict[str, Any]:
        payload = {"name": name, "type": type_, "details": details}
        payload = {k: v for k, v in payload.items() if v not in (None, "")}
        return await self._request("POST", f"projects/{project_id}/locations", json=payload)

    async def add_resource_link(
        self,
        project_id: str,
        name: str,
        url: str,
        folder_id: str = "",
    ) -> Dict[str, Any]:
        payload = {"name": name, "url": url}
        if folder_id:
            payload["folderId"] = folder_id
        return await self._request("POST", f"projects/{project_id}/resources/link", json=payload)


class ProductionPlannerError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
