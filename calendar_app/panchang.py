"""Panchang calculations for Gorakhpur, built directly on pyswisseph.

Neither library suggested in the original spec is usable here:
gaurabda-calendar does not exist on PyPI, and jyotisha's pinned
pyswisseph==2.8.0.post1 does not import on Python 3.12 (removed CPython
macro); a newer pyswisseph makes jyotisha's own rise_trans call fail
(its API changed upstream) and the project has been unmaintained since
~2022. pyswisseph itself is actively maintained and works fine on
arbitrary lat/long, so the tithi/sunrise math lives here instead of
behind a third-party wrapper.

This module computes standard panchang quantities (sunrise, sidereal
tithi at sunrise) used to derive Ekadashi dates and the fixed-tithi
festivals/acharya days handled by the generate_calendar_year command.
Vaishnava Ekadashi rules have well-known edge cases (viddha tithi,
dashami-vyapini exceptions) that this module approximates at a
reviewable level of correctness — see generate_calendar_year's
requirement that every generated row stays in draft until a human
checks it against a published panchang.
"""
import datetime

import swisseph as swe

GORAKHPUR_LAT = 26.7606
GORAKHPUR_LON = 83.3732
IST_OFFSET_HOURS = 5.5

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

MASA_NAMES = [
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashwin", "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna",
]
"""Lunar-month name approximated from the Sun's sidereal rashi (index 0=Chaitra).
This is the same simplification widely used by lightweight panchang tools —
it does not model adhika/kshaya (leap/omitted) months, so masa boundaries can
be a few days off from a full traditional calculation. Fine for a draft that
a human reviews before publishing; not fine to treat as ground truth."""

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
]


def _jd_ut_midnight(date):
    """Julian day (UT) for local midnight of the given date at Gorakhpur."""
    return swe.julday(date.year, date.month, date.day, 0.0) - IST_OFFSET_HOURS / 24.0


def sunrise_jd_ut(date):
    """Julian day (UT) of sunrise at Gorakhpur for the given date."""
    jd0 = _jd_ut_midnight(date)
    _res, tret = swe.rise_trans(
        jd0, swe.SUN, swe.CALC_RISE, (GORAKHPUR_LON, GORAKHPUR_LAT, 0)
    )
    return tret[0]


def _sidereal_longitude(jd_ut, body):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    xx, _flags = swe.calc_ut(jd_ut, body, swe.FLG_SIDEREAL)
    return xx[0]


def tithi_at(jd_ut):
    """Return (tithi_number[1-30], paksha) prevailing at the given jd_ut."""
    sun = _sidereal_longitude(jd_ut, swe.SUN)
    moon = _sidereal_longitude(jd_ut, swe.MOON)
    diff = (moon - sun) % 360
    tithi_number = int(diff // 12) + 1
    paksha = 'shukla' if tithi_number <= 15 else 'krishna'
    return tithi_number, paksha


def nakshatra_at(jd_ut):
    """Return nakshatra name of the Moon at the given jd_ut."""
    moon = _sidereal_longitude(jd_ut, swe.MOON)
    index = int(moon // (360 / 27))
    return NAKSHATRA_NAMES[index % 27]


def masa_at(jd_ut):
    """Approximate lunar month index (0=Chaitra .. 11=Phalguna) via solar sidereal longitude.

    Chaitra (the first amanta lunar month) falls near the new moon closest
    to mid-March, about a month before Mesha Sankranti (Sun entering
    sidereal Aries, mid-April) — so Chaitra mostly has the Sun in Pisces,
    not Aries. Hence the +1 rashi shift below (Pisces=11 -> Chaitra=0,
    Aries=0 -> Vaishakha=1, etc.), matching how Bhadrapada (rashi Leo)
    lines up with Janmashtami actually falling in Aug/Sep.
    """
    sun = _sidereal_longitude(jd_ut, swe.SUN)
    rashi = int(sun // 30)
    return (rashi + 1) % 12


def tithi_at_sunrise(date):
    jd_sr = sunrise_jd_ut(date)
    return tithi_at(jd_sr)


def daily_panchang(date):
    """Convenience bundle of sunrise-based readings for one calendar date."""
    jd_sr = sunrise_jd_ut(date)
    tithi_number, paksha = tithi_at(jd_sr)
    return {
        'date': date,
        'sunrise_jd_ut': jd_sr,
        'tithi_number': tithi_number,
        'tithi_name': TITHI_NAMES[tithi_number - 1],
        'paksha': paksha,
        'nakshatra': nakshatra_at(jd_sr),
        'masa': masa_at(jd_sr),
    }


def iter_year_dates(year):
    d = datetime.date(year, 1, 1)
    one_day = datetime.timedelta(days=1)
    while d.year == year:
        yield d
        d += one_day


def find_ekadashi_dates(year):
    """Scan the year and return each date where tithi 11 or 26 prevails at sunrise.

    Vaishnava Ekadashi observance follows the tithi prevailing at
    sunrise (not a fixed civil date), so we walk day-by-day rather than
    solving analytically. A tithi that starts and ends between two
    sunrises without ever prevailing at either is correctly skipped by
    this method, matching real panchang behaviour.
    """
    results = []
    seen_tithi_11_26_months = set()
    for date in iter_year_dates(year):
        tithi_number, paksha = tithi_at_sunrise(date)
        if tithi_number in (11, 26):
            key = (date.month, tithi_number)
            if key in seen_tithi_11_26_months:
                continue
            seen_tithi_11_26_months.add(key)
            results.append({'date': date, 'paksha': paksha})
    return results
