import logging
import httpx
from typing import Optional, List, Dict, Any

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
                    "Authorization": f"Bearer {self.api_key}",
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
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
            try:
                error_data = response.json()
            except ValueError:
                error_data = None
            if isinstance(error_data, dict):
                message = error_data.get("message") or error_data.get("detail")
            elif isinstance(error_data, str):
                message = error_data
            else:
                message = None
            raise ProductionPlannerError(message or f"API error: {response.status_code}", response.status_code)
        if response.status_code == 204 or not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}

    async def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            response = await self.client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise ProductionPlannerError(f"Failed to communicate with ProductionPlanner: {exc}", 502) from exc
        return self._handle_response(response)

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
