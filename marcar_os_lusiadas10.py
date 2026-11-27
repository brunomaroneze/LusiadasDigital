# -*- coding: utf-8 -*-
"""Marca entidades nomeadas nos cantos da edição modernizada. Requer lxml."""
import argparse
from collections import defaultdict
import os
from pathlib import Path
import re
import stat
from tempfile import NamedTemporaryFile

from lxml import etree

TEI = "{http://www.tei-c.org/ns/1.0}"
NS = {"tei": TEI[1:-1]}

# Lista fechada do script original, incluindo os tipos e as referências.
EPITETOS = {
    "ocidental praia Lusitana": ("place", "#portugal"),
    "Capitão": ("person", "#v_gama"),
    "O ilustre Gama": ("person", "#v_gama"),
    "Sublime Rei": ("person", "#d_sebastiao"),
    "filho de Maia": ("myth", "#mercurio"),
    "clara Deia": ("myth", "#venus"),
    "bela Deusa": ("myth", "#venus"),
    "grão Tebano": ("myth", "#baco"),
}
PADRAO_EPITETOS = re.compile(
    r"(?<!\w)(?:" + "|".join(map(re.escape, sorted(EPITETOS, key=len, reverse=True)))
    + r")(?!\w)"
)

# Chave: (estrofe, texto do verso oficial).
# Cada marcação guarda início e fim no verso, elemento TEI, tipo e ref.
# As posições vieram do alinhamento com a revisão manual do Canto I.
NOMES_REVISADOS = {
    (1, 'Passaram ainda além da Taprobana,'): [
        (23, 32, 'placeName', 'real', '#taprobana'),
    ],
    (2, 'De África e de Ásia andaram devastando;'): [
        (3, 9, 'placeName', 'real', '#africa'),
        (15, 19, 'placeName', 'real', '#asia'),
    ],
    (3, 'Cale-se de Alexandro e de Trajano'): [
        (11, 20, 'persName', 'hist', '#alexandro'),
        (26, 33, 'persName', 'hist', '#trajano'),
    ],
    (3, 'A quem Neptuno e Marte obedeceram:'): [
        (7, 14, 'persName', 'myth', '#neptuno'),
        (17, 22, 'persName', 'myth', '#marte'),
    ],
    (3, 'Cesse tudo o que a Musa antígua canta,'): [
        (19, 23, 'persName', 'myth', '#musa'),
    ],
    (4, 'E vós, Tágides minhas, pois criado'): [
        (7, 14, 'persName', 'myth', '#tagides'),
    ],
    (4, 'Que não tenham inveja às de Hipoerene.'): [
        (28, 37, 'placeName', 'myth', '#hipocrene'),
    ],
    (5, 'Gente vossa, que a Marte tanto ajuda;'): [
        (19, 24, 'persName', 'myth', '#marte'),
    ],
    (6, 'Dada ao mundo por Deus, que todo o mande,'): [
        (18, 22, 'persName', 'myth', '#deus'),
    ],
    (6, 'Para do mundo a Deus dar parte grande;'): [
        (16, 20, 'persName', 'myth', '#deus'),
    ],
    (11, 'Musas, de engrandecer-se desejosas:'): [
        (0, 5, 'persName', 'myth', '#musa'),
    ],
    (11, 'Que excedem Rodamonte, e o vão Rugeiro,'): [
        (12, 21, 'persName', 'myth', '#rodamonte'),
        (31, 38, 'persName', 'myth', '#rugeiro'),
    ],
    (11, 'E Orlando, inda que fora verdadeiro,'): [
        (2, 9, 'persName', 'myth', '#orlando'),
    ],
    (12, 'Por estes vos darei um Nuno fero,'): [
        (23, 27, 'persName', 'hist', '#nuno_alvares'),
    ],
    (12, 'Um Egas, e um D. Fuas, que de Homero'): [
        (3, 7, 'persName', 'hist', '#egas'),
        (14, 21, 'persName', 'hist', '#d._fuas'),
        (30, 36, 'persName', 'hist', '#homero'),
    ],
    (12, 'Os doze de Inglaterra, e o seu Magriço;'): [
        (11, 21, 'placeName', 'real', '#inglaterra'),
        (31, 38, 'persName', 'hist', '#magriço'),
    ],
    (12, 'Dou-vos também aquele ilustre Gama,'): [
        (30, 34, 'persName', 'hist', '#v_gama'),
    ],
    (12, 'Que para si de Eneias toma a fama.'): [
        (15, 21, 'persName', 'hist', '#eneias'),
    ],
    (13, 'Pois se a troco de Carlos, Rei de França,'): [
        (19, 25, 'persName', 'hist', '#carlos_magno'),
        (34, 40, 'placeName', 'real', '#franca'),
    ],
    (13, 'Ou de César, quereis igual memória,'): [
        (6, 11, 'persName', 'hist', '#julio_cesar'),
    ],
    (13, 'Vede o primeiro Afonso, cuja lança'): [
        (16, 22, 'persName', 'hist', None),
    ],
    (13, 'Outro Joane, invicto cavaleiro,'): [
        (6, 11, 'persName', 'hist', None),
    ],
    (13, 'O quarto e quinto Afonsos, e o terceiro.'): [
        (18, 25, 'persName', 'hist', None),
    ],
    (14, 'Um Pacheco fortíssimo, e os temidos'): [
        (3, 10, 'persName', 'hist', '#pacheco'),
    ],
    (14, 'Almeidas, por quem sempre o Tejo chora;'): [
        (0, 8, 'persName', 'hist', '#almeidas'),
        (28, 32, 'placeName', 'real', '#tejo'),
    ],
    (14, 'Albuquerque terríbil, Castro forte,'): [
        (0, 11, 'persName', 'hist', '#afonso_albuquerque'),
        (22, 28, 'persName', 'hist', '#joao_castro'),
    ],
    (15, 'Tomai as rédeas vós do Reino vosso:'): [
        (23, 28, 'placeName', 'real', '#portugal'),
    ],
    (15, 'De África as terras, e do Oriente os marços,'): [
        (3, 9, 'placeName', 'real', '#africa'),
    ],
    (16, 'Tethys todo o cerúleo senhorio'): [
        (0, 6, 'persName', 'myth', '#tetis'),
    ],
    (19, 'Que do gado de Próteo são cortadas'): [
        (15, 21, 'persName', 'myth', '#proteu'),
    ],
    (20, 'Quando os Deuses no Olimpo luminoso,'): [
        (20, 26, 'placeName', 'myth', '#olimpo'),
    ],
    (20, 'Pelo neto gentil do velho Atlante.'): [
        (26, 33, 'persName', 'myth', '#atlante'),
    ],
    (22, 'Que vibra os feros raios de Vulcano,'): [
        (28, 35, 'persName', 'myth', '#vulcano'),
    ],
    (23, 'Quando Júpiter alto, assim dizendo,'): [
        (7, 14, 'persName', 'myth', '#jupiter'),
    ],
    (25, 'Toda a terra, que rega o Tejo ameno:'): [
        (25, 29, 'placeName', 'real', '#tejo'),
    ],
    (26, 'Que coa gente de Rómulo alcançaram,'): [
        (17, 23, 'persName', 'hist', '#romulo'),
    ],
    (26, 'Quando com Viriato, na inimiga'): [
        (11, 18, 'persName', 'hist', '#viriato'),
    ],
    (27, 'De Áf rico e Noto a força, a mais se atreve:'): [
        (3, 10, 'persName', 'myth', '#africo'),
        (13, 17, 'persName', 'myth', '#noto'),
    ],
    (28, '"Prometido lhe está do Fado eterno,'): [
        (23, 27, 'persName', 'myth', '#fado'),
    ],
    (30, 'Estas palavras Júpiter dizia,'): [
        (15, 22, 'persName', 'myth', '#jupiter'),
    ],
    (30, 'O padre Baco ali não consentia'): [
        (8, 12, 'persName', 'myth', '#baco'),
    ],
    (30, 'No que Júpiter disse, conhecendo'): [
        (7, 14, 'persName', 'myth', '#jupiter'),
    ],
    (31, 'Uma gente fortíssima de Espanha'): [
        (24, 31, 'placeName', 'real', '#espanha'),
    ],
    (31, 'Da índia tudo quanto Dóris banha,'): [
        (3, 8, 'placeName', 'real', '#índia'),
        (21, 26, 'persName', 'myth', '#doris'),
    ],
    (31, 'De que Nisa celebra inda a memória.'): [
        (7, 11, 'placeName', 'myth', '#nisa'),
    ],
    (32, 'Vê que já teve o Indo sojugado,'): [
        (17, 21, 'placeName', 'real', '#indo'),
    ],
    (32, 'E nunca lhe tirou Fortuna, ou caso,'): [
        (18, 25, 'persName', 'myth', '#fortuna'),
    ],
    (32, 'Por vencedor da Índia ser cantado'): [
        (16, 21, 'placeName', 'real', '#índia'),
    ],
    (32, 'De quantos bebem a água de Parnaso.'): [
        (27, 34, 'placeName', 'real', '#parnaso'),
    ],
    (33, 'Sustentava contra ele Vénus bela,'): [
        (22, 27, 'persName', 'myth', '#venus'),
    ],
    (33, 'Que mostraram na terra Tingitana,'): [
        (23, 32, 'placeName', 'real', '#tingitana'),
    ],
    (34, 'Estas causas moviam Citereia,'): [
        (20, 28, 'persName', 'myth', '#venus'),
    ],
    (34, 'E mais, porque das Parcas claro entende'): [
        (19, 25, 'persName', 'myth', '#parcas'),
    ],
    (35, 'Entre os Deuses, no Olimpo consagrado.'): [
        (20, 26, 'placeName', 'myth', '#olimpo'),
    ],
    (36, 'Mas Marte, que da Deusa sustentava'): [
        (4, 9, 'persName', 'myth', '#marte'),
    ],
    (37, 'De Júpiter, armado, forte e duro:'): [
        (3, 10, 'persName', 'myth', '#jupiter'),
    ],
    (37, 'O Céu tremeu, e Apolo, de torvado,'): [
        (16, 21, 'persName', 'myth', '#apolo'),
    ],
    (39, 'Bem fora que aqui Baco os sustentasse,'): [
        (18, 22, 'persName', 'myth', '#baco'),
    ],
    (40, 'Mercúrio, pois excede em ligeireza'): [
        (0, 8, 'persName', 'myth', '#mercúrio'),
    ],
    (40, 'Da índia, e onde a gente se reforme."'): [
        (3, 8, 'placeName', 'real', '#índia'),
    ],
    (41, 'No que disse Mavorte valeroso,'): [
        (13, 20, 'persName', 'myth', '#marte'),
    ],
    (42, 'Casa etérea do Olimpo onipotente,'): [
        (15, 21, 'placeName', 'myth', '#olimpo'),
    ],
    (42, 'Entre a costa Etiópica e a famosa'): [
        (14, 22, 'placeName', 'real', '#etiopia'),
    ],
    (42, 'Ilha de São Lourenço; e o Sol ardente'): [
        (0, 20, 'placeName', 'real', '#madagascar'),
    ],
    (42, 'Queimava então os Deuses, que Tifeu'): [
        (30, 35, 'persName', 'myth', '#tifeu'),
    ],
    (43, 'O promontório Prasso já passavam,'): [
        (14, 20, 'placeName', 'real', '#prasso_promontorio'),
    ],
    (43, 'Na costa de Etiópia, nome antigo,'): [
        (12, 19, 'placeName', 'real', '#etiopia'),
    ],
    (44, 'Vasco da Gama, o forte capitão,'): [
        (0, 13, 'persName', 'hist', '#v_gama'),
    ],
    (44, 'A quem Fortuna sempre favorece,'): [
        (7, 14, 'persName', 'myth', '#fortuna'),
    ],
    (46, 'Que Faeton, nas terras acendidas,'): [
        (4, 10, 'persName', 'myth', '#faeton'),
    ],
    (46, 'O Pado o sabe, o Lampetusa o sente.'): [
        (2, 6, 'placeName', 'real', '#rio_pado'),
        (17, 26, 'persName', 'myth', '#lampetusa'),
    ],
    (49, 'Do licor que Lieo prantado havia'): [
        (13, 17, 'persName', 'myth', '#baco'),
    ],
    (49, 'Os de Faeton queimados nada enjeitam.'): [
        (6, 12, 'persName', 'myth', '#faeton'),
    ],
    (51, 'Toda a parte do Antártico e Calisto,'): [
        (28, 35, 'persName', 'myth', '#calisto'),
    ],
    (51, 'Mas no lago entraremos de Aqueronte.'): [
        (26, 35, 'placeName', 'myth', '#aqueronte'),
    ],
    (52, 'A terra Oriental que o Indo rega;'): [
        (23, 27, 'placeName', 'real', '#indo'),
    ],
    (52, 'Ou se tendes da Índia alguns sinais?"'): [
        (16, 21, 'placeName', 'real', '#índia'),
    ],
    (53, 'O claro descendente de Abraão'): [
        (23, 29, 'persName', 'hist', '#abraao'),
    ],
    (54, 'De Quíloa, de Mombaça e de Sofala;'): [
        (3, 9, 'placeName', 'real', '#quiloa'),
        (14, 21, 'placeName', 'real', '#mombaca'),
        (27, 33, 'placeName', 'real', '#sofala'),
    ],
    (54, 'Chama-se a pequena ilha Moçambique.'): [
        (19, 34, 'placeName', 'real', '#mocambique'),
    ],
    (55, 'Buscando o Indo Idaspe e terra ardente,'): [
        (11, 15, 'placeName', 'real', '#indo'),
        (16, 22, 'placeName', 'real', '#idaspe'),
    ],
    (56, 'Nisto Febo nas águas encerrou,'): [
        (6, 10, 'persName', 'myth', '#apolo'),
    ],
    (59, 'Mas assim como a Aurora marchetada'): [
        (17, 23, 'persName', 'myth', '#aurora'),
    ],
    (59, 'Ao claro Hiperiónio, que acordou,'): [
        (9, 19, 'persName', 'myth', '#hiperiao'),
    ],
    (60, 'Vieram; e por ordem do Destino,'): [
        (23, 30, 'persName', 'myth', '#fado'),
    ],
    (60, 'O Império tomaram a Constantino.'): [
        (20, 31, 'persName', 'hist', '#constantino'),
    ],
    (62, 'Está a gente marítima de Luso'): [
        (25, 29, 'placeName', 'real', '#portugal'),
    ],
    (62, '"Se por ventura vinham de Turquia?"'): [
        (26, 33, 'placeName', 'real', '#turquia'),
    ],
    (64, 'Das gentes enojosas de Turquia:'): [
        (23, 30, 'placeName', 'real', '#turquia'),
    ],
    (64, 'Mas sou da forte Europa belicosa,'): [
        (17, 23, 'placeName', 'real', '#europa'),
    ],
    (64, 'Busco as terras da índia tão famosa.'): [
        (19, 24, 'placeName', 'real', '#índia'),
    ],
    (68, 'Porém aos de Vulcano não consente'): [
        (13, 20, 'persName', 'myth', '#vulcano'),
    ],
    (70, 'Por quem pudesse à Índia ser levado;'): [
        (19, 24, 'placeName', 'real', '#índia'),
    ],
    (71, 'Que o Filho de David nos ensinou.'): [
        (15, 20, 'persName', 'hist', '#david'),
    ],
    (72, 'Das águas de Neptuno, e recebido'): [
        (13, 20, 'persName', 'myth', '#neptuno'),
    ],
    (75, 'O filho de Filipo nesta parte'): [
        (11, 17, 'persName', 'hist', '#filipo'),
    ],
    (75, 'Debaixo de seu jugo o fero Marte.'): [
        (27, 32, 'persName', 'myth', '#marte'),
    ],
    (77, 'Para o Prasso sabido se moveu.'): [
        (7, 13, 'placeName', 'real', '#prasso_promontorio'),
    ],
    (77, 'Dum Mouro, em Moçambique conhecido'): [
        (14, 24, 'placeName', 'real', '#mocambique'),
    ],
    (84, 'Os montes Nabatêos acendido,'): [
        (3, 18, 'placeName', 'real', '#nabateia'),
    ],
    (84, 'Quando o Gama, colos seus determinava'): [
        (9, 13, 'persName', 'hist', '#v_gama'),
    ],
    (95, 'Para ir buscar o Indo desejado,'): [
        (17, 21, 'placeName', 'real', '#indo'),
    ],
    (96, 'As ondas de Anfitrite dividia,'): [
        (12, 21, 'persName', 'myth', '#anfitrite'),
    ],
    (96, 'Das filhas de Nereu acompanhada,'): [
        (14, 19, 'persName', 'myth', '#nereu'),
    ],
    (96, 'Da Índia toda, e costas que passava.'): [
        (3, 8, 'placeName', 'real', '#índia'),
    ],
    (97, 'Que o malévolo Baco lhe ensinara,'): [
        (15, 19, 'persName', 'myth', '#baco'),
    ],
    (97, 'Antes que à Índia chegue, lhe prepara:'): [
        (12, 17, 'placeName', 'real', '#índia'),
    ],
    (98, 'Com que Sinon os Frígios enganou:'): [
        (8, 13, 'persName', 'myth', '#sinon'),
    ],
    (99, 'Gente que segue o torpe Mahamede.'): [
        (24, 32, 'persName', 'hist', '#maome'),
    ],
    (99, 'A Moçambique esta ilha, que se chama'): [
        (2, 12, 'placeName', 'real', '#mocambique'),
    ],
    (99, 'Quíloa, mui conhecida pela fama.'): [
        (0, 6, 'placeName', 'real', '#quiloa'),
    ],
    (100, 'Mas a Deusa em Citere celebrada,'): [
        (15, 21, 'placeName', 'real', '#citera'),
    ],
    (102, 'Mas a que a Mahamede celebrava.'): [
        (12, 20, 'persName', 'hist', '#maome'),
    ],
    (103, 'Mombaça é o nome da ilha e da cidade.'): [
        (0, 7, 'placeName', 'real', '#mombaca'),
    ],
    (104, 'Que Baco muito de antes o avisara,'): [
        (4, 8, 'persName', 'myth', '#baco'),
    ],
}


# Formas cujo uso como nome próprio ou epíteto depende da passagem.
FORMAS_CONTEXTUAIS = {"Reino", "Febo", "Aurora", "Luso"}
EPITETOS_CONTEXTUAIS = {
    "Capitão": r"\b(?:Vasco da Gama|Gama)\b",
    "Sublime Rei": r"\b(?:D\. Sebastião|Dom Sebastião)\b",
}
BLACKLIST = {
    "Fé", "Lei", "Rei", "Império", "Mundo", "Fama", "Guerra", "Paz",
    "Obras", "Canto", "Amor", "Morte", "Terra", "Mar",
}


def preparar_dicionario():
    """Reutiliza as etiquetas e referências verificadas no Canto I."""
    opcoes = defaultdict(set)
    for (_, verso), marcas in NOMES_REVISADOS.items():
        for inicio, fim, *etiqueta in marcas:
            forma = verso[inicio:fim]
            if forma != "Áf rico":  # separação de letras específica do XML oficial
                opcoes[forma].add(tuple(etiqueta))
    opcoes["Áfrico"].add(("persName", "myth", "#africo"))
    # Grafia alternativa já prevista no script original.
    opcoes["Venus"].update(opcoes["Vénus"])
    opcoes["Vênus"].update(opcoes["Vénus"])
    # Nomes explícitos do dicionário original ausentes da revisão.
    opcoes["Afonso Henriques"].add(("persName", "hist", "#afonso_henriques"))
    opcoes["D. Manuel"].add(("persName", "hist", "#d_manuel_i"))
    opcoes["Portugal"].add(("placeName", "real", "#portugal"))

    ambiguos = FORMAS_CONTEXTUAIS | {forma for forma, valores in opcoes.items()
                                     if len(valores) != 1}
    entradas = {forma: next(iter(valores)) for forma, valores in opcoes.items()
                if forma not in ambiguos}
    formas = sorted(entradas.keys() | ambiguos, key=lambda forma: (-len(forma), forma))
    padrao = re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, formas)) + r")(?!\w)")
    return entradas, padrao


def sugerir_novas_entidades(modelo, canto, numero, estrofe):
    """Sugere nomes no contexto da estrofe, sem atribuir refs automaticamente."""
    versos = ["".join(v.itertext()) for v in estrofe.findall(TEI + "l")]
    doc = modelo("\n".join(versos))
    conhecidos = {"".join(e.itertext()) for e in estrofe.iter()
                  if e.tag in {TEI + "persName", TEI + "placeName", TEI + "rs"}}
    for ent in doc.ents:
        forma = " ".join(ent.text.split())
        if (ent.label_ in {"PER", "LOC", "GPE"}
                and forma and forma not in BLACKLIST | conhecidos):
            yield canto, numero, forma


def sobrepoe(inicio, fim, marcas):
    return any(inicio < outro_fim and outro_inicio < fim
               for outro_inicio, outro_fim, *_ in marcas)


def inserir_no_texto(verso, anterior, texto, deslocamento, marcas):
    """Insere elementos somente em texto direto ou na cauda de um filho."""
    novas = [m for m in marcas
             if deslocamento <= m[0] < m[1] <= deslocamento + len(texto)]
    if not novas:
        return 0
    inicio_primeira = novas[0][0] - deslocamento
    if anterior is None:
        verso.text = texto[:inicio_primeira]
    else:
        anterior.tail = texto[:inicio_primeira]

    indice = 0 if anterior is None else verso.index(anterior) + 1
    for i, (inicio, fim, tag, tipo, ref) in enumerate(novas):
        elemento = etree.Element(TEI + tag)
        elemento.set("type", tipo)
        if ref:
            elemento.set("ref", f"autoridades.xml{ref}" if ref.startswith("#") else ref)
        elemento.text = texto[inicio - deslocamento:fim - deslocamento]
        proximo = novas[i + 1][0] if i + 1 < len(novas) else deslocamento + len(texto)
        elemento.tail = texto[fim - deslocamento:proximo - deslocamento]
        verso.insert(indice + i, elemento)
    return len(novas)


def marcar_verso(verso, marcas):
    # Usa os filhos originais para que as inserções não mudem os deslocamentos.
    filhos = list(verso)
    blocos = [(None, verso.text or "", 0)]
    cursor = len(verso.text or "")
    for filho in filhos:
        if isinstance(filho.tag, str):
            cursor += len(filho.xpath("string(.)"))
        cauda = filho.tail or ""
        blocos.append((filho, cauda, cursor))
        cursor += len(cauda)

    return sum(inserir_no_texto(verso, anterior, bloco, inicio, marcas)
               for anterior, bloco, inicio in blocos)


def salvar(destino, conteudo, modo):
    temporario = None
    try:
        with NamedTemporaryFile(dir=destino.parent, delete=False) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo)
        temporario.chmod(modo)
        temporario.replace(destino)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("xml", nargs="?", type=Path, default=Path("LusiadasModernizado.xml"))
    cli.add_argument("--aplicar", action="store_true", help="atualiza o próprio XML informado")
    cli.add_argument("--canto", type=int, choices=range(1, 11),
                     help="processa apenas um canto; por padrão, processa todos")
    cli.add_argument("--sugerir", action="store_true",
                     help="usa spaCy para listar possíveis entidades novas para revisão")
    args = cli.parse_args()
    modelo = None
    if args.sugerir:
        try:
            import spacy
            modelo = spacy.load("pt_core_news_lg")
        except (ImportError, OSError):
            cli.error("Para --sugerir, instale spaCy e o modelo pt_core_news_lg.")

    entrada = args.xml.resolve()
    try:
        original = entrada.read_bytes()
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        arvore = etree.fromstring(original, parser).getroottree()
        cantos = arvore.xpath(
            "/tei:TEI/tei:text/tei:body/tei:div[@type='canto']", namespaces=NS)
        if args.canto is not None:
            cantos = [canto for canto in cantos if canto.get("n") == str(args.canto)]
        if not cantos:
            raise ValueError("Não encontrei os cantos solicitados no corpo do TEI.")

        dicionario, padrao_nomes = preparar_dicionario()
        total = 0
        encontradas = set()
        sugestoes = set()
        for canto in cantos:
            identificador = int(canto.get("n"))
            novas = 0
            for estrofe in canto.xpath("./tei:lg[@type='estrofe']", namespaces=NS):
                numero = int(estrofe.get("n"))
                versos = [(v, "".join(v.itertext())) for v in estrofe.findall(TEI + "l")]
                contexto = "\n".join(texto for _, texto in versos)
                for verso, texto in versos:
                    epitetos = []
                    for match in PADRAO_EPITETOS.finditer(texto):
                        forma = match.group()
                        condicao = EPITETOS_CONTEXTUAIS.get(forma)
                        if identificador != 1 and condicao and not re.search(condicao, contexto):
                            sugestoes.add((identificador, numero, forma))
                            continue
                        epitetos.append((*match.span(), "rs", *EPITETOS[forma]))

                    chave = (numero, texto)
                    if identificador == 1:
                        nomes = NOMES_REVISADOS.get(chave, ())
                        if nomes:
                            encontradas.add(chave)
                    else:
                        nomes = []
                        for match in padrao_nomes.finditer(texto):
                            forma = match.group()
                            if sobrepoe(*match.span(), epitetos):
                                continue
                            if forma in dicionario:
                                nomes.append((*match.span(), *dicionario[forma]))
                            else:
                                sugestoes.add((identificador, numero, forma))

                    marcas = sorted(epitetos + [m for m in nomes if not sobrepoe(*m[:2], epitetos)])
                    novas += marcar_verso(verso, marcas)
                if modelo is not None:
                    sugestoes.update(sugerir_novas_entidades(modelo, identificador, numero, estrofe))
            print(f"Canto {identificador}: {novas} marcações novas.")
            total += novas

        if sugestoes:
            print("Ocorrências a conferir:")
            for canto, estrofe, forma in sorted(sugestoes):
                print(f"  Canto {canto}, estrofe {estrofe}: {forma}")

        if any(canto.get("n") == "1" for canto in cantos):
            faltantes = NOMES_REVISADOS.keys() - encontradas
            if faltantes:
                numeros = ", ".join(map(str, sorted({n for n, _ in faltantes})))
                print(f"Atenção: {len(faltantes)} versos de referência divergem. Estrofes: {numeros}.")
                if args.aplicar:
                    raise ValueError("Confira os versos divergentes na prévia antes de aplicar ao Canto I.")

        destino = entrada if args.aplicar else entrada.with_name(entrada.stem + "_previa.xml")
        if args.aplicar and not total:
            print("Nenhuma marcação nova. O arquivo já está atualizado.")
            return

        resultado = etree.tostring(
            arvore, encoding="UTF-8", xml_declaration=original.startswith(b"<?xml")
        )
        resultado += re.search(rb"[ \t\r\n]*\Z", original).group()
        etree.fromstring(resultado, parser)
        salvar(destino, resultado, stat.S_IMODE(entrada.stat().st_mode))
        print(f"{total} marcações novas. XML salvo em {destino}.")
    except (OSError, ValueError, etree.XMLSyntaxError) as erro:
        cli.exit(1, f"Erro: {erro}\n")


if __name__ == "__main__":
    main()
