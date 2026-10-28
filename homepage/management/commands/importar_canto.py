"""
Comando de gerenciamento: importa TODAS as estrofes de um canto a partir de
um arquivo TEI-XML de origem (ex: LusiadasTextos/LusiadasModernizado.xml)
para dentro de PaginaTexto 
IMPORTANTE: a divisão em "páginas" aqui é sintética/artificial (N estrofes
por página, agrupadas em sequência) -- o arquivo de origem não tem marcação
de quebra de página real, então isso NÃO reflete a paginação verdadeira do
fac-símile. É só para termos dados suficientes pra testar a funcionalidade;
quando a paginação real for definida (alinhada às imagens digitalizadas),
os dados aqui deverão ser substituídos por uma importação página a página.

Uso:
    python manage.py importar_canto 1 LusiadasTextos/LusiadasModernizado.xml
    python manage.py importar_canto 1 LusiadasTextos/LusiadasModernizado.xml --por-pagina 3
    python manage.py importar_canto 2 LusiadasTextos/LusiadasModernizado.xml --versao modernizado

O comando é idempotente: rodar de novo com os mesmos parâmetros atualiza
as páginas existentes em vez de duplicá-las (usa update_or_create em
canto+numero+versao, que já é a chave única do modelo).
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from homepage.utils.importacao import ErroDeArquivo, carregar_xml, divs_de_canto, gravar_canto


class Command(BaseCommand):
    help = (
        "Importa todas as estrofes de um canto a partir de um TEI-XML "
        "(ex: LusiadasModernizado.xml), agrupando-as em páginas sintéticas "
        "-- só para testar a navegação por estrofe em escala."
    )

    def add_arguments(self, parser):
        parser.add_argument("canto", type=int,
                            help="Número do canto a importar (ex: 1)")
        parser.add_argument("arquivo_xml", type=str,
                            help="Caminho do arquivo TEI-XML de origem")
        parser.add_argument(
            "--versao", type=str, default="modernizado", choices=["modernizado", "original", "original_a", "original_b"],
            help="Versão a gravar em PaginaTexto (padrão: modernizado)",
        )
        parser.add_argument(
            "--por-pagina", type=int, default=2,
            help="Quantas estrofes agrupar por página sintética (padrão: 2)",
        )

    def handle(self, *args, **options):
        numero_canto = options["canto"]
        caminho = Path(options["arquivo_xml"])
        versao = options["versao"]
        por_pagina = options["por_pagina"]

        if not caminho.exists():
            raise CommandError(f"Arquivo não encontrado: {caminho}")

        if por_pagina < 1:
            raise CommandError("--por-pagina precisa ser pelo menos 1")

        try:
            root = carregar_xml(caminho)
        except ErroDeArquivo as erro:
            raise CommandError(str(erro))

        div_canto = None
        for div in divs_de_canto(root):
            if div.get("n") == str(numero_canto):
                div_canto = div
                break

        if div_canto is None:
            raise CommandError(
                f'Não encontrei <div type="canto" n="{numero_canto}"> em {caminho}'
            )

        try:
            r = gravar_canto(div_canto, numero_canto, versao, por_pagina)
        except ErroDeArquivo as erro:
            raise CommandError(f"{erro} Arquivo: {caminho}")
        titulo_canto, estrofes = r["titulo"], range(r["estrofes"])
        grupos, criadas, atualizadas, canto_criado = range(r["paginas"]), r["criadas"], r["atualizadas"], r["canto_criado"]

        self.stdout.write(self.style.SUCCESS(
            f'Canto {numero_canto} ("{titulo_canto}"): {len(estrofes)} estrofes -> '
            f"{len(grupos)} páginas sintéticas ({por_pagina} estrofes/página), versão '{versao}'."
        ))
        self.stdout.write(
            f"  {criadas} página(s) criada(s), {atualizadas} atualizada(s).")
        if canto_criado:
            self.stdout.write(
                f"  Canto {numero_canto} criado no banco (não existia antes).")
        self.stdout.write(self.style.WARNING(
            "Atenção: a divisão em páginas é artificial (o arquivo de origem não tem "
            "marcação de quebra de página real) -- serve só para testar a navegação "
            "por estrofe em escala, não reflete a paginação real do fac-símile."
        ))
