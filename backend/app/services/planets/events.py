"""
Astronomical event detector for naked-eye planets.

Scans a date range and returns a deduplicated, sorted list of AstronomicalEvent
objects covering six event types:

  conjunction         – two bodies within CONJUNCTION_THRESHOLD_DEG of each other
  opposition          – superior planet (Mars/Jupiter/Saturn) > OPPOSITION_THRESHOLD_DEG from Sun
  mercury_elongation  – Mercury near its greatest angular distance from the Sun
  alignment           – 3+ planets within ALIGNMENT_ARC_DEG of ecliptic longitude arc
  venus_brilliancy    – Venus brighter than VENUS_BRILLIANCY_THRESHOLD (magnitude < -4.5)
  moon_occultation    – Moon within MOON_OCCULTATION_THRESHOLD_DEG of a planet

Sampling strategy
-----------------
- Most detectors sample once per day (midnight UTC).
- moon_occultation samples every 6 hours but only within the first 3 days of the
  window, because occultations are brief and location-dependent.

Deduplication
-------------
Events of the same (event_type, bodies set) that fall within 2 days of each
other are merged into a single event, keeping the sample with the most extreme
value (tightest separation, highest elongation, etc.).
"""

import math
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import ephem

from ...models.planet import AstronomicalEvent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONJUNCTION_THRESHOLD_DEG = 5.0
OPPOSITION_THRESHOLD_DEG = 170.0
MERCURY_ELONGATION_MIN_DEG = 15.0
ALIGNMENT_ARC_DEG = 30.0
ALIGNMENT_MIN_PLANETS = 3
VENUS_BRILLIANCY_THRESHOLD = -4.5
MOON_OCCULTATION_THRESHOLD_DEG = 0.5

# Window (in days on either side of the sample) used to judge "near maximum"
# elongation for Mercury.
_MERCURY_WINDOW_DAYS = 3

# Two events of the same type + bodies within this many days are deduplicated.
_DEDUP_WINDOW_DAYS = 2

# ---------------------------------------------------------------------------
# Name mappings
# ---------------------------------------------------------------------------

PLANET_NAMES_SV = {
    "Mercury": "Merkurius",
    "Venus": "Venus",
    "Mars": "Mars",
    "Jupiter": "Jupiter",
    "Saturn": "Saturnus",
    "Moon": "Månen",
}

EVENT_ICONS = {
    "conjunction": "conjunction",
    "opposition": "opposition",
    "mercury_elongation": "elongation",
    "alignment": "alignment",
    "venus_brilliancy": "brilliancy",
    "moon_occultation": "occultation",
}

# Planet classes in the order we always iterate them.
_PLANET_CLASSES = [
    ephem.Mercury,
    ephem.Venus,
    ephem.Mars,
    ephem.Jupiter,
    ephem.Saturn,
]

# Only superior planets can be in opposition (they orbit outside Earth's orbit).
_SUPERIOR_PLANET_CLASSES = [ephem.Mars, ephem.Jupiter, ephem.Saturn]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _make_observer(lat: float, lon: float) -> ephem.Observer:
    """Return a base ephem.Observer for the given WGS-84 co-ordinates."""
    obs = ephem.Observer()
    # ephem requires lat/lon as strings (degrees) or angle objects.
    obs.lat = str(lat)
    obs.lon = str(lon)
    # Disable atmospheric refraction for geometric positions.
    obs.pressure = 0
    return obs


def _set_date(observer: ephem.Observer, dt: datetime) -> None:
    """Set observer.date from a Python datetime (naive UTC assumed)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    observer.date = ephem.Date(dt)


def _dt_to_iso(dt: datetime) -> str:
    """Format a naive-UTC datetime as an ISO 8601 UTC string."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _separation_deg(body1, body2) -> float:
    """Return the angular separation between two computed ephem bodies, in degrees."""
    return math.degrees(float(ephem.separation(body1, body2)))


def _ecliptic_lon_deg(body, epoch) -> float:
    """Return the ecliptic longitude of a computed body in degrees [0, 360)."""
    ecl = ephem.Ecliptic(body, epoch=epoch)
    return math.degrees(float(ecl.lon)) % 360.0


# ---------------------------------------------------------------------------
# Detector sub-functions
# ---------------------------------------------------------------------------

def _detect_conjunctions(observer: ephem.Observer, dt: datetime) -> List[AstronomicalEvent]:
    """
    Detect conjunctions between any two of the five planets or between a planet
    and the Moon.

    Checks all 10 planet-planet pairs plus 5 planet-Moon pairs (15 total).
    A conjunction is flagged when the angular separation is below
    CONJUNCTION_THRESHOLD_DEG.
    """
    _set_date(observer, dt)
    date_iso = _dt_to_iso(dt)
    events: List[AstronomicalEvent] = []

    # Compute all planets and the Moon.
    bodies = {}
    for cls in _PLANET_CLASSES:
        body = cls()
        body.compute(observer)
        bodies[type(body).__name__] = body

    moon = ephem.Moon()
    moon.compute(observer)
    bodies["Moon"] = moon

    planet_names = [type(cls()).__name__ for cls in _PLANET_CLASSES]

    # Planet-planet pairs (10 combinations).
    for i in range(len(planet_names)):
        for j in range(i + 1, len(planet_names)):
            n1, n2 = planet_names[i], planet_names[j]
            sep = _separation_deg(bodies[n1], bodies[n2])
            if sep < CONJUNCTION_THRESHOLD_DEG:
                sv1 = PLANET_NAMES_SV[n1]
                sv2 = PLANET_NAMES_SV[n2]
                events.append(AstronomicalEvent(
                    event_type="conjunction",
                    bodies=[n1, n2],
                    date=date_iso,
                    description_sv=f"{sv1} och {sv2} i konjunktion ({sep:.1f}° separation)",
                    separation_deg=round(sep, 2),
                    event_icon=EVENT_ICONS["conjunction"],
                ))

    # Planet-Moon pairs (5 checks).
    for name in planet_names:
        sep = _separation_deg(bodies[name], moon)
        if sep < CONJUNCTION_THRESHOLD_DEG:
            sv = PLANET_NAMES_SV[name]
            sv_moon = PLANET_NAMES_SV["Moon"]
            events.append(AstronomicalEvent(
                event_type="conjunction",
                bodies=[name, "Moon"],
                date=date_iso,
                description_sv=f"{sv_moon} och {sv} i konjunktion ({sep:.1f}° separation)",
                separation_deg=round(sep, 2),
                event_icon=EVENT_ICONS["conjunction"],
            ))

    return events


def _detect_oppositions(observer: ephem.Observer, dt: datetime) -> List[AstronomicalEvent]:
    """
    Detect oppositions for superior planets (Mars, Jupiter, Saturn).

    ephem's body.elong gives the elongation from the Sun in radians (signed:
    positive = east, negative = west).  When abs(elong) > OPPOSITION_THRESHOLD_DEG
    the planet is near opposition (full opposition is 180°).
    """
    _set_date(observer, dt)
    date_iso = _dt_to_iso(dt)
    events: List[AstronomicalEvent] = []

    for cls in _SUPERIOR_PLANET_CLASSES:
        body = cls()
        body.compute(observer)
        elong_deg = math.degrees(abs(float(body.elong)))
        if elong_deg > OPPOSITION_THRESHOLD_DEG:
            name = type(body).__name__
            sv = PLANET_NAMES_SV[name]
            events.append(AstronomicalEvent(
                event_type="opposition",
                bodies=[name],
                date=date_iso,
                description_sv=f"{sv} i opposition – bästa tillfället att observera planeten",
                elongation_deg=round(elong_deg, 2),
                event_icon=EVENT_ICONS["opposition"],
            ))

    return events


def _mercury_elong_at(lat: float, lon: float, dt: datetime) -> float:
    """Return Mercury's signed elongation in degrees at a given time."""
    obs = _make_observer(lat, lon)
    _set_date(obs, dt)
    mercury = ephem.Mercury()
    mercury.compute(obs)
    return math.degrees(float(mercury.elong))


def _detect_mercury_elongation(observer: ephem.Observer, dt: datetime) -> List[AstronomicalEvent]:
    """
    Detect Mercury near greatest elongation.

    Mercury is a candidate when abs(elongation) > MERCURY_ELONGATION_MIN_DEG.
    We then confirm it is near the local maximum by sampling the elongation over
    a ±MERCURY_WINDOW_DAYS window; if the current value is within 1° of the
    maximum in that window, we report the event.

    Direction: positive elong = east of Sun = evening sky (western horizon after
    sunset); negative elong = west = morning sky (eastern horizon before sunrise).
    """
    _set_date(observer, dt)
    mercury = ephem.Mercury()
    mercury.compute(observer)
    elong_deg = math.degrees(float(mercury.elong))

    if abs(elong_deg) <= MERCURY_ELONGATION_MIN_DEG:
        return []

    # Sample elongation across the window to find the local maximum.
    # We need lat/lon to build fresh observers; extract from the observer angle objects.
    lat = math.degrees(float(observer.lat))
    lon = math.degrees(float(observer.lon))

    samples = []
    for day_offset in range(-_MERCURY_WINDOW_DAYS, _MERCURY_WINDOW_DAYS + 1):
        sample_dt = dt + timedelta(days=day_offset)
        try:
            samples.append(abs(_mercury_elong_at(lat, lon, sample_dt)))
        except Exception:
            pass

    if not samples:
        return []

    max_in_window = max(samples)
    if abs(elong_deg) < (max_in_window - 1.0):
        # Current value is not near the peak; skip to avoid duplicates.
        return []

    evening = elong_deg > 0
    if evening:
        desc_sv = "Bästa tillfället att se Merkurius – titta lågt i väster strax efter solnedgång"
    else:
        desc_sv = "Bästa tillfället att se Merkurius – titta lågt i öster strax före soluppgång"

    return [AstronomicalEvent(
        event_type="mercury_elongation",
        bodies=["Mercury"],
        date=_dt_to_iso(dt),
        description_sv=desc_sv,
        elongation_deg=round(abs(elong_deg), 2),
        event_icon=EVENT_ICONS["mercury_elongation"],
    )]


def _detect_alignment(observer: ephem.Observer, dt: datetime) -> List[AstronomicalEvent]:
    """
    Detect when 3 or more planets fit within ALIGNMENT_ARC_DEG of ecliptic
    longitude.

    Algorithm:
    1. Compute ecliptic longitude for all 5 planets.
    2. Try multiple circular arrangements to handle the 360/0° wraparound:
       - raw longitudes as-is
       - each planet's longitude shifted so the smallest is 0
       - for each planet, try folding longitudes > 180° down by subtracting 360°
         (handles groups that straddle the 0°/360° boundary)
    3. Sort by longitude; check every consecutive sub-window of 3, 4, 5 planets.
    4. Report the group with the most planets; break ties by tightest arc.
    5. Determine morning/evening by comparing the group's mean ecliptic longitude
       to the Sun's ecliptic longitude.
    """
    _set_date(observer, dt)
    date_iso = _dt_to_iso(dt)

    planet_lons: List[Tuple[str, float]] = []
    for cls in _PLANET_CLASSES:
        body = cls()
        body.compute(observer)
        name = type(body).__name__
        lon_deg = _ecliptic_lon_deg(body, epoch=observer.date)
        planet_lons.append((name, lon_deg))

    # Compute Sun's ecliptic longitude for morning/evening determination.
    sun = ephem.Sun()
    sun.compute(observer)
    sun_lon_deg = _ecliptic_lon_deg(sun, epoch=observer.date)

    # Build candidate longitude sets to handle wraparound.
    raw_lons = [lon for _, lon in planet_lons]
    names = [name for name, _ in planet_lons]

    candidate_sets: List[List[float]] = []

    # Raw values.
    candidate_sets.append(raw_lons[:])

    # Shift so minimum is 0.
    min_lon = min(raw_lons)
    candidate_sets.append([(lon - min_lon) % 360 for lon in raw_lons])

    # For each planet as an anchor, fold longitudes on the far side of the circle.
    # This helps when the group straddles 0°/360°.
    for anchor_idx in range(len(raw_lons)):
        adjusted = []
        for lon in raw_lons:
            diff = lon - raw_lons[anchor_idx]
            if diff > 180:
                adjusted.append(lon - 360)
            elif diff < -180:
                adjusted.append(lon + 360)
            else:
                adjusted.append(lon)
        candidate_sets.append(adjusted)

    best_group: Optional[List[str]] = None
    best_arc = float("inf")
    best_count = 0

    for lons in candidate_sets:
        # Sort planets by this longitude variant.
        sorted_pairs = sorted(zip(lons, names), key=lambda x: x[0])
        sorted_lons = [p[0] for p in sorted_pairs]
        sorted_names = [p[1] for p in sorted_pairs]
        n = len(sorted_lons)

        # Check all consecutive sub-windows of size 3..n.
        for size in range(ALIGNMENT_MIN_PLANETS, n + 1):
            for start in range(n - size + 1):
                arc = sorted_lons[start + size - 1] - sorted_lons[start]
                if arc <= ALIGNMENT_ARC_DEG:
                    group_names = sorted_names[start:start + size]
                    # Prefer more planets, then tighter arc.
                    if size > best_count or (size == best_count and arc < best_arc):
                        best_count = size
                        best_arc = arc
                        best_group = group_names

    if best_group is None:
        return []

    # Determine morning vs. evening by comparing mean group longitude to the Sun.
    # "Evening" means the group is roughly west of the meridian at sunset —
    # i.e., the group's mean longitude lags the Sun by less than 180°.
    # A simpler heuristic: planets west of the Sun (lower ecliptic longitude,
    # within 180°) are in the evening sky.
    group_lons = []
    for planet_name in best_group:
        for name, lon in planet_lons:
            if name == planet_name:
                group_lons.append(lon)
                break
    mean_group_lon = sum(group_lons) / len(group_lons)
    lon_diff = (mean_group_lon - sun_lon_deg) % 360
    # lon_diff in [0, 360): 0–180 means group leads Sun (evening sky),
    # 180–360 means group trails Sun (morning sky).
    evening = lon_diff < 180

    sky_word = "kvälls" if evening else "morgon"
    desc_sv = f"{best_count} planeter syns på rad i {sky_word}himlen!"

    return [AstronomicalEvent(
        event_type="alignment",
        bodies=best_group,
        date=date_iso,
        description_sv=desc_sv,
        alignment_count=best_count,
        event_icon=EVENT_ICONS["alignment"],
    )]


def _detect_venus_brilliancy(observer: ephem.Observer, dt: datetime) -> List[AstronomicalEvent]:
    """
    Detect when Venus reaches exceptional brightness (magnitude < -4.5).

    At these magnitudes Venus is visible in broad daylight.
    """
    _set_date(observer, dt)
    venus = ephem.Venus()
    venus.compute(observer)
    mag = float(venus.mag)

    if mag >= VENUS_BRILLIANCY_THRESHOLD:
        return []

    return [AstronomicalEvent(
        event_type="venus_brilliancy",
        bodies=["Venus"],
        date=_dt_to_iso(dt),
        description_sv="Venus är nu på sin ljusaste – den syns till och med i dagsljus!",
        magnitude=round(mag, 2),
        event_icon=EVENT_ICONS["venus_brilliancy"],
    )]


def _detect_moon_occultation(observer: ephem.Observer, dt: datetime) -> List[AstronomicalEvent]:
    """
    Detect when the Moon is within MOON_OCCULTATION_THRESHOLD_DEG of a planet.

    A threshold of 0.5° means the Moon is essentially covering the planet as seen
    from the observer's location (the Moon's disc is ~0.5° wide).
    """
    _set_date(observer, dt)
    date_iso = _dt_to_iso(dt)
    events: List[AstronomicalEvent] = []

    moon = ephem.Moon()
    moon.compute(observer)

    for cls in _PLANET_CLASSES:
        body = cls()
        body.compute(observer)
        sep = _separation_deg(moon, body)
        if sep < MOON_OCCULTATION_THRESHOLD_DEG:
            name = type(body).__name__
            sv_name = PLANET_NAMES_SV[name]
            events.append(AstronomicalEvent(
                event_type="moon_occultation",
                bodies=["Moon", name],
                date=date_iso,
                description_sv=f"Månen täcker {sv_name} – ett sällsynt skådespel",
                separation_deg=round(sep, 4),
                event_icon=EVENT_ICONS["moon_occultation"],
            ))

    return events


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _bodies_key(bodies: List[str]) -> frozenset:
    """Canonical frozenset key for a list of body names."""
    return frozenset(bodies)


def _best_value(event_type: str, events: List[AstronomicalEvent]) -> AstronomicalEvent:
    """
    From a group of same-type, same-bodies events, return the one with the
    most extreme value for that event type.

    Rules:
      conjunction / moon_occultation  – smallest separation_deg (tightest)
      opposition / mercury_elongation – largest elongation_deg (most extreme)
      alignment                       – largest alignment_count, then tightest arc
                                        (no per-event arc stored, so just pick first)
      venus_brilliancy                – smallest magnitude (brightest)
    """
    if event_type in ("conjunction", "moon_occultation"):
        return min(
            events,
            key=lambda e: e.separation_deg if e.separation_deg is not None else float("inf"),
        )
    if event_type in ("opposition", "mercury_elongation"):
        return max(
            events,
            key=lambda e: e.elongation_deg if e.elongation_deg is not None else 0.0,
        )
    if event_type == "alignment":
        return max(
            events,
            key=lambda e: (e.alignment_count or 0),
        )
    if event_type == "venus_brilliancy":
        return min(
            events,
            key=lambda e: e.magnitude if e.magnitude is not None else float("inf"),
        )
    # Fallback: keep the first (earliest).
    return events[0]


def _dedup_events(raw_events: List[AstronomicalEvent], start_dt: datetime) -> List[AstronomicalEvent]:
    """
    Deduplicate raw events and attach the days_away field.

    Groups events by (event_type, frozenset(bodies)).  Within each group,
    merges consecutive events that fall within _DEDUP_WINDOW_DAYS of each
    other into a single representative event (the one with the most extreme
    value).  Returns the list sorted by date.
    """
    # Sort all raw events by date first so we can cluster consecutively.
    def _parse_date(e: AstronomicalEvent) -> datetime:
        return datetime.strptime(e.date, "%Y-%m-%dT%H:%M:%SZ")

    raw_events = sorted(raw_events, key=_parse_date)

    # Group by (event_type, bodies frozenset).
    groups: dict = {}
    for event in raw_events:
        key = (event.event_type, _bodies_key(event.bodies))
        groups.setdefault(key, []).append(event)

    merged: List[AstronomicalEvent] = []

    for (event_type, _bodies_fs), group in groups.items():
        # Cluster consecutive events within _DEDUP_WINDOW_DAYS.
        clusters: List[List[AstronomicalEvent]] = []
        current_cluster: List[AstronomicalEvent] = []

        for event in group:
            event_dt = _parse_date(event)
            if not current_cluster:
                current_cluster.append(event)
            else:
                prev_dt = _parse_date(current_cluster[-1])
                if (event_dt - prev_dt).days <= _DEDUP_WINDOW_DAYS:
                    current_cluster.append(event)
                else:
                    clusters.append(current_cluster)
                    current_cluster = [event]

        if current_cluster:
            clusters.append(current_cluster)

        # For each cluster, keep the best representative.
        for cluster in clusters:
            best = _best_value(event_type, cluster)
            # Compute days_away from start_dt.
            event_dt = _parse_date(best)
            # Use naive UTC comparison; start_dt should also be naive UTC.
            start_naive = start_dt.replace(tzinfo=None) if start_dt.tzinfo else start_dt
            days_away = (event_dt.date() - start_naive.date()).days
            best.days_away = days_away
            merged.append(best)

    merged.sort(key=_parse_date)
    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_events(
    lat: float,
    lon: float,
    start_dt: datetime,
    end_dt: datetime,
) -> List[AstronomicalEvent]:
    """
    Scan the date range [start_dt, end_dt] and return detected astronomical
    events, deduplicated and sorted by date.

    Args:
        lat:      Observer latitude in decimal degrees (positive = North).
        lon:      Observer longitude in decimal degrees (positive = East).
        start_dt: Inclusive start of the search window (UTC).
        end_dt:   Inclusive end of the search window (UTC).

    Returns:
        A sorted, deduplicated list of AstronomicalEvent objects.
    """
    # Ensure naive UTC datetimes for ephem compatibility.
    if start_dt.tzinfo is not None:
        start_dt = start_dt.astimezone(timezone.utc).replace(tzinfo=None)
    if end_dt.tzinfo is not None:
        end_dt = end_dt.astimezone(timezone.utc).replace(tzinfo=None)

    base_observer = _make_observer(lat, lon)

    # Build daily sample times (midnight UTC each day).
    daily_samples: List[datetime] = []
    current = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    while current <= end_dt:
        daily_samples.append(current)
        current += timedelta(days=1)

    # Build 6-hourly samples for moon_occultation, limited to first 3 days.
    occultation_cutoff = start_dt + timedelta(days=3)
    occultation_samples: List[datetime] = []
    current = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    while current <= min(end_dt, occultation_cutoff):
        occultation_samples.append(current)
        current += timedelta(hours=6)

    raw_events: List[AstronomicalEvent] = []

    # --- Daily detectors ---
    detectors_daily = [
        ("conjunctions", _detect_conjunctions),
        ("oppositions", _detect_oppositions),
        ("mercury_elongation", _detect_mercury_elongation),
        ("alignment", _detect_alignment),
        ("venus_brilliancy", _detect_venus_brilliancy),
    ]

    for sample_dt in daily_samples:
        for detector_name, detector_fn in detectors_daily:
            try:
                found = detector_fn(base_observer, sample_dt)
                raw_events.extend(found)
            except Exception as exc:
                logger.warning(
                    "Event detector '%s' failed at %s: %s",
                    detector_name,
                    sample_dt.isoformat(),
                    exc,
                )

    # --- 6-hourly occultation detector ---
    for sample_dt in occultation_samples:
        try:
            found = _detect_moon_occultation(base_observer, sample_dt)
            raw_events.extend(found)
        except Exception as exc:
            logger.warning(
                "Event detector 'moon_occultation' failed at %s: %s",
                sample_dt.isoformat(),
                exc,
            )

    logger.info(
        "detect_events: %d raw events found over %d daily samples "
        "and %d occultation samples",
        len(raw_events),
        len(daily_samples),
        len(occultation_samples),
    )

    return _dedup_events(raw_events, start_dt)
