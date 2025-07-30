from django.shortcuts import render

# Create your views here.
def about(request):
    return render(request, 'who-we-are/about-us.html')

def our_mission(request):
    return render(request, 'who-we-are/our-mission.html')

def founder_acharya(request):
    return render(request, 'who-we-are/founder-acharya.html')

def history(request):
    return render(request, 'who-we-are/history.html')

def philosophy(request):
    return render(request, 'who-we-are/philosophy.html')

def harekrsna_movement(request):
    return render(request, 'who-we-are/harekrsna-movement.html')

def temple_schedule(request):
    return render(request, 'who-we-are/temple-schedule.html')

def resources(request):
    return render(request, 'who-we-are/resources.html')

