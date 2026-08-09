# Vaishnava Calendar + Events (`calendar_app`)

Powers the "Vaishnava Calendar" nav dropdown (Prominent Festivals, Ekadashi,
Appearance Day, Disappearance Day, View all Festivals) and the "Events" nav
item. Fully separate from the existing `festivals` app and from all
payment/donation code — new models, views, URLs only.

## Library used, and why

The original spec suggested `gaurabda-calendar` or `jyotisha`. Neither works
on this project's Python 3.12 environment:

- `gaurabda-calendar` does not exist on PyPI.
- `jyotisha==0.1.9` pins `pyswisseph==2.8.0.post1`, which fails to import on
  Python 3.12 (it uses a CPython macro removed in that version). Forcing a
  newer `pyswisseph` lets it import, but then jyotisha's own calls into the
  Swiss Ephemeris API break, because that API changed upstream and jyotisha
  hasn't been updated since ~2022.

Instead, `calendar_app/panchang.py` computes sunrise and sidereal tithi
directly on **`pyswisseph`** (the actively-maintained Swiss Ephemeris
binding both of the above libraries wrap anyway), for Gorakhpur's fixed
coordinates (26.7606° N, 83.3732° E). This was validated against known
values before building on it (see `panchang.find_ekadashi_dates`).

**Important caveat:** `panchang.py` uses a simplified solar-rashi
approximation for identifying the lunar month (masa) of each date — it does
not implement full adhika/kshaya (leap/omitted) month handling. This is
exactly why `generate_calendar_year` never auto-publishes: every generated
date must be checked by a human against an authoritative published
Vaishnava panchang before going live. A wrong Ekadashi date is a real
problem for devotees' fasting — this workflow is designed around that.

Installing `pyswisseph` requires building from source on this environment
(`pip install --no-binary=pyswisseph pyswisseph==2.10.3.2`) — the prebuilt
wheel available for some platforms is incompatible with Python 3.12. It's
already pinned in `requirements.txt`.

## Running the yearly generation command

```
python manage.py generate_calendar_year 2027
```

This:
- Computes all Ekadashi dates (tithi 11/26 prevailing at sunrise) for the year.
- Computes the standard major festivals (Janmashtami, Gaura Purnima, Ratha
  Yatra, Radhashtami, Nrsimha Chaturdashi, Rama Navami, Govardhan Puja,
  Diwali, Guru Purnima, Nityananda Trayodashi) and acharya appearance/
  disappearance days (Srila Prabhupada, Bhaktisiddhanta Saraswati Thakura,
  Bhaktivinoda Thakura, Gaura Kishora Das Babaji).
- Skips (and prints a warning for) anything already present with the same
  `date` + `event_type` + `title` — it never overwrites or deletes existing
  rows, published or draft.
- Writes everything else as `CalendarEvent(status="draft")`.
- Prints a summary table (`date | type | title | major Y/N`) and never
  publishes anything itself.

## Where to review and publish

Django Admin → **Calendar Events** (or **Temple Events**):

1. Filter `status = Draft`.
2. Check each generated date/title against your temple's published
   Gaudiya Vaishnava panchang for that year (this is the manual step that
   makes the dates trustworthy — don't skip it).
3. Fix any wrong dates/titles/`fasting_till` text directly in the row.
4. Select the verified rows and run the **"Mark as Published"** admin
   action (or edit `status` inline in the changelist — both are logged).
5. Every publish is recorded in **Publish Logs** (who, when, which record) —
   read-only in admin, for audit purposes.

If a future year's generation command isn't run in time, the **"Duplicate
to next year"** admin action on `CalendarEvent` copies a selected row
forward by exactly one year as a new draft, as a manual fallback.

## Routes

| URL | Name | Purpose |
|---|---|---|
| `/calendar/` | `calendar_app:vaishnava_calendar` | Landing page, all published events, `?type=` / `?major=true` filters |
| `/calendar/ekadashi/` | `calendar_app:ekadashi_list` | Ekadashi only |
| `/calendar/appearance-days/` | `calendar_app:appearance_days` | Appearance days only |
| `/calendar/disappearance-days/` | `calendar_app:disappearance_days` | Disappearance days only |
| `/calendar/festivals/` | `calendar_app:festivals` | Major festivals; `?upcoming=true` for the short homepage-teaser mode ("Prominent Festivals"), no param for the full paginated list ("View all Festivals") |
| `/events/` | `calendar_app:temple_events` | Temple-managed program listings (`TempleEvent`) |
| `/api/calendar/<year>/` | `calendar_app:calendar_api` | JSON of published `CalendarEvent` rows for that year |
