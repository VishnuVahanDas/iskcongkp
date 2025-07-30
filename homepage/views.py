from django.shortcuts import render

# Create your views here.
from .models import Banner, TopHeader

def home_view(request):
    banners = Banner.objects.all().order_by('-id')
    top_headers = TopHeader.objects.all().order_by('-id')
    context = {
         "banner": banners ,
         "top_header": top_headers
         }
    return render(request, 'home.html', context)
