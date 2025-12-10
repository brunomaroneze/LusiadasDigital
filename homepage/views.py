from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader


def home(request):
    return render(request, 'homepage.html')


def autor(request):
    return render(request, 'autor.html')


def sobre(request):
    return render(request, 'sobre.html')
