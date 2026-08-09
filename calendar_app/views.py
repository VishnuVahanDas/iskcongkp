import datetime

from django.http import JsonResponse
from django.views.generic import ListView

from .models import CalendarEvent, TempleEvent

PAST_PAGE_SIZE = 20
FESTIVAL_TEASER_LIMIT = 5


class PublishedListMixin:
    """Shared upcoming/past split for all published-CalendarEvent list pages."""

    model = CalendarEvent
    paginate_by = None  # past-list pagination handled manually in context

    def get_base_queryset(self):
        return CalendarEvent.objects.filter(status='published')

    def get_queryset(self):
        return self.get_base_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()
        queryset = self.get_queryset()
        upcoming = list(queryset.filter(date__gte=today).order_by('date'))
        past_qs = queryset.filter(date__lt=today).order_by('-date')

        past_page = self.request.GET.get('past_page', 1)
        try:
            past_page = max(int(past_page), 1)
        except (TypeError, ValueError):
            past_page = 1
        start = (past_page - 1) * PAST_PAGE_SIZE
        past_slice = list(past_qs[start:start + PAST_PAGE_SIZE])
        has_more_past = past_qs.count() > start + PAST_PAGE_SIZE

        context.update({
            'upcoming_events': upcoming,
            'past_events': past_slice,
            'past_page': past_page,
            'has_more_past': has_more_past,
            'heading': self.heading,
        })
        return context


class CalendarListView(PublishedListMixin, ListView):
    template_name = 'calendar_app/month_view.html'
    heading = 'Vaishnava Calendar'

    def get_queryset(self):
        queryset = self.get_base_queryset()
        event_type = self.request.GET.get('type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if self.request.GET.get('major') == 'true':
            queryset = queryset.filter(is_major_festival=True)
        return queryset


class EkadashiListView(PublishedListMixin, ListView):
    template_name = 'calendar_app/list.html'
    heading = 'Ekadashi'

    def get_queryset(self):
        return self.get_base_queryset().filter(event_type='ekadashi')


class AppearanceDayListView(PublishedListMixin, ListView):
    template_name = 'calendar_app/list.html'
    heading = 'Appearance Day'

    def get_queryset(self):
        return self.get_base_queryset().filter(event_type='appearance')


class DisappearanceDayListView(PublishedListMixin, ListView):
    template_name = 'calendar_app/list.html'
    heading = 'Disappearance Day'

    def get_queryset(self):
        return self.get_base_queryset().filter(event_type='disappearance')


class FestivalListView(PublishedListMixin, ListView):
    """Serves both 'Prominent Festivals' (?upcoming=true, short teaser) and
    'View all Festivals' (full, paginated) nav items from one view/queryset,
    per the nav-clarification: same filter, different display density."""

    template_name = 'calendar_app/list.html'
    heading = 'Festivals'

    def get_queryset(self):
        return self.get_base_queryset().filter(is_major_festival=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET.get('upcoming') == 'true':
            try:
                limit = int(self.request.GET.get('limit', FESTIVAL_TEASER_LIMIT))
            except (TypeError, ValueError):
                limit = FESTIVAL_TEASER_LIMIT
            context['upcoming_events'] = context['upcoming_events'][:limit]
            context['past_events'] = []
            context['has_more_past'] = False
            context['teaser_mode'] = True
        return context


class TempleEventListView(ListView):
    model = TempleEvent
    template_name = 'calendar_app/events_list.html'
    heading = 'Events'

    def get_queryset(self):
        return TempleEvent.objects.filter(status='published')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()
        queryset = self.get_queryset()
        context['upcoming_events'] = queryset.filter(event_date__gte=today).order_by('event_date')
        context['past_events'] = queryset.filter(event_date__lt=today).order_by('-event_date')
        context['heading'] = self.heading
        return context


def upcoming_widget_items(limit=3):
    """Nearest published Ekadashi + TempleEvent entries, merged and sorted by date.

    Used by the homepage's 'Upcoming Events' widget.
    """
    today = datetime.date.today()
    ekadashis = CalendarEvent.objects.filter(
        status='published', event_type='ekadashi', date__gte=today
    ).order_by('date')[:limit]
    temple_events = TempleEvent.objects.filter(
        status='published', event_date__gte=today
    ).order_by('event_date')[:limit]

    items = [
        {'kind': 'Ekadashi', 'title': event.title, 'date': event.date}
        for event in ekadashis
    ] + [
        {'kind': 'Event', 'title': event.title, 'date': event.event_date}
        for event in temple_events
    ]
    items.sort(key=lambda item: item['date'])
    return items[:limit]


def calendar_api_json(request, year):
    events = CalendarEvent.objects.filter(status='published', gregorian_year=year).order_by('date')
    data = [
        {
            'date': event.date.isoformat(),
            'event_type': event.event_type,
            'title': event.title,
            'description': event.description,
            'fasting_till': event.fasting_till,
            'is_major_festival': event.is_major_festival,
            'location': event.location,
        }
        for event in events
    ]
    return JsonResponse({'year': year, 'count': len(data), 'events': data})
