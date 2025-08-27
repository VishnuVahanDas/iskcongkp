from django.shortcuts import render

def contact_view(request):
    return render(request, 'contact.html')

def terms_view(request):
    return render(request, 'terms.html')

def privacy_view(request):
    return render(request, 'privacy.html')

def maintenance_view(request):
    return render(request, 'maintenance.html')

def error_404_view(request, exception):
    # we add the path to the 404.html file
    # here. The name of our HTML file is 404.html
    return render(request, '404.html', status=404)

def launch(request):
    return render(request, 'launch.html')
