from django.urls import path
from . import views

urlpatterns = [
    # páginas institucionais
    path("", views.homepage, name="homepage"),
    path("sobre/", views.sobre, name="sobre"),
    path("autor/", views.autor, name="autor"),
    path("pretextuais/", views.pretextuais, name="pretextuais"),
    path("canto/<int:canto>/index/", views.canto_index, name="canto_index"),

    # DEBUG — índice estrofe→página, ainda não usado por nenhuma página
    # (rota temporária de verificação, ver views.indice_estrofes_view)
    path("canto/<int:canto>/estrofes/", views.indice_estrofes_view, name="indice_estrofes_debug"),

    # lista de cantos cadastrados — usada pela aba lateral de navegação
    path("cantos/", views.listar_cantos_view, name="listar_cantos"),

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

    # canto (genérico — DEIXAR POR ÚLTIMO)
    path("canto/<int:canto>/", views.canto, name="canto"),
]
