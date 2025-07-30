from django.db import models

class banner(models.Model):
    image = models.ImageField(upload_to="homepage")
    alt = models.CharField(max_length=255)

    def __str__(self):
        return self.alt


class top_header(models.Model):
    image = models.ImageField(upload_to="homepage")
    alt = models.CharField(max_length=255)

    def __str__(self):
        return self.alt