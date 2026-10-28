from django.test import TestCase
from django.urls import reverse

from .models import Canto, PaginaTexto
from .utils.tei import tei_para_html, tei_para_html_comparado


def tei(*estrofes):
    """Monta um TEI mínimo. Cada estrofe é (numero, [versos em XML])."""
    lgs = "".join(
        f'<lg n="{n}">' + "".join(f"<l>{v}</l>" for v in versos) + "</lg>"
        for n, versos in estrofes
    )
    return f'<div type="canto" n="1">{lgs}</div>'


class DiferencasTests(TestCase):
    def comparar(self, a, b):
        return tei_para_html_comparado(tei((1, [a])), tei((1, [b])))

    def test_palavra_diferente_e_marcada_nos_dois_lados(self):
        html_a, html_b, total = self.comparar("edificáram novo Reino", "edificarão novo Reino")
        self.assertEqual(total, 1)
        self.assertIn('<span class="dif">edificáram</span> novo Reino', html_a)
        self.assertIn('<span class="dif">edificarão</span> novo Reino', html_b)

    def test_versos_iguais_nao_recebem_marcacao(self):
        html_a, html_b, total = self.comparar("As armas e os barões", "As armas e os barões")
        self.assertEqual(total, 0)
        self.assertNotIn("dif", html_a + html_b)

    def test_so_pontuacao_e_nivel_leve(self):
        html_a, html_b, _ = self.comparar("força humana:", "força humana.")
        self.assertIn('<span class="dif dif--leve">:</span>', html_a)
        self.assertIn('<span class="dif dif--leve">.</span>', html_b)

    def test_hifenizacao_e_nivel_leve(self):
        html_a, html_b, _ = self.comparar("praya Lusi-tana,", "praya Lusitana,")
        self.assertIn("dif--leve", html_a)
        self.assertIn("dif--leve", html_b)
        self.assertNotIn('class="dif"', html_a + html_b)

    def test_palavra_a_mais_marca_so_o_lado_que_a_tem(self):
        html_a, html_b, total = self.comparar("E entre gente remota", "entre gente remota")
        self.assertEqual(total, 1)
        self.assertIn('<span class="dif">E</span>', html_a)
        self.assertNotIn("dif", html_b)

    def test_quebra_de_linha_lb_e_preservada(self):
        html_a, html_b, _ = self.comparar('os ba-<lb break="no"/>rões novos', "os barões velhos")
        self.assertIn("<br>", html_a)  # <lb/> continua virando <br>
        # "ba-" + <lb/> + "rões" x "barões": só hifenização, nível leve, nos dois pedaços
        self.assertIn('<span class="dif dif--leve">ba-</span><br><span class="dif dif--leve">rões</span>', html_a)
        self.assertIn('<span class="dif">novos</span>', html_a)
        self.assertIn('<span class="dif">velhos</span>', html_b)

    def test_estrofes_sao_pareadas_pelo_numero_e_versos_pela_posicao(self):
        a = tei((1, ["um", "dois"]), (2, ["tres", "quatro"]))
        b = tei((2, ["tres", "QUATRO"]), (1, ["um", "dois"]))  # ordem trocada
        html_a, html_b, total = tei_para_html_comparado(a, b)
        self.assertEqual(total, 1)
        self.assertIn('<span class="dif">quatro</span>', html_a)
        self.assertIn('<span class="dif">QUATRO</span>', html_b)

    def test_estrofe_sem_par_nao_quebra(self):
        a = tei((1, ["um"]), (2, ["dois"]))
        b = tei((1, ["um"]))
        _, _, total = tei_para_html_comparado(a, b)
        self.assertEqual(total, 0)

    def test_html_continua_com_estrutura_de_estrofe_e_verso(self):
        html_a, _, _ = self.comparar("um dois", "um tres")
        self.assertIn('class="estrofe"', html_a)
        self.assertIn('data-estrofe="1"', html_a)
        self.assertIn('class="verso"', html_a)

    def test_xml_invalido_nao_levanta_excecao(self):
        html_a, html_b, total = tei_para_html_comparado("<lg>", tei((1, ["ok"])))
        self.assertIn("aviso-erro", html_a)
        self.assertEqual(total, 0)

    def test_sem_comparacao_html_e_igual_ao_de_antes(self):
        xml = tei((1, ["um dois"]))
        self.assertEqual(tei_para_html(xml), tei_para_html_comparado(xml, xml)[0])


class LeituraViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        canto = Canto.objects.create(numero=1, titulo="Canto Primeiro")
        PaginaTexto.objects.create(canto=canto, numero=1, versao="original_a", tei_xml=tei((1, ["praya Lusi-tana"])))
        PaginaTexto.objects.create(canto=canto, numero=1, versao="original_b", tei_xml=tei((1, ["praia Lusitana"])))

    def url(self, esq, dir):
        return reverse("leitura", args=[1, esq, "esq"]) + f"?p=1&dir={dir}"

    def test_duas_versoes_mostram_botao_e_contagem(self):
        r = self.client.get(self.url("original_a", "original_b"))
        self.assertContains(r, "alternar-diferencas")
        self.assertContains(r, 'class="dif')
        self.assertTrue(r.context["pode_comparar"])

    def test_mesma_versao_nos_dois_lados_nao_compara(self):
        r = self.client.get(self.url("original_a", "original_a"))
        self.assertNotContains(r, "alternar-diferencas")
        self.assertFalse(r.context["pode_comparar"])

    def test_coluna_de_imagem_nao_compara(self):
        r = self.client.get(self.url("original_a", "imagem_a"))
        self.assertNotContains(r, "alternar-diferencas")


# ---------------------------------------------------------------------------
# Importação de todos os cantos + relatório de integridade
# ---------------------------------------------------------------------------
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from lxml import etree

from .utils.importacao import ESTROFES_ESPERADAS, carregar_xml, verificar_integridade


def estrofe_xml(n, versos=8, texto="verso"):
    ls = "".join(f"<l>{texto} {n}.{i}</l>" for i in range(1, versos + 1))
    return f'<lg type="estrofe" n="{n}">{ls}</lg>'


def arquivo_tei(pasta, nome, cantos):
    """cantos: lista de (n_do_atributo, [estrofes em XML])."""
    divs = "".join(
        f'<div type="canto" n="{n}"><head>Canto {n}</head>{"".join(estrofes)}</div>'
        for n, estrofes in cantos
    )
    caminho = Path(pasta) / nome
    caminho.write_text(f'<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>{divs}</body></text></TEI>', encoding="utf-8")
    return caminho


class IntegridadeTests(TestCase):
    def verificar(self, cantos, esperados=None):
        with tempfile.TemporaryDirectory() as pasta:
            root = carregar_xml(arquivo_tei(pasta, "t.xml", cantos))
        return verificar_integridade(root, esperados or {1: 2, 2: 2})

    def mensagens(self, problemas):
        return " | ".join(str(p) for p in problemas)

    def test_arquivo_sem_problemas(self):
        problemas = self.verificar([("1", [estrofe_xml(1), estrofe_xml(2)]), ("2", [estrofe_xml(1), estrofe_xml(2)])])
        self.assertEqual(problemas, [])

    def test_canto_com_n_errado_e_apontado(self):
        problemas = self.verificar([("1", [estrofe_xml(1), estrofe_xml(2)]), ("8", [estrofe_xml(1), estrofe_xml(2)])])
        self.assertIn('posição 2 está marcado n="8"', self.mensagens(problemas))

    def test_estrofes_com_1_7_e_9_versos(self):
        problemas = self.verificar([
            ("1", [estrofe_xml(1, 1), estrofe_xml(2, 9)]),
            ("2", [estrofe_xml(1, 7), estrofe_xml(2)]),
        ])
        texto = self.mensagens(problemas)
        self.assertIn("estrofe 1 tem 1 verso(s)", texto)
        self.assertIn("fragmento", texto)  # dica para estrofe de 1 verso
        self.assertIn("estrofe 2 tem 9 verso(s)", texto)
        self.assertIn("estrofe 1 tem 7 verso(s)", texto)

    def test_numeracao_repetida_e_com_lacuna(self):
        problemas = self.verificar([("1", [estrofe_xml(1), estrofe_xml(3), estrofe_xml(3)]), ("2", [estrofe_xml(1), estrofe_xml(2)])])
        texto = self.mensagens(problemas)
        self.assertIn("repetido: 3 aparece 2 vezes", texto)
        self.assertIn("falta(m) 2", texto)
        self.assertIn("3 estrofes (esperado: 2)", texto)

    def test_arquivo_parcial_e_informativo(self):
        problemas = self.verificar([("1", [estrofe_xml(1), estrofe_xml(2)])])
        self.assertTrue(any(p.nivel == "INFO" and "arquivo parcial" in p.mensagem for p in problemas))
        self.assertFalse(any(p.nivel == "ERRO" for p in problemas))


class ImportarTudoTests(TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        dois = [estrofe_xml(1), estrofe_xml(2), estrofe_xml(3)]
        arquivo_tei(self.pasta.name, "LusiadasModernizado.xml", [("1", dois), ("2", dois)])
        arquivo_tei(self.pasta.name, "LusiadasEsquerda.xml", [("1", dois)])          # parcial
        arquivo_tei(self.pasta.name, "LusiadasDireita.xml", [("1", dois), ("8", dois)])  # 2º canto com n errado

    def rodar(self, *extra):
        saida = StringIO()
        call_command("importar_tudo", "--pasta", self.pasta.name, "--cantos", "1", "2", *extra, stdout=saida)
        return saida.getvalue()

    def test_importa_as_tres_versoes_usando_a_posicao_do_canto(self):
        saida = self.rodar()
        self.assertEqual(Canto.objects.count(), 2)
        self.assertEqual(PaginaTexto.objects.filter(versao="modernizado").count(), 4)  # 2 cantos x 2 págs
        self.assertEqual(PaginaTexto.objects.filter(versao="original_a").count(), 2)   # só o canto 1
        # o <div n="8"> do arquivo B foi gravado como canto 2
        self.assertTrue(PaginaTexto.objects.filter(versao="original_b", canto__numero=2).exists())
        self.assertFalse(Canto.objects.filter(numero=8).exists())
        self.assertIn('marcado n="8"', saida)

    def test_so_relatorio_nao_grava_nada(self):
        saida = self.rodar("--so-relatorio")
        self.assertEqual(PaginaTexto.objects.count(), 0)
        self.assertIn("nada foi gravado", saida)

    def test_rodar_de_novo_atualiza_sem_duplicar(self):
        self.rodar()
        total = PaginaTexto.objects.count()
        self.rodar()
        self.assertEqual(PaginaTexto.objects.count(), total)

    def test_relatorio_pode_ser_salvo_em_arquivo(self):
        destino = Path(self.pasta.name) / "relatorio.txt"
        self.rodar("--so-relatorio", "--relatorio", str(destino))
        self.assertIn("LusiadasDireita.xml", destino.read_text(encoding="utf-8"))

    def test_importar_canto_continua_funcionando(self):
        caminho = Path(self.pasta.name) / "LusiadasModernizado.xml"
        call_command("importar_canto", "1", str(caminho), "--versao", "modernizado", stdout=StringIO())
        self.assertEqual(PaginaTexto.objects.filter(canto__numero=1, versao="modernizado").count(), 2)
