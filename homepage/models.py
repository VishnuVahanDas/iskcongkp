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

