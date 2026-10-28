from django.db import models

## CANTO

class Canto(models.Model):
    numero = models.PositiveIntegerField(unique=True)
    titulo = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Canto {self.numero}"


## IMAGEM
class PaginaImagem(models.Model):
    canto = models.ForeignKey(
        Canto,
        on_delete=models.CASCADE,
        related_name="paginas"
    )
    EDICOES = [
        ("A", "Imagem A"),
        ("B", "Imagem B"),
    ]

    numero = models.PositiveIntegerField()
    edicao = models.CharField(
        max_length=1,
        choices=EDICOES,
        default="A",
        help_text="A ou B: de qual das duas edições é este fac-símile",
    )
    imagem = models.ImageField(upload_to="poema/")

    class Meta:
        verbose_name = "Página de imagem"
        verbose_name_plural = "Páginas de imagens"
        ordering = ["numero", "edicao"]
        unique_together = ("canto", "numero", "edicao")

    def __str__(self):
        return f"Canto {self.canto.numero} – pág. {self.numero} (imagem {self.edicao})"


## TEXTO
class PaginaTexto(models.Model):
    VERSOES = [
        ("modernizado", "Versão modernizada"),
        ("original_a", "Versão original A"),
        ("original_b", "Versão original B"),
        # legado (não aparece nas abas de leitura)
        ("original", "Original (legado)"),
    ]

    canto = models.ForeignKey(
        Canto,
        on_delete=models.CASCADE,
        related_name="textos"
    )
    numero = models.PositiveIntegerField()
    versao = models.CharField(
        max_length=20,
        choices=VERSOES
    )
    tei_xml = models.TextField(
        help_text="Cole aqui o TEI-XML"
    )

    class Meta:
        unique_together = ("canto", "numero", "versao")
        ordering = ["numero"]

    def __str__(self):
        return f"Canto {self.canto.numero} – pág. {self.numero} ({self.versao})"



