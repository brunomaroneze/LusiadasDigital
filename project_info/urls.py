# project_info/urls.py

from django.urls import path
from . import views

app_name = 'project_info'

urlpatterns = [
    path('', views.index, name='index'), # Exemplo futuro
]