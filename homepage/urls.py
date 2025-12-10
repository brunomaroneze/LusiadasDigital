from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Caminho Raiz
    path('sobre/', views.sobre, name='sobre'),  # Caminho informações
    path('autor/', views.autor, name='autor'),  # Caminho Autor
]
