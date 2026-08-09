"""Generate a draft CalendarEvent batch for one year from computed panchang data.

Usage: python manage.py generate_calendar_year 2027

Never auto-publishes. Never touches existing rows (published or draft) —
duplicates are detected on (date, event_type, title) and skipped with a
warning. See calendar_app/README.md for the manual review workflow.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from calendar_app.models import CalendarEvent
from calendar_app import panchang

# Fixed-tithi festivals, keyed by (masa index into panchang.MASA_NAMES, tithi_number 1-30).
# tithi_number follows panchang.tithi_at(): 1-15 = shukla paksha, 16-30 = krishna paksha
# (tithi_number 15+N = krishna paksha tithi N, e.g. 23 = Krishna Ashtami, 30 = Amavasya).
#
# These associations are the standard ones published on Gaudiya Vaishnava
# calendars, but masa identification here uses the simplified solar-rashi
# approximation in panchang.MASA_NAMES (no adhika/kshaya month handling).
# ALWAYS verify each generated date against an authoritative published
# panchang before publishing — this table is a starting point, not ground truth.
FESTIVALS = [
    {'masa': 5, 'tithi': 23, 'title': 'Sri Krishna Janmashtami', 'is_major_festival': True,
     'fasting_till': 'till midnight (parana next day)'},
    {'masa': 5, 'tithi': 8, 'title': 'Sri Radhashtami', 'is_major_festival': True},
    {'masa': 11, 'tithi': 15, 'title': 'Sri Gaura Purnima', 'is_major_festival': True},
    {'masa': 3, 'tithi': 2, 'title': 'Sri Ratha Yatra', 'is_major_festival': True},
    {'masa': 1, 'tithi': 14, 'title': 'Sri Nrsimha Chaturdashi', 'is_major_festival': True,
     'fasting_till': 'till evening (parana after Nrsimha puja)'},
    {'masa': 0, 'tithi': 9, 'title': 'Sri Rama Navami', 'is_major_festival': True},
    {'masa': 3, 'tithi': 15, 'title': 'Guru Purnima', 'is_major_festival': False},
    {'masa': 7, 'tithi': 1, 'title': 'Sri Govardhan Puja', 'is_major_festival': True},
    {'masa': 7, 'tithi': 30, 'title': 'Sri Diwali / Dipavali', 'is_major_festival': True},
    {'masa': 10, 'tithi': 13, 'title': 'Sri Nityananda Trayodashi', 'is_major_festival': False},
]

# Acharya appearance/disappearance days — same masa/tithi caveat as FESTIVALS above.
ACHARYA_DAYS = [
    {'masa': 1, 'tithi': 24, 'title': 'Srila Prabhupada Appearance Day', 'event_type': 'appearance'},
    {'masa': 7, 'tithi': 2, 'title': 'Srila Prabhupada Disappearance Day', 'event_type': 'disappearance',
     'fasting_till': 'till noon'},
    {'masa': 10, 'tithi': 22, 'title': 'Srila Bhaktisiddhanta Saraswati Thakura Appearance Day', 'event_type': 'appearance'},
    {'masa': 10, 'tithi': 27, 'title': 'Srila Bhaktisiddhanta Saraswati Thakura Disappearance Day', 'event_type': 'disappearance',
     'fasting_till': 'till noon'},
    {'masa': 10, 'tithi': 5, 'title': 'Srila Bhaktivinoda Thakura Appearance Day', 'event_type': 'appearance'},
    {'masa': 10, 'tithi': 21, 'title': 'Srila Gaura Kishora Das Babaji Disappearance Day', 'event_type': 'disappearance',
     'fasting_till': 'till noon'},
]


class Command(BaseCommand):
    help = "Generate draft CalendarEvent rows (Ekadashi/festivals/acharya days) for a year."

    def add_arguments(self, parser):
        parser.add_argument('year', type=int)

    def handle(self, *args, **options):
        year = options['year']
        if year < 2000 or year > 2100:
            raise CommandError("year looks out of range — pass a 4-digit Gregorian year")

        rows = []
        rows.extend(self._build_ekadashi_rows(year))
        rows.extend(self._build_masa_tithi_rows(year, FESTIVALS, default_event_type='festival'))
        rows.extend(self._build_masa_tithi_rows(year, ACHARYA_DAYS, default_event_type=None))

        created, skipped = self._write_rows(rows)
        self._print_summary(created, skipped)

    def _build_ekadashi_rows(self, year):
        rows = []
        for occ in panchang.find_ekadashi_dates(year):
            rows.append({
                'date': occ['date'],
                'event_type': 'ekadashi',
                'title': f"{occ['paksha'].capitalize()} Paksha Ekadashi",
                'fasting_till': 'till sunrise next day (break fast during parana window)',
                'is_major_festival': False,
            })
        return rows

    def _build_masa_tithi_rows(self, year, table, default_event_type):
        # One occurrence per year per named festival/acharya day: in an
        # adhika (leap) lunar month year, the same masa+tithi combination
        # can genuinely recur ~29-30 days apart (e.g. an extra Ashadha),
        # which would otherwise duplicate an annual festival like Ratha
        # Yatra. First match in the year wins; the human review step is
        # where a real adhika-masa correction (observe in nija, not
        # adhika, month) gets applied if it matters for a given year.
        found_titles = set()
        rows = []
        for date in panchang.iter_year_dates(year):
            reading = panchang.daily_panchang(date)
            key = (reading['masa'], reading['tithi_number'])
            for entry in table:
                if (entry['masa'], entry['tithi']) != key:
                    continue
                if entry['title'] in found_titles:
                    continue
                found_titles.add(entry['title'])
                rows.append({
                    'date': date,
                    'event_type': entry.get('event_type', default_event_type),
                    'title': entry['title'],
                    'fasting_till': entry.get('fasting_till', ''),
                    'is_major_festival': entry.get('is_major_festival', False),
                })
        return rows

    def _write_rows(self, rows):
        created, skipped = [], []
        for row in rows:
            exists = CalendarEvent.objects.filter(
                date=row['date'], event_type=row['event_type'], title=row['title']
            ).exists()
            if exists:
                skipped.append(row)
                continue
            try:
                obj = CalendarEvent.objects.create(
                    date=row['date'],
                    gregorian_year=row['date'].year,
                    event_type=row['event_type'],
                    title=row['title'],
                    fasting_till=row.get('fasting_till', ''),
                    is_major_festival=row.get('is_major_festival', False),
                    status='draft',
                )
                created.append(obj)
            except IntegrityError:
                skipped.append(row)
        return created, skipped

    def _print_summary(self, created, skipped):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f"Created {len(created)} draft event(s):"))
        self.stdout.write(f"{'date':<12} {'type':<16} {'title':<45} major")
        self.stdout.write('-' * 80)
        for obj in sorted(created, key=lambda o: o.date):
            major = 'Y' if obj.is_major_festival else 'N'
            self.stdout.write(f"{str(obj.date):<12} {obj.event_type:<16} {obj.title:<45} {major}")

        if skipped:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                f"Skipped {len(skipped)} row(s) already present (same date + event_type + title):"
            ))
            for row in skipped:
                self.stdout.write(f"  {row['date']} — {row['title']}")

        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            "Nothing was published. Review these drafts in Admin -> Calendar Events "
            "against an authoritative panchang before using 'Mark as Published'."
        ))
