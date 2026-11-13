"""Importa TODOS os cantos, nas três versões de texto, de uma vez, cadastra as
imagens do fac-símile e mostra um relatório de integridade dos arquivos.

Uso (na pasta do projeto, onde fica o manage.py):
    python manage.py importar_tudo                  # verifica e importa tudo
    python manage.py importar_tudo --so-relatorio   # só verifica, não grava nada
    python manage.py importar_tudo --cantos 1 2     # só alguns cantos
    python manage.py importar_tudo --sem-imagens    # não mexe nas imagens
    python manage.py importar_tudo --relatorio relatorio.txt   # salva o relatório

Versões gravadas (arquivos em LusiadasTextos/):
    modernizado <- LusiadasModernizado.xml
    original_a  <- LusiadasEsquerda.xml   (pelicano à esquerda)  + imagens A
    original_b  <- LusiadasDireita.xml    (pelicano à direita)   + imagens B

PAGINAÇÃO
    Se os originais tiverem <pb facs="..."/>, cada página do banco é uma página
    do fac-símile: os originais são divididos pelas próprias <pb> e o
    modernizado segue as mesmas estrofes da edição A. As imagens indicadas em
    facs (caminho relativo ao XML) são copiadas para MEDIA_ROOT/facsimile/ e
    associadas às páginas (PaginaImagem A e B). Páginas que contêm o fim de um
    canto e o começo do seguinte aparecem nos dois cantos.

    Sem <pb> (ou com --por-pagina N), volta à divisão sintética de N estrofes
    por página, que NÃO corresponde ao fac-símile.

Os cantos são identificados pela POSIÇÃO no arquivo, e não pelo atributo n,
porque na LusiadasDireita.xml o canto 9 está marcado n="8". Cada caso desses
aparece no relatório. O comando é idempotente: rodar de novo atualiza as
páginas em vez de duplicá-las e remove páginas que deixaram de existir nos
XMLs, dentro do escopo importado.
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from homepage.models import Canto, PaginaImagem, PaginaTexto
from homepage.utils.importacao import (
    ESTROFES_ESPERADAS, FONTES, ErroDeArquivo,
    carregar_xml, divs_de_canto, gravar_canto, gravar_paginas_reais,
    paginas_de_cada_canto, paginas_por_pb, paginas_por_referencia,
    tem_paginacao, titulo_do_canto, verificar_integridade,
)

# versão de texto -> edição das imagens (a mesma <pb> dá o texto e a imagem)
EDICAO_DA_VERSAO = {"original_a": "A", "original_b": "B"}
VERSAO_DE_REFERENCIA = "original_a"
PASTA_MEDIA = "facsimile"


class Command(BaseCommand):
    help = "Importa todos os cantos nas três versões de texto (e as imagens) e relata problemas nos XMLs."

    def add_arguments(self, parser):
        parser.add_argument("--pasta", default="LusiadasTextos",
                            help="Pasta dos XMLs, relativa ao projeto (padrão: LusiadasTextos)")
        parser.add_argument("--por-pagina", type=int, default=None,
                            help="Força a paginação sintética: N estrofes por página "
                                 "(padrão: páginas reais do fac-símile; 2 se não houver <pb>)")
        parser.add_argument("--cantos", type=int, nargs="+", metavar="N",
                            help="Importar só estes cantos (padrão: todos os que os arquivos têm)")
        parser.add_argument("--sem-imagens", action="store_true",
                            help="Não copia nem cadastra as imagens do fac-símile")
        parser.add_argument("--so-relatorio", action="store_true",
                            help="Só verifica os arquivos; não grava nada no banco")
        parser.add_argument("--relatorio", metavar="ARQUIVO",
                            help="Também grava o relatório de integridade neste arquivo de texto")

    def handle(self, *args, **opcoes):
        if opcoes["por_pagina"] is not None and opcoes["por_pagina"] < 1:
            raise CommandError("--por-pagina precisa ser pelo menos 1")

        pasta = Path(settings.BASE_DIR) / opcoes["pasta"]
        filtro = set(opcoes["cantos"]) if opcoes["cantos"] else None
        if filtro and not filtro <= set(ESTROFES_ESPERADAS):
            raise CommandError(f"--cantos só aceita números de 1 a {len(ESTROFES_ESPERADAS)}")

        # 1) carrega e verifica tudo ANTES de gravar
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

        # paginação real (pelas <pb> da edição de referência)?
        raizes = {versao: root for versao, _, root in arquivos}
        referencia = raizes.get(VERSAO_DE_REFERENCIA)
        paginacao_real = (opcoes["por_pagina"] is None and referencia is not None
                          and tem_paginacao(referencia))
        paginas = {}
        if paginacao_real:
            paginas_ref = paginas_por_pb(referencia)
            linhas_relatorio.append(
                f"== Paginação (referência: '{VERSAO_DE_REFERENCIA}', {len(paginas_ref)} páginas)")
            for versao, nome, root in arquivos:
                if tem_paginacao(root):
                    paginas[versao] = paginas_por_pb(root)
                    linhas_relatorio += self._comparar_paginacao(nome, paginas[versao], paginas_ref, contagem)
                else:
                    paginas[versao] = paginas_por_referencia(root, paginas_ref)
                    linhas_relatorio.append(f"  {nome}: sem <pb>; paginado pelas estrofes da referência.")
            linhas_relatorio.append("")

        self._mostrar_relatorio(linhas_relatorio, contagem)
        if opcoes["relatorio"]:
            Path(opcoes["relatorio"]).write_text("\n".join(linhas_relatorio) + "\n", encoding="utf-8")
            self.stdout.write(f"Relatório salvo em {opcoes['relatorio']}\n")

        if opcoes["so_relatorio"]:
            self.stdout.write("Modo --so-relatorio: nada foi gravado no banco.")
            return

        # 2) grava (modernizado primeiro: é ele que dá o título ao Canto)
        por_pagina = opcoes["por_pagina"] or 2
        total_criadas = total_atualizadas = total_removidas = 0
        cantos_para_sincronizar = filtro if filtro is not None else set(ESTROFES_ESPERADAS)

        def no_escopo(posicao):
            return posicao in ESTROFES_ESPERADAS and (not filtro or posicao in filtro)

        self.stdout.write(self.style.MIGRATE_HEADING(
            "Importando (páginas do fac-símile)..." if paginacao_real
            else f"Importando (páginas sintéticas de {por_pagina} estrofes)..."))

        with transaction.atomic():
            for versao, nome, root in arquivos:
                paginas_importadas = {}
                divs = divs_de_canto(root)
                if paginacao_real:
                    for posicao, indices in sorted(paginas_de_cada_canto(paginas[versao]).items()):
                        if not no_escopo(posicao):
                            continue
                        titulo = titulo_do_canto(divs[posicao - 1], posicao) if posicao <= len(divs) else None
                        r = gravar_paginas_reais(paginas[versao], indices, posicao, versao, titulo)
                        paginas_importadas[posicao] = r["paginas"]
                        total_criadas += r["criadas"]
                        total_atualizadas += r["atualizadas"]
                        self.stdout.write(f"  canto {posicao:>2} [{versao:<11}] -> {r['paginas']:>3} páginas")
                else:
                    for posicao, div in enumerate(divs, start=1):
                        if not no_escopo(posicao):
                            continue
                        r = gravar_canto(div, posicao, versao, por_pagina)
                        paginas_importadas[posicao] = r["paginas"]
                        total_criadas += r["criadas"]
                        total_atualizadas += r["atualizadas"]
                        self.stdout.write(
                            f"  canto {posicao:>2} [{versao:<11}] {r['estrofes']:>3} estrofes -> {r['paginas']:>3} páginas")

                for numero_canto in cantos_para_sincronizar:
                    total_removidas += self._remover_excedentes(
                        PaginaTexto.objects.filter(canto__numero=numero_canto, versao=versao),
                        paginas_importadas.get(numero_canto, 0))

            if paginacao_real and not opcoes["sem_imagens"]:
                for versao, edicao in EDICAO_DA_VERSAO.items():
                    if versao in raizes and tem_paginacao(raizes[versao]):
                        self._gravar_imagens(paginas[versao], edicao, pasta, no_escopo, cantos_para_sincronizar)

            for numero_canto in cantos_para_sincronizar:
                canto = Canto.objects.filter(numero=numero_canto).first()
                if canto and not canto.textos.exists() and not canto.paginas.exists():
                    canto.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Concluído: {total_criadas} página(s) criada(s), "
            f"{total_atualizadas} atualizada(s), {total_removidas} removida(s)."))
        if not paginacao_real:
            self.stdout.write(self.style.WARNING(
                "Lembrete: a divisão em páginas é artificial e não corresponde ao fac-símile."))

    # ------------------------------------------------------------------

    @staticmethod
    def _remover_excedentes(queryset, total):
        if total:
            removidas, _ = queryset.exclude(numero__range=(1, total)).delete()
        else:
            removidas, _ = queryset.delete()
        return removidas

    @staticmethod
    def _comparar_paginacao(nome, paginas, referencia, contagem):
        if [p.estrofes() for p in paginas] == [p.estrofes() for p in referencia]:
            return [f"  {nome}: {len(paginas)} páginas, com as mesmas estrofes da referência."]
        contagem["AVISO"] += 1
        linhas = [f"  [AVISO] {nome}: {len(paginas)} páginas; a paginação difere da referência."]
        for i, (p, r) in enumerate(zip(paginas, referencia), start=1):
            if p.estrofes() != r.estrofes():
                linhas.append(f"    primeira diferença na {i}ª página ({p.facs or 'sem facs'}): "
                              f"{p.estrofes()[:3]} x {r.estrofes()[:3]}")
                break
        return linhas

    def _gravar_imagens(self, paginas, edicao, pasta_xml, no_escopo, cantos_para_sincronizar):
        """Copia as imagens indicadas em facs para MEDIA_ROOT e cria as PaginaImagem."""
        destino_base = Path(settings.MEDIA_ROOT) / PASTA_MEDIA
        copiadas = cadastradas = 0
        faltando = set()
        gravadas = {}
        for posicao, indices in sorted(paginas_de_cada_canto(paginas).items()):
            if not no_escopo(posicao):
                continue
            canto = Canto.objects.get(numero=posicao)
            gravadas[posicao] = len(indices)
            for local, i in enumerate(indices, start=1):
                facs = paginas[i].facs
                origem = (pasta_xml / facs).resolve() if facs else None
                if origem is None or not origem.is_file():
                    faltando.add(Path(facs).name if facs else f"(canto {posicao}, pág. {local}, sem facs)")
                    PaginaImagem.objects.filter(canto=canto, numero=local, edicao=edicao).delete()
                    continue
                destino = destino_base / origem.parent.name / origem.name
                if not destino.exists() or destino.stat().st_size != origem.stat().st_size:
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(origem, destino)
                    copiadas += 1
                PaginaImagem.objects.update_or_create(
                    canto=canto, numero=local, edicao=edicao,
                    defaults={"imagem": f"{PASTA_MEDIA}/{origem.parent.name}/{origem.name}"})
                cadastradas += 1

        for numero_canto in cantos_para_sincronizar:
            self._remover_excedentes(
                PaginaImagem.objects.filter(canto__numero=numero_canto, edicao=edicao),
                gravadas.get(numero_canto, 0))

        self.stdout.write(
            f"  imagens {edicao}: {cadastradas} associada(s) às páginas, {copiadas} copiada(s) para {destino_base}")
        if faltando:
            lista = sorted(faltando)
            self.stdout.write(self.style.WARNING(
                f"  imagens {edicao}: {len(lista)} arquivo(s) não encontrado(s): {', '.join(lista[:15])}"
                + (" ..." if len(lista) > 15 else "")))

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
