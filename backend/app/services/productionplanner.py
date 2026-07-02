import httpx
from typing import Optional, List, Dict, Any

from app.config import settings


class ProductionPlannerClient:
    def __init__(self, api_key: str = "", base_url: str = ""):
        self.base_url = (base_url or settings.productionplanner_base_url).rstrip("/")
        self.api_key = api_key or settings.productionplanner_api_key
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        if response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("message", f"API error: {response.status_code}")
            except Exception:
                message = f"API error: {response.status_code}"
            raise ProductionPlannerError(message, response.status_code)
        return response.json()

    async def get_info(self) -> Dict[str, Any]:
        response = await self.client.get("info")
        return self._handle_response(response)

    async def list_projects(self) -> List[Dict[str, Any]]:
        response = await self.client.get("projects")
        data = self._handle_response(response)
        return data.get("data", [])

    async def create_project(self, name: str, description: str = "", timezone: str = "UTC") -> Dict[str, Any]:
        payload = {"name": name, "description": description, "timezone": timezone}
        response = await self.client.post("projects", json=payload)
        return self._handle_response(response)

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        response = await self.client.get(f"projects/{project_id}")
        return self._handle_response(response)

    async def update_project(self, project_id: str, **kwargs) -> Dict[str, Any]:
        response = await self.client.patch(f"projects/{project_id}", json=kwargs)
        return self._handle_response(response)

    async def add_date(self, project_id: str, date_str: str, label: str = "") -> Dict[str, Any]:
        payload = {"date": date_str, "label": label}
        response = await self.client.post(f"projects/{project_id}/dates", json=payload)
        return self._handle_response(response)

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
        response = await self.client.post(f"projects/{project_id}/schedule/{date_str}", json=payload)
        return self._handle_response(response)

    async def add_team_member(
        self,
        project_id: str,
        name: str,
        role: str = "",
        email: str = "",
    ) -> Dict[str, Any]:
        payload = {"name": name, "role": role, "email": email}
        payload = {k: v for k, v in payload.items() if v not in (None, "")}
        response = await self.client.post(f"projects/{project_id}/team", json=payload)
        return self._handle_response(response)

    async def add_task(self, project_id: str, label: str) -> Dict[str, Any]:
        payload = {"label": label}
        response = await self.client.post(f"projects/{project_id}/tasks", json=payload)
        return self._handle_response(response)

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
        response = await self.client.post(f"projects/{project_id}/budget", json=payload)
        return self._handle_response(response)

    async def add_location(
        self,
        project_id: str,
        name: str,
        type_: str = "physical",
        details: str = "",
    ) -> Dict[str, Any]:
        payload = {"name": name, "type": type_, "details": details}
        payload = {k: v for k, v in payload.items() if v not in (None, "")}
        response = await self.client.post(f"projects/{project_id}/locations", json=payload)
        return self._handle_response(response)

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
        response = await self.client.post(f"projects/{project_id}/resources/link", json=payload)
        return self._handle_response(response)


class ProductionPlannerError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


productionplanner_client = ProductionPlannerClient()