from .models import Canto, PaginaImagem, PaginaTexto
from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from .utils.tei import tei_para_html

# -----------------------
# PÁGINAS
# -----------------------

def homepage(request):
    return render(request, "homepage.html")


def sobre(request):
    return render(request, "sobre.html")


def autor(request):
    return render(request, "autor.html")


# -----------------------
# CANTO
# -----------------------


def canto(request, canto):
    pagina_num = int(request.GET.get("p", 1))

    paginas = PaginaImagem.objects.filter(
        canto__numero=canto
    ).order_by("numero")

    pagina = paginas.filter(numero=pagina_num).first()

    contexto = {
        "canto": canto,
        "esq": "modernizado",
        "dir": "original",
        "pagina": pagina,          # objeto
        "pagina_num": pagina_num,  # número
        "paginas": paginas,
    }

    return render(request, "poema/canto.html", contexto)


# -----------------------
# Página inicial de CANTO
# -----------------------
def canto_index(request, canto):
    paginas = PaginaImagem.objects.filter(
        canto__numero=canto
    ).order_by("numero")

    return render(request, "poema/canto_index.html", {
        "canto": canto,
        "paginas": paginas
    })



# -----------------------
# LEITURA
# -----------------------

def leitura(request, canto, conteudo, coluna, pagina=None):
    print("ENTROU NA LEITURA")
    esq = "modernizado"
    dir = "original"

    if coluna == "esq":
        esq = conteudo
    elif coluna == "dir":
        dir = conteudo

    pagina_num = int(request.GET.get("p", 1))

    imagem = PaginaImagem.objects.filter(
        canto__numero=canto,
        numero=pagina_num
    ).first()

    texto_esq = PaginaTexto.objects.filter(
        canto__numero=canto,
        numero=pagina_num,
        versao=esq
    ).first()

    texto_dir = PaginaTexto.objects.filter(
        canto__numero=canto,
        numero=pagina_num,
        versao=dir
    ).first()

    html_esq = tei_para_html(texto_esq.tei_xml) if texto_esq else ""
    html_dir = tei_para_html(texto_dir.tei_xml) if texto_dir else ""

    paginas = PaginaImagem.objects.filter(
        canto__numero=canto
    ).order_by("numero")

    contexto = {
        "canto": canto,
        "pagina_num": pagina_num,
        "imagem": imagem,
        "paginas": paginas,
        "esq": esq,
        "dir": dir,
        "html_esq": html_esq,
        "html_dir": html_dir,
    }

    return render(request, "poema/canto.html", contexto)


