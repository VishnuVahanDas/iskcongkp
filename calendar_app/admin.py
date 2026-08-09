from dateutil.relativedelta import relativedelta
from django.contrib import admin

from .models import CalendarEvent, PublishLog, TempleEvent


def _log_publish(model_name, obj, actor):
    PublishLog.objects.create(
        model_name=model_name,
        object_id=obj.pk,
        title=obj.title,
        actor=actor,
        action='published',
    )


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'event_type', 'is_major_festival', 'status')
    list_editable = ('status',)
    list_filter = ('event_type', 'status', 'is_major_festival')
    search_fields = ('title',)
    date_hierarchy = 'date'
    actions = ['mark_as_published', 'duplicate_to_next_year']

    def save_model(self, request, obj, form, change):
        was_published = False
        if change:
            was_published = (
                CalendarEvent.objects.filter(pk=obj.pk).values_list('status', flat=True).first()
                == 'published'
            )
        super().save_model(request, obj, form, change)
        if obj.status == 'published' and not was_published:
            _log_publish('CalendarEvent', obj, request.user)

    @admin.action(description='Mark selected as Published')
    def mark_as_published(self, request, queryset):
        for obj in queryset.exclude(status='published'):
            obj.status = 'published'
            obj.save(update_fields=['status'])
            _log_publish('CalendarEvent', obj, request.user)

    @admin.action(description='Duplicate to next year (draft)')
    def duplicate_to_next_year(self, request, queryset):
        created = 0
        for obj in queryset:
            next_date = obj.date + relativedelta(years=1)
            if CalendarEvent.objects.filter(
                date=next_date, event_type=obj.event_type, title=obj.title
            ).exists():
                continue
            CalendarEvent.objects.create(
                date=next_date,
                gregorian_year=next_date.year,
                event_type=obj.event_type,
                title=obj.title,
                description=obj.description,
                fasting_till=obj.fasting_till,
                is_major_festival=obj.is_major_festival,
                location=obj.location,
                status='draft',
            )
            created += 1
        self.message_user(request, f"Created {created} draft row(s) for next year.")


@admin.register(TempleEvent)
class TempleEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_date', 'event_time', 'is_recurring', 'status')
    list_editable = ('status',)
    list_filter = ('status', 'is_recurring')
    search_fields = ('title',)
    date_hierarchy = 'event_date'
    actions = ['mark_as_published']

    def save_model(self, request, obj, form, change):
        was_published = False
        if change:
            was_published = (
                TempleEvent.objects.filter(pk=obj.pk).values_list('status', flat=True).first()
                == 'published'
            )
        super().save_model(request, obj, form, change)
        if obj.status == 'published' and not was_published:
            _log_publish('TempleEvent', obj, request.user)

    @admin.action(description='Mark selected as Published')
    def mark_as_published(self, request, queryset):
        for obj in queryset.exclude(status='published'):
            obj.status = 'published'
            obj.save(update_fields=['status'])
            _log_publish('TempleEvent', obj, request.user)


@admin.register(PublishLog)
class PublishLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'model_name', 'title', 'action', 'actor')
    list_filter = ('model_name', 'action')
    search_fields = ('title',)
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
