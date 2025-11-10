# author/urls.py

from django.urls import path
from . import views

app_name = 'author'

urlpatterns = [
    path('', views.index, name='index'), # Exemplo futuro
]