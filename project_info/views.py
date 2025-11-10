from django.shortcuts import render

def index(request):
    return render(request, 'project_info/index.html', {'page_title': 'Sobre o projeto'})