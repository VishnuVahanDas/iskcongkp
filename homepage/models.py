from django.db import models

class Banner(models.Model):
    image = models.ImageField(upload_to="homepage")
    alt = models.CharField(max_length=255)

    def __str__(self):
        return self.alt


class TopHeader(models.Model):
    image = models.ImageField(upload_to="homepage")
    alt = models.CharField(max_length=255)

    def __str__(self):
        return self.alt


class NewsPopup(models.Model):
    image = models.ImageField(upload_to="homepage/news")
    alt = models.CharField(max_length=255, blank=True)
    link_url = models.URLField(blank=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.alt or f"NewsPopup {self.pk}"

