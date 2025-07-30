from django.shortcuts import render

# Create your views here.
def sunday_feast(request):
    return render(request, 'services/sunday-feast.html')

def life_member(request):
    return render(request, 'services/life-membership.html')

def harinam(request):
    return render(request, 'services/harinam-sankirtan.html')

def iyf(request):
    return render(request, 'services/iyf.html')

def krsna_school(request):
    return render(request, 'services/krishna-fun-school.html')

def courses(request):
    return render(request, 'services/courses.html')

def siksha(request):
    return render(request, 'services/siksha.html')

def food_for_life(request):
    return render(request, 'services/food-for-life.html')
