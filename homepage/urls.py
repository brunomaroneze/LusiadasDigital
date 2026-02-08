from django.urls import path
from . import views

urlpatterns = [
    # páginas institucionais
    path("", views.homepage, name="homepage"),
    path("sobre/", views.sobre, name="sobre"),
    path("autor/", views.autor, name="autor"),

    # canto (estado inicial)
    path("canto/<int:canto>/", views.canto, name="canto"),

    # leitura SEM paginação (continua funcionando)
    path(
        "canto/<int:canto>/leitura/<str:conteudo>/<str:coluna>/",
        views.leitura,
        name="leitura"
    ),

    # leitura COM paginação (para imagens)
    path(
        "canto/<int:canto>/leitura/<str:conteudo>/<str:coluna>/<int:pagina>/",
        views.leitura,
        name="leitura_paginada"
    ),

    # 
    #path(
    #    "canto/<int:canto>/imagem/<int:pagina>/",
    #    views.imagem,
    #    name="imagem"
    #),

]

