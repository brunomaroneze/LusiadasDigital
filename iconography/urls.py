# iconography/urls.py

from django.urls import path
from . import views

app_name = 'iconography' # O namespace ainda é útil

urlpatterns = [
    path('', views.index, name='index'), # Exemplo futuro
]