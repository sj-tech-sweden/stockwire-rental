"""Modeling support for digital/analog stageboxes in ``Product.specs``.

Stagewire reads flat ``specs.sb_inputs`` / ``specs.sb_outputs`` counts from stagebox
products, which works for analog boxes but fails to capture the real digital transport
of a modern stagebox (Allen & Heath AR2412 / AB168 / DX168 / GX4816, a Dante / AES50 /
AVB / MADI box) where the digital link is a protocol (dSnake, Dante, …) carrying a
separate in/out channel count, decoupled from the physical XLR socket inventory.

The existing ``specs.sb_inputs`` / ``specs.sb_outputs`` / ``specs.connectors`` keys are
left intact for backwards compatibility and catalog filtering. This module adds an
optional, structured ``specs.stagebox`` block carrying the digital I/O, mirroring the
``specs.mixer`` model in :mod:`app.domain.inventory.mixer_spec`.

The ``stagebox`` block is stored inside the existing free-form JSON ``specs`` blob, so no
database migration is required. All parsing here is intentionally lenient: malformed or
partial data yields ``None`` rather than raising, matching the defensive normalizers
already used for connectors / power inlet / mixer.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Shared digital-transport vocabulary. Kept identical to stagewire's digital-connector set
# ({dsnake, dante, aes50, avb, madi}) so import mapping between the two repos is stable.
# Mixer expansion cards (io_card / option_card / waves / other) are intentionally excluded
# here: a stagebox's digital links are point-to-point or network transports, not console cards.
DIGITAL_PROTOCOLS: frozenset[str] = frozenset({"dsnake", "dante", "aes50", "avb", "madi"})
DIGITAL_PROTOCOL_OPTIONS: list[str] = ["dsnake", "dante", "aes50", "avb", "madi"]


class StageboxDigitalPort(BaseModel):
    """A single digital transport on a stagebox (in/out channel counts kept separate)."""

    model_config = ConfigDict(extra="ignore")

    protocol: str | None = None
    channels_in: int | None = None
    channels_out: int | None = None
    # Optional interface name (e.g. "dSnake", "dSnake Expander"). Carried through to stagewire's
    # Port.label so an imported product's channels are labelled instead of a bare connector.
    name: str | None = None


class StageboxSpec(BaseModel):
    """Structured digital I/O for a stagebox, stored as ``specs.stagebox``."""

    model_config = ConfigDict(extra="ignore")

    digital_io: list[StageboxDigitalPort] = Field(default_factory=list)


def parse_stagebox_spec(specs: Any) -> StageboxSpec | None:
    """Extract and validate ``specs.stagebox``.

    Returns ``None`` when there is no stagebox block or when the data is malformed, so
    callers can safely treat the block as optional.
    """
    if not isinstance(specs, dict):
        return None
    stagebox = specs.get("stagebox")
    if stagebox is None or not isinstance(stagebox, dict):
        return None
    try:
        return StageboxSpec(**stagebox)
    except Exception:  # noqa: BLE001 - lenient: malformed stagebox data yields None
        return None


def normalize_stagebox_spec(specs: Any) -> dict | None:
    """Return a clean, JSON-serializable stagebox dict for API responses.

    Drops unset (``None``) fields so the payload stays compact. Returns ``None`` when no
    valid stagebox block is present.
    """
    stagebox = parse_stagebox_spec(specs)
    if stagebox is None:
        return None
    return stagebox.model_dump(exclude_none=True, mode="json")
