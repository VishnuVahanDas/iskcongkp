from django.shortcuts import render

# Create your views here.
from .models import Banner, TopHeader, NewsPopup


def home_view(request):
    banners = Banner.objects.all().order_by('-id')
    top_headers = TopHeader.objects.all().order_by('-id')
    news_popup = NewsPopup.objects.filter(active=True).order_by('-id').first()
    context = {
        "banner": banners,
        "top_header": top_headers,
        "news_popup": news_popup,
    }
    return render(request, 'home.html', context)
