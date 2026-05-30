from django.contrib import admin
from .models import Canto, PaginaImagem, PaginaTexto

class PaginaImagemInline(admin.TabularInline):
    model = PaginaImagem
    extra = 1


@admin.register(Canto)
class CantoAdmin(admin.ModelAdmin):
    list_display = ("numero",)
    inlines = [PaginaImagemInline]


@admin.register(PaginaImagem)
class PaginaImagemAdmin(admin.ModelAdmin):
    list_display = ("canto", "numero", "imagem")


@admin.register(PaginaTexto)
class PaginaTextoAdmin(admin.ModelAdmin):
    list_display = ("canto", "numero", "versao")
    list_filter = ("canto", "versao")
    ordering = ("canto", "numero")
    search_fields = ("tei_xml",)

    fieldsets = (
        ("Metadados", {
            "fields": ("canto", "numero", "versao")
        }),
        ("TEI (fonte)", {
            "fields": ("tei_xml",),
            "description": "Cole o XML TEI aqui"
        }),
    )