# -----------------------
# IMAGENS FUTURAMENTE (IGNORAR POR ENQUANTO 27-01-2026)
# -----------------------

from django.conf import settings
import os

def imagens_canto(request, canto):
    pasta = os.path.join(
        settings.MEDIA_ROOT,
        "poema",
        f"canto_{canto}"
    )

    arquivos = sorted(os.listdir(pasta))

    paginas = []
    for f in arquivos:
        paginas.append({
            "numero": f.replace(".jpg", ""),
            "url": f"/media/poema/canto_{canto}/{f}"
        })

    return render(request, "poema/imagem_grid.html", {
        "canto": canto,
        "paginas": paginas
    })
