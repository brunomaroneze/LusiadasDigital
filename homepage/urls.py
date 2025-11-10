# homepage/urls.py

from django.urls import path
from . import views

app_name = 'homepage' # É uma boa prática definir um namespace para apps

urlpatterns = [
    path('', views.index, name='index'), # 'name' é o nome da URL que você usará nos templates
]