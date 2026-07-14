import httpx
import pytest

from app.services.productionplanner import (
    ProductionPlannerClient,
    ProductionPlannerError,
    batch_task_labels,
)


def test_batch_task_labels_reduces_task_calls():
    labels = [f"Task {index}" for index in range(11)]

    batches = batch_task_labels(labels)

    assert batches == [
        "; ".join(f"Task {index}" for index in range(10)),
        "Task 10",
    ]


def test_handle_response_tolerates_empty_and_non_json_success():
    client = ProductionPlannerClient(api_key="test-key", base_url="https://api.productionplanner.io/v1")
    request = httpx.Request("POST", "https://api.productionplanner.io/v1/projects")

    assert client._handle_response(httpx.Response(204, request=request)) == {}
    assert client._handle_response(
        httpx.Response(
            200,
            request=request,
            content=b"ok",
            headers={"content-type": "text/plain"},
        )
    ) == {}


def test_handle_response_tolerates_non_object_error_json():
    client = ProductionPlannerClient(api_key="test-key", base_url="https://api.productionplanner.io/v1")
    request = httpx.Request("POST", "https://api.productionplanner.io/v1/projects")

    with pytest.raises(ProductionPlannerError, match="rate limited"):
        client._handle_response(
            httpx.Response(
                429,
                request=request,
                json="rate limited",
            )
        )
