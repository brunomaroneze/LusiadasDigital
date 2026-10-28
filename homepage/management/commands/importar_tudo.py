"""Importa TODOS os cantos, nas três versões de texto, de uma vez, e mostra um
relatório de integridade dos arquivos de origem.

Uso (na pasta do projeto, onde fica o manage.py):
    python manage.py importar_tudo                  # verifica e importa tudo
    python manage.py importar_tudo --so-relatorio   # só verifica, não grava nada
    python manage.py importar_tudo --cantos 1 2     # só alguns cantos
    python manage.py importar_tudo --por-pagina 3
    python manage.py importar_tudo --relatorio relatorio.txt   # salva o relatório

Versões gravadas (arquivos em LusiadasTextos/):
    modernizado <- LusiadasModernizado.xml
    original_a  <- LusiadasEsquerda.xml   (pelicano à esquerda)
    original_b  <- LusiadasDireita.xml    (pelicano à direita)

Os cantos são identificados pela POSIÇÃO no arquivo, e não pelo atributo n,
porque na LusiadasDireita.xml o canto 9 está marcado n="8". Cada caso desses
aparece no relatório.

Como no importar_canto, a divisão em páginas é sintética (N estrofes por
página) e NÃO corresponde à paginação do fac-símile. O comando é idempotente:
rodar de novo atualiza as páginas em vez de duplicá-las.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from homepage.utils.importacao import (
    ESTROFES_ESPERADAS, FONTES, ErroDeArquivo,
    carregar_xml, divs_de_canto, gravar_canto, verificar_integridade,
)


class Command(BaseCommand):
    help = "Importa todos os cantos nas três versões de texto e relata problemas nos XMLs."

    def add_arguments(self, parser):
        parser.add_argument("--pasta", default="LusiadasTextos",
                            help="Pasta dos XMLs, relativa ao projeto (padrão: LusiadasTextos)")
        parser.add_argument("--por-pagina", type=int, default=2,
                            help="Estrofes por página sintética (padrão: 2; use o mesmo valor nas três versões)")
        parser.add_argument("--cantos", type=int, nargs="+", metavar="N",
                            help="Importar só estes cantos (padrão: todos os que os arquivos têm)")
        parser.add_argument("--so-relatorio", action="store_true",
                            help="Só verifica os arquivos; não grava nada no banco")
        parser.add_argument("--relatorio", metavar="ARQUIVO",
                            help="Também grava o relatório de integridade neste arquivo de texto")

    def handle(self, *args, **opcoes):
        if opcoes["por_pagina"] < 1:
            raise CommandError("--por-pagina precisa ser pelo menos 1")

        pasta = Path(settings.BASE_DIR) / opcoes["pasta"]
        filtro = set(opcoes["cantos"]) if opcoes["cantos"] else None
        if filtro and not filtro <= set(ESTROFES_ESPERADAS):
            raise CommandError(f"--cantos só aceita números de 1 a {len(ESTROFES_ESPERADAS)}")

        # 1) carrega e verifica tudo ANTES de gravar (gravar move nós do XML)
        arquivos, linhas_relatorio, contagem = [], [], {"ERRO": 0, "AVISO": 0, "INFO": 0}
        for versao, nome in FONTES:
            try:
                root = carregar_xml(pasta / nome)
            except ErroDeArquivo as erro:
                raise CommandError(str(erro))
            arquivos.append((versao, nome, root))

            problemas = verificar_integridade(root)
            for p in problemas:
                contagem[p.nivel] += 1
            linhas_relatorio.append(f"== {nome}  (versão '{versao}')")
            linhas_relatorio += [f"  {p}" for p in problemas] or ["  nenhum problema encontrado."]
            linhas_relatorio.append("")

        self._mostrar_relatorio(linhas_relatorio, contagem)
        if opcoes["relatorio"]:
            Path(opcoes["relatorio"]).write_text("\n".join(linhas_relatorio) + "\n", encoding="utf-8")
            self.stdout.write(f"Relatório salvo em {opcoes['relatorio']}\n")

        if opcoes["so_relatorio"]:
            self.stdout.write("Modo --so-relatorio: nada foi gravado no banco.")
            return

        # 2) grava (modernizado primeiro: é ele que dá o título ao Canto)
        total_criadas = total_atualizadas = 0
        self.stdout.write(self.style.MIGRATE_HEADING("Importando..."))
        with transaction.atomic():
            for versao, nome, root in arquivos:
                for posicao, div in enumerate(divs_de_canto(root), start=1):
                    if posicao not in ESTROFES_ESPERADAS or (filtro and posicao not in filtro):
                        continue
                    r = gravar_canto(div, posicao, versao, opcoes["por_pagina"])
                    total_criadas += r["criadas"]
                    total_atualizadas += r["atualizadas"]
                    self.stdout.write(
                        f"  canto {posicao:>2} [{versao:<11}] {r['estrofes']:>3} estrofes -> {r['paginas']:>3} páginas")

        self.stdout.write(self.style.SUCCESS(
            f"Concluído: {total_criadas} página(s) criada(s), {total_atualizadas} atualizada(s)."))
        self.stdout.write(self.style.WARNING(
            "Lembrete: a divisão em páginas é artificial e não corresponde ao fac-símile."))

    def _mostrar_relatorio(self, linhas, contagem):
        self.stdout.write(self.style.MIGRATE_HEADING("Relatório de integridade dos arquivos de origem"))
        for linha in linhas:
            if "[ERRO]" in linha:
                self.stdout.write(self.style.ERROR(linha))
            elif "[AVISO]" in linha:
                self.stdout.write(self.style.WARNING(linha))
            else:
                self.stdout.write(linha)
        self.stdout.write(
            f"Resumo: {contagem['ERRO']} erro(s), {contagem['AVISO']} aviso(s), {contagem['INFO']} informação(ões).\n")
