from django.shortcuts import render

# Create your views here.
def shastra_daan(request):
    return render(request, 'donation/shastra-daan.html')

def temple_seva(request):
    return render(request, 'donation/temple-seva.html')

def annadana_seva(request):
    return render(request, 'donation/annadaan.html')

def nitya_seva(request):
    return render(request, 'donation/nitya-seva.html')

def janmashtami_seva(request):
    return render(request, 'donation/janmashtami.html')

def tula_daan(request):
    return render(request, 'donation/tula-daan.html')

def donate_brick(request):
    return render(request, 'donation/donate-brick.html')