from django.urls import path
from . import views

urlpatterns = [
    # páginas institucionais
    path("", views.homepage, name="homepage"),
    path("sobre/", views.sobre, name="sobre"),
    path("autor/", views.autor, name="autor"),
    path("canto/<int:canto>/index/", views.canto_index, name="canto_index"),

    # leitura COM paginação (mais específico)
    path(
        "canto/<int:canto>/leitura/<str:conteudo>/<str:coluna>/<int:pagina>/",
        views.leitura,
        name="leitura_paginada"
    ),

    # leitura SEM paginação
    path(
        "canto/<int:canto>/leitura/<str:conteudo>/<str:coluna>/",
        views.leitura,
        name="leitura"
    ),

    # índice do canto (miniaturas)
    path("canto/<int:canto>/index/", views.canto_index, name="canto_index"),

    # canto (genérico — DEIXAR POR ÚLTIMO)
    path("canto/<int:canto>/", views.canto, name="canto"),
]
