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
    numero = models.PositiveIntegerField()
    imagem = models.ImageField(upload_to="poema/")

    class Meta:
        verbose_name = "Página de imagem"
        verbose_name_plural = "Páginas de imagens"
        ordering = ["numero"]
        unique_together = ("canto", "numero")

    def __str__(self):
        return f"Canto {self.canto.numero} – pág. {self.numero}"


## TEXTO
class PaginaTexto(models.Model):
    VERSOES = [
        ("original", "Original"),
        ("modernizado", "Modernizado"),
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



