"""Tests for digital/analog stagebox modeling in Product.specs.

Covers parsing/normalization of ``specs.stagebox`` (structured digital I/O) and the
shared digital-transport vocabulary. Mirrors the mixer model tests in
``test_mixer_spec.py``.
"""

from app.domain.inventory.stagebox_spec import (
    DIGITAL_PROTOCOLS,
    StageboxDigitalPort,
    StageboxSpec,
    normalize_stagebox_spec,
    parse_stagebox_spec,
)

GX4816_STAGEBOX = {
    "digital_io": [
        {"protocol": "dsnake", "channels_in": 48, "channels_out": 24},
        {"protocol": "dante", "channels_in": 64, "channels_out": 64},
    ],
}


# ---------------------------------------------------------------------------
# Parsing / normalization
# ---------------------------------------------------------------------------


def test_parse_stagebox_spec_absent():
    assert parse_stagebox_spec({"sb_inputs": 32}) is None
    assert parse_stagebox_spec(None) is None
    assert parse_stagebox_spec([{"connectors": []}]) is None
    assert parse_stagebox_spec({"stagebox": "not-a-dict"}) is None


def test_parse_stagebox_spec_valid():
    parsed = parse_stagebox_spec({"stagebox": GX4816_STAGEBOX})
    assert isinstance(parsed, StageboxSpec)
    assert len(parsed.digital_io) == 2
    assert isinstance(parsed.digital_io[0], StageboxDigitalPort)
    assert parsed.digital_io[0].protocol == "dsnake"
    assert parsed.digital_io[0].channels_in == 48
    assert parsed.digital_io[0].channels_out == 24


def test_parse_stagebox_spec_malformed_returns_none():
    # Wrong type for channels_in; Pydantic validation fails -> lenient None.
    assert parse_stagebox_spec({"stagebox": {"digital_io": [{"channels_in": "many"}]}}) is None
    assert parse_stagebox_spec({"stagebox": {"digital_io": "nope"}}) is None


def test_normalize_stagebox_spec_returns_clean_dict():
    normalized = normalize_stagebox_spec({"stagebox": GX4816_STAGEBOX})
    assert isinstance(normalized, dict)
    assert normalized == {
        "digital_io": [
            {"protocol": "dsnake", "channels_in": 48, "channels_out": 24},
            {"protocol": "dante", "channels_in": 64, "channels_out": 64},
        ]
    }


def test_normalize_stagebox_spec_absent_is_none():
    assert normalize_stagebox_spec({"sb_inputs": 1}) is None
    assert normalize_stagebox_spec(None) is None


def test_normalize_stagebox_spec_drops_none_fields():
    # A port with no channels set still appears, but unset protocol is dropped.
    normalized = normalize_stagebox_spec({"stagebox": {"digital_io": [{"protocol": "avb"}]}})
    assert normalized == {"digital_io": [{"protocol": "avb"}]}


# ---------------------------------------------------------------------------
# Shared digital-transport vocabulary (R4: identical across both repos)
# ---------------------------------------------------------------------------

# The canonical controlled digital-transport vocabulary. Must stay identical to
# stagewire's digital CONNECTOR_CHOICES set and rental's STAGEWIRE_STAGEBOX_PROTOCOLS
# (see docs/digital-stagebox-softpatch-plan.md §8.3 R4).
EXPECTED_DIGITAL_PROTOCOLS = {"dsnake", "dante", "aes50", "avb", "madi"}


def test_digital_protocols_is_canonical_set():
    assert DIGITAL_PROTOCOLS == EXPECTED_DIGITAL_PROTOCOLS


def test_digital_protocols_excludes_console_cards():
    # Stagebox transports are network/point-to-point links, not console expansion cards.
    assert "dsnake" in DIGITAL_PROTOCOLS
    assert "dante" in DIGITAL_PROTOCOLS
    assert "aes50" in DIGITAL_PROTOCOLS
    assert "avb" in DIGITAL_PROTOCOLS
    assert "madi" in DIGITAL_PROTOCOLS
    assert "io_card" not in DIGITAL_PROTOCOLS
    assert "option_card" not in DIGITAL_PROTOCOLS
    assert "waves" not in DIGITAL_PROTOCOLS
