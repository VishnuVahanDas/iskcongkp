from django.conf import settings
from django.db import models


class CalendarEvent(models.Model):
    EVENT_TYPES = [
        ('ekadashi', 'Ekadashi'),
        ('appearance', 'Appearance Day'),
        ('disappearance', 'Disappearance Day'),
        ('festival', 'Festival'),
    ]
    STATUS = [('draft', 'Draft'), ('published', 'Published')]

    date = models.DateField()
    gregorian_year = models.IntegerField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    fasting_till = models.CharField(max_length=100, blank=True)
    is_major_festival = models.BooleanField(default=False)
    location = models.CharField(max_length=100, default='Gorakhpur')
    status = models.CharField(max_length=10, choices=STATUS, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']
        indexes = [models.Index(fields=['date', 'event_type', 'status'])]
        constraints = [
            models.UniqueConstraint(
                fields=['date', 'event_type', 'title'],
                name='unique_calendar_event_date_type_title',
            )
        ]

    def __str__(self):
        return f"{self.date} — {self.title}"


class TempleEvent(models.Model):
    STATUS = [('draft', 'Draft'), ('published', 'Published')]

    title = models.CharField(max_length=200)
    event_date = models.DateField()
    event_time = models.TimeField(blank=True, null=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    is_recurring = models.BooleanField(default=False)
    recurrence_note = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='draft')

    class Meta:
        ordering = ['event_date']

    def __str__(self):
        return f"{self.event_date} — {self.title}"


class PublishLog(models.Model):
    """Audit trail for draft->published transitions in admin.

    Devotees rely on these dates for fasting, so every publish action
    needs a who/when record independent of Django's built-in LogEntry
    (which does not fire for list_editable inline saves).
    """

    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=50, default='published')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action}: {self.model_name}#{self.object_id} by {self.actor}"
