"""Modeling support for digital/modular mixing consoles in ``Product.specs``.

Stagewire reads flat ``specs.inputs`` / ``specs.outputs`` counts from mixer
products, which works for fixed-architecture analog consoles but fails to model
modern digital systems (Allen & Heath GLD/SQ/dLive, Yamaha CL/QL, Behringer
Wing) where:

* **Bus pools are dynamic** - a console has a fixed pool of bus slots (e.g. a
  GLD-80 has 30 bus slots into 20 mix outputs), where a Mono bus consumes 1
  slot and a Stereo bus consumes 2 (LCR typically 3).
* **Physical I/O is decoupled** from DSP channels and external stageboxes.
* **Control surface is decoupled** from input/bus counts.

The existing ``specs.inputs`` / ``specs.outputs`` / ``specs.connectors`` keys
are left intact for backwards compatibility and catalog filtering. This module
adds optional, structured access to ``specs.mixer`` and the bus-pool slot math
that makes the dynamic modeling useful.

The ``mixer`` block is stored inside the existing free-form JSON ``specs`` blob,
so no database migration is required. All parsing here is intentionally lenient:
malformed or partial mixer data yields ``None`` rather than raising, matching
the defensive normalizers already used for connectors/power inlet.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Bus "type" determines how many pool slots a single mix consumes. Anything not
# explicitly stereo/lcr is treated as a mono (1-slot) bus.
BusType = Literal["mono", "stereo", "lcr"]

_ALLOWED_ARCHITECTURES = {
    "digital_bus_pool",
    "digital_fixed",
    "fixed_analog",
}

_STEREO_DEFAULT_SLOT_COST = 2
_LCR_DEFAULT_SLOT_COST = 3


class DspInputs(BaseModel):
    """DSP processing input channels, decoupled from physical sockets."""

    model_config = ConfigDict(extra="ignore")

    mono: int | None = None
    stereo: int | None = None
    fx_returns: int | None = None


class BusPool(BaseModel):
    """Capacity of a dynamic bus pool (slots -> mix outputs)."""

    model_config = ConfigDict(extra="ignore")

    total_slots: int | None = None
    max_mixes: int | None = None
    stereo_slot_cost: int = _STEREO_DEFAULT_SLOT_COST
    lcr_slot_cost: int = _LCR_DEFAULT_SLOT_COST
    allowed_roles: list[str] = Field(default_factory=list)
    odd_even_stereo_pairing: bool = False


class SurfaceBank(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    label: str | None = None
    faders: int | None = None


class Surface(BaseModel):
    model_config = ConfigDict(extra="ignore")

    banks: list[SurfaceBank] = Field(default_factory=list)
    layers: int | None = None


class ExpansionPort(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protocol: str | None = None
    max_channels_in: int | None = None
    max_channels_out: int | None = None
    slots: int | None = None
    max_channels: int | None = None


class MixerSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    architecture: str | None = None
    dsp_inputs: DspInputs | None = None
    bus_pool: BusPool | None = None
    dcas: int | None = None
    surface: Surface | None = None
    expansion_ports: list[ExpansionPort] = Field(default_factory=list)


def parse_mixer_spec(specs: Any) -> MixerSpec | None:
    """Extract and validate ``specs.mixer``.

    Returns ``None`` when there is no mixer block or when the data is malformed,
    so callers can safely treat the block as optional.
    """
    if not isinstance(specs, dict):
        return None
    mixer = specs.get("mixer")
    if mixer is None or not isinstance(mixer, dict):
        return None
    try:
        return MixerSpec(**mixer)
    except Exception:  # noqa: BLE001 - lenient: malformed mixer data yields None
        return None


def normalize_mixer_spec(specs: Any) -> dict | None:
    """Return a clean, JSON-serializable mixer dict for API responses.

    Drops unset (``None``) fields so the payload stays compact. Returns ``None``
    when no valid mixer block is present.
    """
    mixer = parse_mixer_spec(specs)
    if mixer is None:
        return None
    return mixer.model_dump(exclude_none=True, mode="json")


def dsp_input_channel_count(dsp_inputs: DspInputs | dict | None) -> int | None:
    """Total DSP input channel count.

    Stereo pairs are counted as two channels (mono + 2 * stereo + fx_returns).
    Returns ``None`` when no DSP inputs are described.
    """
    if dsp_inputs is None:
        return None
    if isinstance(dsp_inputs, dict):
        try:
            dsp_inputs = DspInputs(**dsp_inputs)
        except Exception:  # noqa: BLE001 - lenient: malformed DSP inputs yields None
            return None
    mono = dsp_inputs.mono or 0
    stereo = dsp_inputs.stereo or 0
    fx_returns = dsp_inputs.fx_returns or 0
    total = mono + 2 * stereo + fx_returns
    return total if total > 0 else None


def _coerce_bus_pool(bus_pool: BusPool | dict | None) -> BusPool | None:
    if bus_pool is None:
        return None
    if isinstance(bus_pool, BusPool):
        return bus_pool
    if isinstance(bus_pool, dict):
        try:
            return BusPool(**bus_pool)
        except Exception:  # noqa: BLE001 - lenient: malformed bus pool yields None
            return None
    return None


def compute_bus_slot_usage(
    bus_pool: BusPool | dict | None,
    mixes: list[str],
) -> dict[str, Any]:
    """Compute bus-pool slot consumption for a proposed mix configuration.

    ``mixes`` is a list of bus types (``"mono"``, ``"stereo"``, ``"lcr"`` or any
    other string treated as mono). A ``stereo`` bus consumes ``stereo_slot_cost``
    slots (default 2) and an ``lcr`` bus consumes ``lcr_slot_cost`` slots
    (default 3); everything else consumes 1 slot.

    Returns a dict with ``used_slots``, ``total_slots``, ``remaining_slots``,
    ``mix_count``, ``max_mixes``, ``within_slot_capacity`` and
    ``within_mix_limit``. Capacity/limit checks are ``None`` when the
    corresponding capacity figure is unknown.
    """
    pool = _coerce_bus_pool(bus_pool)
    stereo_cost = pool.stereo_slot_cost if pool else _STEREO_DEFAULT_SLOT_COST
    lcr_cost = pool.lcr_slot_cost if pool else _LCR_DEFAULT_SLOT_COST

    used = 0
    for mix in mixes:
        kind = str(mix).strip().lower()
        if kind == "stereo":
            used += stereo_cost
        elif kind == "lcr":
            used += lcr_cost
        else:
            used += 1

    total = pool.total_slots if pool else None
    max_mixes = pool.max_mixes if pool else None

    return {
        "used_slots": used,
        "total_slots": total,
        "remaining_slots": (total - used) if total is not None else None,
        "mix_count": len(mixes),
        "max_mixes": max_mixes,
        "within_slot_capacity": (used <= total) if total is not None else None,
        "within_mix_limit": (len(mixes) <= max_mixes) if max_mixes is not None else None,
    }


def validate_bus_configuration(
    bus_pool: BusPool | dict | None,
    mixes: list[str],
) -> dict[str, Any]:
    """Validate a proposed mix configuration against a console's bus pool.

    Returns the slot usage plus a boolean ``valid`` (``True`` only when the
    configuration is known to fit both the slot and mix-count limits) and a
    human-readable ``reason`` when it does not.
    """
    usage = compute_bus_slot_usage(bus_pool, mixes)
    valid = True
    reason = ""
    if usage["within_slot_capacity"] is False:
        valid = False
        reason = (
            f"Configuration uses {usage['used_slots']} slots but the bus pool "
            f"only has {usage['total_slots']}."
        )
    elif usage["within_mix_limit"] is False:
        valid = False
        reason = (
            f"Configuration defines {usage['mix_count']} mixes but the bus pool "
            f"allows at most {usage['max_mixes']}."
        )
    return {**usage, "valid": valid, "reason": reason}
