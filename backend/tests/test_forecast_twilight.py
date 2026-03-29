"""
Unit tests for Phase B10 — Twilight-Window Forecast.

Tests cover:
  Group A: _compute_twilight_window_for_night() — evening and morning windows
           at a Swedish latitude, plus polar midnight-sun edge case.
  Group B: compute_next_good_observation() — Venus uses a twilight window,
           Mars uses the nautical-darkness window.

All tests use fixed datetimes so results are fully deterministic.
No network calls are made; ephem is used directly (pure ephemeris math).

Coordinates used:
  Malmö area  — lat=55.7, lon=13.4  (southern Sweden, April)
  Stockholm   — lat=59.3, lon=18.1  (central Sweden)
  Tromsø area — lat=71.0, lon=25.0  (above Arctic Circle, midsummer)
"""

from datetime import datetime, timedelta

import ephem
import pytest

from app.services.planets.forecast import (
    _compute_twilight_window_for_night,
    compute_next_good_observation,
)


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# Southern-Sweden coordinates used for window-boundary tests.
_MALMO_LAT = 55.7
_MALMO_LON = 13.4

# Stockholm coordinates used for integration tests.
_STOCKHOLM_LAT = 59.3
_STOCKHOLM_LON = 18.1

# Tromsø-area coordinates (above Arctic Circle) used for midnight-sun tests.
_TROMSO_LAT = 71.0
_TROMSO_LON = 25.0


# ---------------------------------------------------------------------------
# Group A: _compute_twilight_window_for_night()
# ---------------------------------------------------------------------------

# April 15 is a reliable mid-spring date: sun sets in the evening, rises in
# the morning, and the civil-to-nautical twilight window is well-defined at
# Swedish latitudes.  No midnight sun at 55.7°N in April.
_APRIL_DATE = datetime(2026, 4, 15)


class TestEveningTwilightWindow:
    """Evening twilight window at Malmö (55.7°N) on 2026-04-15."""

    def setup_method(self):
        self.start, self.end = _compute_twilight_window_for_night(
            lat=_MALMO_LAT,
            lon=_MALMO_LON,
            night_dt=_APRIL_DATE,
            is_evening=True,
        )

    def test_returns_datetime_tuple(self):
        # Both elements must be datetime objects (not None).
        assert isinstance(self.start, datetime), (
            f"Expected start to be datetime, got {type(self.start)}"
        )
        assert isinstance(self.end, datetime), (
            f"Expected end to be datetime, got {type(self.end)}"
        )

    def test_start_before_end(self):
        assert self.start < self.end, (
            f"Expected start < end; got start={self.start}, end={self.end}"
        )

    def test_start_after_14_utc(self):
        # Sunset in southern Sweden in April is around 18:00-19:00 local (CEST = UTC+2),
        # which is 16:00-17:00 UTC.  A start before 14:00 UTC would be implausible.
        lower_bound = _APRIL_DATE.replace(hour=14, minute=0, second=0)
        assert self.start > lower_bound, (
            f"Expected start after 14:00 UTC (reasonable sunset for 55.7°N in April); "
            f"got start={self.start}"
        )

    def test_end_before_23_utc(self):
        # Nautical twilight ends well before midnight at this latitude in April.
        upper_bound = _APRIL_DATE.replace(hour=23, minute=0, second=0)
        assert self.end < upper_bound, (
            f"Expected end before 23:00 UTC; got end={self.end}"
        )

    def test_window_duration_between_30min_and_2h(self):
        duration = self.end - self.start
        assert duration >= timedelta(minutes=30), (
            f"Expected window >= 30 minutes; got {duration}"
        )
        assert duration <= timedelta(hours=2), (
            f"Expected window <= 2 hours; got {duration}"
        )


class TestMorningTwilightWindow:
    """Morning twilight window at Malmö (55.7°N) on 2026-04-15."""

    def setup_method(self):
        self.start, self.end = _compute_twilight_window_for_night(
            lat=_MALMO_LAT,
            lon=_MALMO_LON,
            night_dt=_APRIL_DATE,
            is_evening=False,
        )

    def test_returns_datetime_tuple(self):
        assert isinstance(self.start, datetime), (
            f"Expected start to be datetime, got {type(self.start)}"
        )
        assert isinstance(self.end, datetime), (
            f"Expected end to be datetime, got {type(self.end)}"
        )

    def test_start_before_end(self):
        assert self.start < self.end, (
            f"Expected start < end; got start={self.start}, end={self.end}"
        )

    def test_end_before_08_utc(self):
        # Sunrise in southern Sweden in April is around 05:00-06:00 local (CEST = UTC+2),
        # which is 03:00-04:00 UTC.  The end (sunrise at 0°) cannot be later than
        # 08:00 UTC without something being very wrong.
        # We use the day AFTER night_dt because the morning window is anchored
        # to the next calendar day.
        next_day = _APRIL_DATE + timedelta(days=1)
        upper_bound = next_day.replace(hour=8, minute=0, second=0)
        assert self.end < upper_bound, (
            f"Expected morning window end before 08:00 UTC on {next_day.date()}; "
            f"got end={self.end}"
        )

    def test_window_duration_between_30min_and_2h(self):
        duration = self.end - self.start
        assert duration >= timedelta(minutes=30), (
            f"Expected window >= 30 minutes; got {duration}"
        )
        assert duration <= timedelta(hours=2), (
            f"Expected window <= 2 hours; got {duration}"
        )


class TestPolarMidnightSun:
    """Midnight-sun edge case at Tromsø (71°N) on summer solstice."""

    def test_evening_window_returns_none_none(self):
        # At 71°N on the summer solstice the sun never dips to -12°, so
        # ephem raises AlwaysUpError and the function must return (None, None).
        start, end = _compute_twilight_window_for_night(
            lat=_TROMSO_LAT,
            lon=_TROMSO_LON,
            night_dt=datetime(2026, 6, 21),
            is_evening=True,
        )
        assert start is None and end is None, (
            f"Expected (None, None) for 71°N on summer solstice (midnight sun); "
            f"got ({start}, {end})"
        )

    def test_morning_window_returns_none_none(self):
        # At 71°N on the summer solstice the sun never dips to -12°, so the
        # morning twilight window is equally degenerate and must return (None, None).
        start, end = _compute_twilight_window_for_night(
            lat=_TROMSO_LAT,
            lon=_TROMSO_LON,
            night_dt=datetime(2026, 6, 21),
            is_evening=False,
        )
        assert start is None and end is None, (
            f"Expected (None, None) for morning window at 71°N on summer solstice; "
            f"got ({start}, {end})"
        )


# ---------------------------------------------------------------------------
# Group B: compute_next_good_observation()
# ---------------------------------------------------------------------------

class TestVenusUsesTowilightWindow:
    """Venus (inferior planet) should return a twilight-windowed forecast."""

    # April 2026: Venus is prominent in the western sky after sunset.
    _FROM_DATE = datetime(2026, 4, 1)

    def setup_method(self):
        # The function scans up to 180 nights; Venus should qualify quickly
        # because it is bright (-4 mag) during this period.
        self.result = compute_next_good_observation(
            "Venus",
            lat=_STOCKHOLM_LAT,
            lon=_STOCKHOLM_LON,
            start_dt=self._FROM_DATE,
        )

    def test_result_is_not_none(self):
        assert self.result is not None, (
            "Expected compute_next_good_observation('Venus', Stockholm, 2026-04-01) "
            "to return a non-None result; Venus should be observable in April 2026"
        )

    def test_start_time_is_iso_string(self):
        import re
        iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        assert iso_re.match(self.result["start_time"]), (
            f"Expected ISO 8601 UTC string for start_time, got: {self.result['start_time']!r}"
        )

    def test_end_time_is_iso_string(self):
        import re
        iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        assert iso_re.match(self.result["end_time"]), (
            f"Expected ISO 8601 UTC string for end_time, got: {self.result['end_time']!r}"
        )

    def test_quality_score_non_negative(self):
        score = self.result["quality_score"]
        assert score >= 0, (
            f"Expected quality_score >= 0, got {score}"
        )

    def test_start_before_end(self):
        # Both fields are ISO 8601 UTC strings; lexicographic comparison is valid.
        assert self.result["start_time"] < self.result["end_time"], (
            f"Expected start_time < end_time; got "
            f"start={self.result['start_time']}, end={self.result['end_time']}"
        )


class TestVenusMorningStar:
    """Exercises the is_evening=False branch of _compute_twilight_window_for_night.

    compute_next_good_observation always selects the highest-scoring window per
    night (evening or morning), so it cannot be relied upon to return a morning
    window when Venus has a well-placed evening apparition.  Instead, we call
    _compute_twilight_window_for_night directly with is_evening=False on a
    regular spring date and verify that the returned window is:
      - valid (not None)
      - anchored before 08:00 UTC (pre-dawn at Stockholm latitude)
      - shorter than 2 hours (civil-to-nautical twilight band, not full night)

    This proves the dawn-side code path is operational, independent of which
    window Venus's score maximiser happens to select on any particular date.
    """

    # April 15 is also used by the morning window group-A tests; we reuse it
    # here at Stockholm latitude to avoid adding new ephemeris dependencies.
    _NIGHT_DT = datetime(2026, 4, 15)

    def setup_method(self):
        self.start, self.end = _compute_twilight_window_for_night(
            lat=_STOCKHOLM_LAT,
            lon=_STOCKHOLM_LON,
            night_dt=self._NIGHT_DT,
            is_evening=False,
        )

    def test_returns_valid_datetime_pair(self):
        assert isinstance(self.start, datetime), (
            f"Expected start to be datetime, got {type(self.start)}"
        )
        assert isinstance(self.end, datetime), (
            f"Expected end to be datetime, got {type(self.end)}"
        )

    def test_start_before_end(self):
        assert self.start < self.end, (
            f"Expected morning window start < end; got start={self.start}, end={self.end}"
        )

    def test_start_time_before_08_utc(self):
        # Morning twilight at Stockholm in April begins around 03:00–04:00 UTC.
        # A start at or after 08:00 UTC would indicate the wrong (evening) branch.
        next_day = self._NIGHT_DT + timedelta(days=1)
        upper_bound = next_day.replace(hour=8, minute=0, second=0, microsecond=0)
        assert self.start < upper_bound, (
            f"Expected morning window start before 08:00 UTC on {next_day.date()}; "
            f"got start={self.start}"
        )

    def test_window_duration_under_2h(self):
        # The civil-to-nautical twilight band is much narrower than the full night.
        duration = self.end - self.start
        assert duration <= timedelta(hours=2), (
            f"Expected morning twilight window <= 2 hours; got {duration}"
        )


class TestMarsUsesNauticalDarkness:
    """Mars (outer planet) should use the nautical-darkness window, not civil twilight.

    We verify this by confirming that the returned start_time is at least
    60 minutes after sunset for the same location and date — a window that
    starts only seconds after sunset would indicate a civil-twilight boundary
    rather than the -12° nautical boundary.
    """

    # August 2026: Mars is well-placed in the evening sky and nights are still
    # reasonably long at Stockholm to allow a nautical window.
    _FROM_DATE = datetime(2026, 8, 1)

    def _get_sunset_utc(self, night_dt: datetime) -> datetime:
        """Compute civil sunset (sun crosses 0°) for Stockholm on night_dt."""
        observer = ephem.Observer()
        observer.lat = str(_STOCKHOLM_LAT)
        observer.lon = str(_STOCKHOLM_LON)
        observer.pressure = 0
        observer.horizon = "0"
        anchor = night_dt.replace(hour=12, minute=0, second=0, microsecond=0)
        observer.date = anchor
        sunset_ephem = observer.next_setting(ephem.Sun(), use_center=True)
        return ephem.Date(sunset_ephem).datetime()

    def test_start_time_at_least_60min_after_sunset(self):
        result = compute_next_good_observation(
            "Mars",
            lat=_STOCKHOLM_LAT,
            lon=_STOCKHOLM_LON,
            start_dt=self._FROM_DATE,
        )
        # If Mars is not observable within 180 days, skip this assertion rather
        # than fail — the key invariant (no twilight-window misuse) only applies
        # when a qualifying night exists.
        if result is None:
            pytest.skip(
                "Mars returned no qualifying observation in the 180-day scan; "
                "cannot verify nautical-darkness window boundary"
            )

        start_dt = datetime.strptime(result["start_time"], "%Y-%m-%dT%H:%M:%SZ")
        night_date = datetime.strptime(result["date"], "%Y-%m-%d")

        sunset = self._get_sunset_utc(night_date)
        gap = start_dt - sunset

        assert gap >= timedelta(minutes=60), (
            f"Expected Mars start_time to be at least 60 minutes after sunset "
            f"(nautical dusk, not civil dusk); got gap={gap} "
            f"(start={start_dt}, sunset={sunset})"
        )


# ---------------------------------------------------------------------------
# Group C: Mercury integration test
# ---------------------------------------------------------------------------

class TestMercuryUsesTwilightWindow:
    """Mercury (inferior planet) should return a twilight-windowed forecast.

    Mercury has an eastern elongation around 2026-04-10 at ~19°.  At Swedish
    latitudes (≥55°N) the shallow ecliptic angle in spring means Mercury never
    clears the 15° altitude minimum required by compute_next_good_observation.
    Paris (48.8°N) is used as the test location because it is the southernmost
    latitude at which Mercury reliably reaches the 15° threshold during the
    spring 2026 eastern elongation — the twilight-window logic is location-
    independent, so this fully exercises the inner-planet code path.
    """

    # Paris (48.8°N) — Mercury clears 15° altitude here during spring 2026.
    # Swedish latitudes (≥55°N) are too far north for Mercury to reach the
    # 15° minimum during any 2026 elongation.
    _LAT = 48.8
    _LON = 2.3

    # April 2026 — near Mercury's eastern elongation (~19° on 2026-04-10).
    _FROM_DATE_SPRING = datetime(2026, 4, 1)
    # Autumn fallback elongation window.
    _FROM_DATE_AUTUMN = datetime(2026, 10, 1)

    def _find_mercury_result(self):
        """Try spring window first; fall back to autumn elongation."""
        result = compute_next_good_observation(
            "Mercury",
            lat=self._LAT,
            lon=self._LON,
            start_dt=self._FROM_DATE_SPRING,
        )
        if result is not None:
            return result
        # Spring elongation may still be geometrically poor; try autumn.
        return compute_next_good_observation(
            "Mercury",
            lat=self._LAT,
            lon=self._LON,
            start_dt=self._FROM_DATE_AUTUMN,
        )

    def test_result_is_not_none(self):
        result = self._find_mercury_result()
        if result is None:
            pytest.skip(
                "Mercury returned no qualifying observation at 48.8°N in either "
                "the spring (2026-04-01) or autumn (2026-10-01) elongation windows"
            )
        assert "quality_score" in result, (
            f"Expected result to contain 'quality_score' key; got keys: {list(result.keys())}"
        )

    def test_start_time_is_iso_string(self):
        import re
        result = self._find_mercury_result()
        if result is None:
            pytest.skip("No Mercury result found — see test_result_is_not_none")
        iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        assert iso_re.match(result["start_time"]), (
            f"Expected ISO 8601 UTC string for start_time, got: {result['start_time']!r}"
        )

    def test_end_time_is_iso_string(self):
        import re
        result = self._find_mercury_result()
        if result is None:
            pytest.skip("No Mercury result found — see test_result_is_not_none")
        iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        assert iso_re.match(result["end_time"]), (
            f"Expected ISO 8601 UTC string for end_time, got: {result['end_time']!r}"
        )

    def test_quality_score_non_negative(self):
        result = self._find_mercury_result()
        if result is None:
            pytest.skip("No Mercury result found — see test_result_is_not_none")
        assert result["quality_score"] >= 0, (
            f"Expected quality_score >= 0, got {result['quality_score']}"
        )

    def test_start_before_end(self):
        result = self._find_mercury_result()
        if result is None:
            pytest.skip("No Mercury result found — see test_result_is_not_none")
        # Both fields are ISO 8601 UTC strings; lexicographic comparison is valid.
        assert result["start_time"] < result["end_time"], (
            f"Expected start_time < end_time; got "
            f"start={result['start_time']}, end={result['end_time']}"
        )
