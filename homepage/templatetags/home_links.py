from django import template
from django.urls import reverse


register = template.Library()


@register.simple_tag(takes_context=True)
def home_anchor(context, anchor):
    request = context.get("request")
    anchor_name = str(anchor).lstrip("#")
    prefix = "" if request and request.path == "/" else reverse("home")
    return f"{prefix}#{anchor_name}"
