from django.shortcuts import render

def index(request):
    return render(request, 'author/index.html', {'page_title': 'Sobre o autor'})