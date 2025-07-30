from django.shortcuts import render

# Create your views here.
from .models import banner, top_header

def home_view(request):
    banners = banner.objects.all().order_by('-id')
    top_headers = top_header.objects.all().order_by('-id')
    context = {
         "banner": banners ,
         "top_header": top_headers
         }
    return render(request, 'home.html', context)
