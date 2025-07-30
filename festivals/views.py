from django.shortcuts import render

# Create your views here.
def calender(request):
    return render(request, 'festivals/calender.html')

def festivals(request):
    return render(request, 'festivals/pro-festivals.html')