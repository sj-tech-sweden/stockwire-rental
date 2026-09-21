"""Routing helpers: geocoding + drive-time estimation via OpenStreetMap.

These features are optional. When ``routing_enabled`` is ``False`` or when the
external services (Nominatim for geocoding, OSRM for routing) are unreachable,
the helpers degrade gracefully: geocoding returns ``None`` and drive-time
computation reports ``available=False`` with a human-readable note so the UI can
show a friendly fallback instead of failing.
"""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass

import httpx

from app.config import settings


_GEOCODE_CACHE: dict[str, tuple[float, tuple[float, float] | None]] = {}
_GEOCODE_TTL_SECONDS = 60 * 60 * 24  # 24h


@dataclass
class StopAddress:
    stop_id: int
    address: str
    lat: float | None = None
    lon: float | None = None


@dataclass
class DriveTimeLeg:
    stop_id: int
    leg_duration_s: float | None
    leg_distance_m: float | None


@dataclass
class DriveTimeResult:
    available: bool
    note: str | None
    legs: list[DriveTimeLeg]
    total_duration_s: float | None
    total_distance_m: float | None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two coordinates in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _coord_for_stop(stop: StopAddress) -> tuple[float, float] | None:
    """Return coordinates for a stop, preferring stored lat/lon over geocoding."""
    if stop.lat is not None and stop.lon is not None:
        return (stop.lat, stop.lon)
    return geocode(stop.address)


def _haversine_matrix(points: list[tuple[float, float]]) -> list[list[float]] | None:
    """Build an NxN distance matrix (km) between points as a routing fallback."""
    n = len(points)
    if n == 0:
        return None
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = haversine_km(points[i][0], points[i][1], points[j][0], points[j][1])
    return matrix


# Country-name -> ISO 3166-1 alpha-2, used to bias Nominatim with ``countrycodes``.
_COUNTRY_CODES = {
    "sweden": "se", "sverige": "se",
    "germany": "de", "deutschland": "de",
    "norway": "no", "norge": "no",
    "denmark": "dk", "danmark": "dk",
    "finland": "fi", "suomi": "fi",
    "united kingdom": "gb", "great britain": "gb", "england": "gb", "scotland": "gb",
    "united states": "us", "usa": "us", "america": "us",
    "netherlands": "nl", "nederland": "nl",
    "belgium": "be", "belgië": "be", "belgique": "be",
    "france": "fr",
    "spain": "es", "españa": "es",
    "italy": "it", "italia": "it",
    "poland": "pl",
    "austria": "at", "österreich": "at",
    "switzerland": "ch", "schweiz": "ch", "suisse": "ch",
    "iceland": "is",
    "estonia": "ee", "eesti": "ee",
    "latvia": "lv",
    "lithuania": "lt",
}


def _geocode_once(params: dict) -> tuple[float, float] | None:
    resp = httpx.get(
        f"{settings.routing_nominatim_url.rstrip('/')}/search",
        params=params,
        headers={"User-Agent": "StockwireRental/1.0"},
        timeout=settings.routing_timeout_seconds,
    )
    resp.raise_for_status()
    data = resp.json()
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None


def geocode(address: str) -> tuple[float, float] | None:
    """Resolve a free-text address to ``(lat, lon)`` using Nominatim.

    Returns ``None`` when routing is disabled, the address is empty, or the
    geocoder is unreachable / returns no match. Results are cached per address.

    The query is biased by ``countrycodes`` when a country is detected, and a
    fallback strips the leading token (often a venue/company name) when the full
    query fails, which improves matches for "Name, Street, City, Country" inputs.
    """
    if not address or not address.strip():
        return None
    key = address.strip().lower()
    now = time.time()
    cached = _GEOCODE_CACHE.get(key)
    if cached and now - cached[0] < _GEOCODE_TTL_SECONDS:
        return cached[1]
    if not settings.routing_enabled:
        return None
    try:
        country = None
        for token in re.split(r"[,\n]", address):
            low = token.strip().lower()
            if low in _COUNTRY_CODES:
                country = _COUNTRY_CODES[low]
                break

        attempts = [{"q": address, "format": "json", "limit": 1, "addressdetails": 1}]
        if country:
            attempts[0]["countrycodes"] = country
        # Fallback: drop the leading token (often a venue/company name) and retry.
        parts = [p.strip() for p in address.split(",")]
        if len(parts) > 1:
            fallback_q = ", ".join(parts[1:])
            fb = {"q": fallback_q, "format": "json", "limit": 1, "addressdetails": 1}
            if country:
                fb["countrycodes"] = country
            attempts.append(fb)

        coords = None
        for params in attempts:
            coords = _geocode_once(params)
            if coords:
                break
        _GEOCODE_CACHE[key] = (now, coords)
        return coords
    except Exception:
        return None


def compute_drive_times(
    origin: str | None,
    stops: list[StopAddress],
    pickup_points: list[tuple[float, float]] | None = None,
) -> DriveTimeResult:
    """Estimate drive time/distance for each stop relative to the previous one.

    Equipment pickup points (``pickup_points``) are inserted as leading waypoints
    before the delivery stops, so the first stop's inbound leg starts from the
    last pickup. Returns ``available=False`` with a note when coordinates or the
    routing service are unavailable.
    """
    stops = stops or []
    if not settings.routing_enabled:
        return DriveTimeResult(False, "Routing is disabled.", [], None, None)
    if not stops:
        return DriveTimeResult(True, None, [], 0.0, 0.0)

    pickup_points = pickup_points or []
    coords: list[tuple[float, float] | None] = []
    if origin:
        coords.append(geocode(origin))
    for p in pickup_points:
        coords.append(p)
    for s in stops:
        coords.append(_coord_for_stop(s))

    if any(c is None for c in coords):
        return DriveTimeResult(
            False, "Could not resolve all stop addresses to coordinates.", [], None, None
        )

    coord_str = ";".join(f"{lon},{lat}" for lat, lon in coords)  # type: ignore[union-attr]
    url = f"{settings.routing_osrm_url.rstrip('/')}/route/v1/driving/{coord_str}"
    try:
        resp = httpx.get(url, params={"overview": "false"}, timeout=settings.routing_timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return DriveTimeResult(False, "Routing service is unavailable.", [], None, None)

    if data.get("code") != "Ok" or not data.get("routes"):
        return DriveTimeResult(False, "Routing service returned no route.", [], None, None)

    legs = data["routes"][0]["legs"]
    prefix = (1 if origin else 0) + len(pickup_points)
    result_legs: list[DriveTimeLeg] = []
    total_d = 0.0
    total_dist = 0.0
    for leg in legs:
        if leg.get("duration"):
            total_d += leg["duration"]
        if leg.get("distance"):
            total_dist += leg["distance"]
    for i, s in enumerate(stops):
        leg_idx = prefix + i - 1
        if leg_idx < 0 or leg_idx >= len(legs):
            result_legs.append(DriveTimeLeg(s.stop_id, None, None))
            continue
        leg = legs[leg_idx]
        result_legs.append(DriveTimeLeg(s.stop_id, leg.get("duration"), leg.get("distance")))
    return DriveTimeResult(True, None, result_legs, total_d, total_dist)


def compute_distance_matrix(
    points: list[tuple[float, float]],
) -> list[list[float]] | None:
    """Return an NxN duration matrix (seconds) between all points via OSRM table."""
    if not points:
        return None
    coord_str = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = f"{settings.routing_osrm_url.rstrip('/')}/table/v1/driving/{coord_str}"
    try:
        resp = httpx.get(
            url,
            params={"sources": "all", "destinations": "all"},
            timeout=settings.routing_timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok" or "durations" not in data:
            return None
        return data["durations"]
    except Exception:
        return None


def optimize_stop_order(
    origin: str | None,
    stops: list[StopAddress],
    pickup_points: list[tuple[float, float]] | None = None,
) -> list[int] | None:
    """Reorder delivery stops by nearest-neighbour using drive-time durations.

    Equipment pickup points (``pickup_points``) are treated as a fixed leading
    prefix: every route starts from the last pickup (or ``origin``), and only the
    delivery stops are reordered. Returns the delivery stop ids in optimized
    visiting order, or ``None`` when routing is unavailable.
    """
    stops = stops or []
    if not settings.routing_enabled or len(stops) < 2:
        return None

    pickup_points = pickup_points or []
    coords: list[tuple[float, float] | None] = []
    if origin:
        coords.append(geocode(origin))
    for p in pickup_points:
        coords.append(p)
    for s in stops:
        coords.append(_coord_for_stop(s))
    if any(c is None for c in coords):
        return None

    resolved = [c for c in coords if c is not None]
    matrix = compute_distance_matrix(resolved)
    if not matrix:
        # Fallback: straight-line distance matrix when the routing service is down
        matrix = _haversine_matrix(resolved)
    if not matrix:
        return None

    prefix = (1 if origin else 0) + len(pickup_points)
    n = len(stops)
    visited_matrix = [False] * len(resolved)
    # Start from the last prefix point (or first stop when there is no prefix).
    start_matrix = (prefix - 1) if prefix > 0 else 0
    visited_matrix[start_matrix] = True

    order_matrix: list[int] = []
    current = start_matrix
    for _ in range(n):
        row = matrix[current]
        best = None
        best_cost = float("inf")
        for j in range(n):
            mj = prefix + j
            if visited_matrix[mj]:
                continue
            cost = row[mj] if mj < len(row) else float("inf")
            if cost is not None and cost < best_cost:
                best_cost = cost
                best = mj
        if best is None:
            break
        visited_matrix[best] = True
        order_matrix.append(best)
        current = best

    for j in range(n):
        mj = prefix + j
        if not visited_matrix[mj]:
            order_matrix.append(mj)

    return [stops[m - prefix].stop_id for m in order_matrix]
