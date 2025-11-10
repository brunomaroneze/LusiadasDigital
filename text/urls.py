# text/urls.py

from django.urls import path
from . import views

app_name = 'text'

urlpatterns = [
    # 1. Página inicial do app 'text' - pode listar todos os cantos
    path('', views.canto_list, name='canto_list'), # Ex: /texto/

    # 2. Página para visualizar um canto específico
    # <int:canto_numero> é um "path converter" que captura um inteiro da URL.
    # Ex: /texto/canto/1/
    path('canto/<int:canto_numero>/', views.canto_detail, name='canto_detail'),

    # 3. (Opcional, para mais tarde) Página para visualizar uma estrofe específica dentro de um canto
    # Ex: /texto/canto/1/estrofe/10/
    # path('canto/<int:canto_numero>/estrofe/<int:estrofe_numero>/', views.estrofe_detail, name='estrofe_detail'),

    # 4. (Opcional, para mais tarde) Página de busca de texto
    # path('search/', views.search_text, name='search_text'),
]