# iconography/views.py
from django.shortcuts import render

def index(request):
    return render(request, 'iconography/index.html', {'page_title': 'Iconografia'})