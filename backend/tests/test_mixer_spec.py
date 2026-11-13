"""Tests for digital-console mixer modeling in Product.specs.

Covers parsing/normalization of ``specs.mixer`` and the bus-pool slot math that
lets Stagewire model dynamic bus pools (mono=1 slot, stereo=2, lcr=3).
"""

from app.domain.inventory.mixer_spec import (
    MixerSpec,
    compute_bus_slot_usage,
    dsp_input_channel_count,
    normalize_mixer_spec,
    parse_mixer_spec,
    validate_bus_configuration,
)

GLD_MIXER = {
    "architecture": "digital_bus_pool",
    "dsp_inputs": {"mono": 44, "stereo": 2, "fx_returns": 8},
    "bus_pool": {
        "total_slots": 30,
        "max_mixes": 20,
        "stereo_slot_cost": 2,
        "lcr_slot_cost": 3,
        "allowed_roles": ["aux", "group", "matrix", "main", "fx_send"],
        "odd_even_stereo_pairing": False,
    },
    "dcas": 16,
    "surface": {
        "banks": [
            {"id": "A", "label": "Left Bank", "faders": 12},
            {"id": "B", "label": "Right Bank", "faders": 8},
        ],
        "layers": 4,
    },
    "expansion_ports": [
        {"protocol": "dsnake", "max_channels_in": 48, "max_channels_out": 24},
        {"protocol": "io_card", "slots": 1, "max_channels": 64},
    ],
}


# ---------------------------------------------------------------------------
# Parsing / normalization
# ---------------------------------------------------------------------------


def test_parse_mixer_spec_absent():
    assert parse_mixer_spec({"inputs": 48}) is None
    assert parse_mixer_spec(None) is None
    assert parse_mixer_spec([{"connectors": []}]) is None
    assert parse_mixer_spec({"mixer": "not-a-dict"}) is None


def test_parse_mixer_spec_valid():
    parsed = parse_mixer_spec({"mixer": GLD_MIXER})
    assert isinstance(parsed, MixerSpec)
    assert parsed.architecture == "digital_bus_pool"
    assert parsed.bus_pool.total_slots == 30
    assert parsed.bus_pool.stereo_slot_cost == 2
    assert parsed.dcas == 16
    assert len(parsed.surface.banks) == 2
    assert len(parsed.expansion_ports) == 2


def test_parse_mixer_spec_applies_defaults():
    parsed = parse_mixer_spec({"mixer": {"bus_pool": {"total_slots": 30}}})
    assert parsed is not None
    assert parsed.bus_pool is not None
    assert parsed.bus_pool.stereo_slot_cost == 2
    assert parsed.bus_pool.lcr_slot_cost == 3


def test_parse_mixer_spec_malformed_returns_none():
    # Wrong types for slots; Pydantic validation fails -> lenient None.
    assert parse_mixer_spec({"mixer": {"bus_pool": {"total_slots": "lots"}}}) is None


def test_normalize_mixer_spec_returns_clean_dict():
    normalized = normalize_mixer_spec({"mixer": GLD_MIXER})
    assert isinstance(normalized, dict)
    assert normalized["architecture"] == "digital_bus_pool"
    assert normalized["bus_pool"]["total_slots"] == 30
    assert normalized["surface"]["layers"] == 4
    # No extra None keys should be present at the top level.
    assert "dcas" in normalized


def test_normalize_mixer_spec_absent_is_none():
    assert normalize_mixer_spec({"inputs": 1}) is None
    assert normalize_mixer_spec(None) is None


# ---------------------------------------------------------------------------
# DSP input channel count
# ---------------------------------------------------------------------------


def test_dsp_input_channel_count_sums_pairs():
    assert dsp_input_channel_count({"mono": 44, "stereo": 2, "fx_returns": 8}) == 44 + 4 + 8


def test_dsp_input_channel_count_none_when_empty():
    assert dsp_input_channel_count(None) is None
    assert dsp_input_channel_count({}) is None
    assert dsp_input_channel_count({"mono": 0, "stereo": 0, "fx_returns": 0}) is None


# ---------------------------------------------------------------------------
# Bus-pool slot usage
# ---------------------------------------------------------------------------


def test_compute_bus_slot_usage_mixes_costs():
    usage = compute_bus_slot_usage(
        GLD_MIXER["bus_pool"],
        ["mono", "mono", "stereo", "lcr", "aux"],
    )
    # 1 + 1 + 2 + 3 + 1 = 8 slots, 5 mixes
    assert usage["used_slots"] == 8
    assert usage["mix_count"] == 5
    assert usage["total_slots"] == 30
    assert usage["remaining_slots"] == 22
    assert usage["within_slot_capacity"] is True
    assert usage["within_mix_limit"] is True


def test_compute_bus_slot_usage_capacity_none_without_pool():
    usage = compute_bus_slot_usage(None, ["stereo", "stereo"])
    assert usage["used_slots"] == 4
    assert usage["total_slots"] is None
    assert usage["within_slot_capacity"] is None


def test_validate_bus_configuration_over_slot_capacity():
    # 20 stereo mixes * 2 slots = 40 > 30 slots.
    mixes = ["stereo"] * 20
    result = validate_bus_configuration(GLD_MIXER["bus_pool"], mixes)
    assert result["valid"] is False
    assert "slots" in result["reason"]
    assert result["used_slots"] == 40


def test_validate_bus_configuration_over_mix_limit():
    # 21 mono mixes exceeds max_mixes=20, but fits in 30 slots.
    mixes = ["mono"] * 21
    result = validate_bus_configuration(GLD_MIXER["bus_pool"], mixes)
    assert result["valid"] is False
    assert "mixes" in result["reason"].lower()


def test_validate_bus_configuration_valid():
    mixes = ["stereo"] * 10 + ["mono"] * 10  # 20 slots, 20 mixes
    result = validate_bus_configuration(GLD_MIXER["bus_pool"], mixes)
    assert result["valid"] is True
    assert result["reason"] == ""


# ---------------------------------------------------------------------------
# Public Stagewire device-specs endpoint
# ---------------------------------------------------------------------------


def test_device_specs_includes_mixer(client):
    create = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": "AHO-GLD80",
            "name": "Allen & Heath GLD-80",
            "specs": {
                "inputs": 48,
                "outputs": 20,
                "mixer": GLD_MIXER,
            },
        },
    )
    assert create.status_code in (200, 201), create.text
    product_id = create.json()["id"]

    resp = client.get(f"/api/v1/stockwire/products/{product_id}/device-specs")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["inputs"] == 48
    assert body["outputs"] == 20
    assert body["mixer"] == normalize_mixer_spec({"mixer": GLD_MIXER})


def test_device_specs_mixer_absent_is_none(client):
    create = client.post(
        "/api/v1/inventory/products",
        json={"sku": "ANALOG-16", "name": "Analog 16", "specs": {"inputs": 16, "outputs": 4}},
    )
    assert create.status_code in (200, 201), create.text
    product_id = create.json()["id"]

    resp = client.get(f"/api/v1/stockwire/products/{product_id}/device-specs")
    assert resp.status_code == 200, resp.text
    assert resp.json()["mixer"] is None


# ---------------------------------------------------------------------------
# Catalog filtering by mixer attributes
# ---------------------------------------------------------------------------


def test_list_products_filters_by_min_bus_slots(client):
    digital = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": "DIGITAL-1",
            "name": "Digital Console",
            "specs": {"mixer": {"architecture": "digital_bus_pool", "bus_pool": {"total_slots": 30}}},
        },
    )
    analog = client.post(
        "/api/v1/inventory/products",
        json={"sku": "ANALOG-2", "name": "Analog Console", "specs": {"inputs": 16, "outputs": 4}},
    )
    assert digital.status_code in (200, 201) and analog.status_code in (200, 201)

    resp = client.get("/api/v1/inventory/products?min_bus_slots=25")
    assert resp.status_code == 200, resp.text
    returned_ids = {item["id"] for item in resp.json()["items"]}
    assert digital.json()["id"] in returned_ids
    assert analog.json()["id"] not in returned_ids


def test_list_products_filters_by_mixer_architecture(client):
    digital = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": "DIGITAL-3",
            "name": "Digital Console",
            "specs": {"mixer": {"architecture": "digital_bus_pool"}},
        },
    )
    analog = client.post(
        "/api/v1/inventory/products",
        json={"sku": "ANALOG-3", "name": "Analog Console", "specs": {"inputs": 8, "outputs": 2}},
    )
    assert digital.status_code in (200, 201) and analog.status_code in (200, 201)

    resp = client.get("/api/v1/inventory/products?mixer_architecture=digital_bus_pool")
    assert resp.status_code == 200, resp.text
    returned_ids = {item["id"] for item in resp.json()["items"]}
    assert digital.json()["id"] in returned_ids
    assert analog.json()["id"] not in returned_ids
