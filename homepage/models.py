from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "gif"]
MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_image_file_size(file):
    if file.size > MAX_IMAGE_UPLOAD_BYTES:
        raise ValidationError(f"Image file too large — max size is {MAX_IMAGE_UPLOAD_BYTES // (1024 * 1024)}MB.")


class Banner(models.Model):
    image = models.ImageField(
        upload_to="homepage",
        validators=[FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS), validate_image_file_size],
    )
    alt = models.CharField(max_length=255)

    def __str__(self):
        return self.alt


class TopHeader(models.Model):
    image = models.ImageField(
        upload_to="homepage",
        validators=[FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS), validate_image_file_size],
    )
    alt = models.CharField(max_length=255)

    def __str__(self):
        return self.alt


class NewsPopup(models.Model):
    image = models.ImageField(
        upload_to="homepage/news",
        validators=[FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS), validate_image_file_size],
    )
    alt = models.CharField(max_length=255, blank=True)
    link_url = models.URLField(blank=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.alt or f"NewsPopup {self.pk}"

