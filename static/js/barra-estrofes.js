/**
 * barra-estrofes.js

 * Autocontido: cria seu próprio HTML via JS e não exige nenhuma
 * alteração em nav.html, footer.html ou nas páginas de canto.
 
 * Como funciona:
 *  1. Só ativa na tela de leitura (/canto/<n>/ ou /canto/<n>/leitura/...)
 *     -- fora dela, o link "cantos" do menu volta a ser normal.
 *  2. Ao clicar em "selecionar estrofes" no menu, a barra desliza logo
 *     abaixo do nav, com um <select> de canto e um campo de estrofe.
 *  3. Escolher um canto busca o índice estrofe->página
 *     (/canto/<n>/estrofes/) e habilita o campo de número.
 *  4. Confirmar navega para /canto/<n>/?p=<pagina>&estrofe=<n>.
 *  5. O estado (barra aberta / canto escolhido) fica em sessionStorage,
 *     então continua aberta ao trocar de página de leitura.
 */
(function () {
  "use strict";

  function iniciar() {
    var linkCantos = document.querySelector(".links-nav .nav-item");
    if (!linkCantos) {
      return; // página sem a barra de navegação padrão — não faz nada
    }

    
    var ehTelaDeLeitura = /^\/canto\/\d+\/(leitura\/|$)/.test(window.location.pathname);

    if (!ehTelaDeLeitura) {
      linkCantos.textContent = "cantos";
      return; // não cria a barra fora da tela de leitura
    }

    linkCantos.textContent = "selecionar estrofes";

    var nav = document.querySelector(".nav-fixa");
    if (!nav) {
      return; // sem o nav padrão não tem onde ancorar a barra logo abaixo
    }

    var CHAVE_ABERTA = "abaEstrofesAberta";
    var CHAVE_CANTO = "abaEstrofesCanto";

    function escaparHtml(texto) {
      var div = document.createElement("div");
      div.textContent = texto == null ? "" : String(texto);
      return div.innerHTML;
    }

    var barra = document.createElement("div");
    barra.className = "barra-estrofes";
    barra.setAttribute("role", "complementary");
    barra.setAttribute("aria-label", "Selecionar estrofe");
    barra.innerHTML =
      '<div class="barra-estrofes__container">' +
        '<span class="barra-estrofes__rotulo">Selecionar estrofe</span>' +
        '<div class="barra-estrofes__controles">' +
          '<select class="barra-estrofes__canto" aria-label="Canto" disabled></select>' +
          '<input type="number" class="barra-estrofes__input" min="1" ' +
            'placeholder="nº da estrofe" aria-label="Número da estrofe" disabled>' +
          '<button type="button" class="barra-estrofes__ir" disabled>Ir</button>' +
          '<span class="barra-estrofes__status"></span>' +
        "</div>" +
      "</div>";

    // insere logo depois do nav, no fluxo normal do documento — não é
    // posicionamento fixo/flutuante, então empurra o conteúdo abaixo
    // dela ao abrir, sem sobrepor nada.
    nav.insertAdjacentElement("afterend", barra);

    var selectCanto = barra.querySelector(".barra-estrofes__canto");
    var inputEstrofe = barra.querySelector(".barra-estrofes__input");
    var botaoIr = barra.querySelector(".barra-estrofes__ir");
    var status = barra.querySelector(".barra-estrofes__status");

    var indiceAtual = {};
    var cantosCarregados = false;

    function definirStatus(mensagem, ehErro) {
      status.textContent = mensagem || "";
      status.classList.toggle("barra-estrofes__status--erro", !!ehErro);
    }

    function abrirBarra() {
      barra.classList.add("barra-estrofes--aberta");
      try { sessionStorage.setItem(CHAVE_ABERTA, "1"); } catch (e) { /* sem storage disponível */ }
    }

    function fecharBarra() {
      barra.classList.remove("barra-estrofes--aberta");
      try { sessionStorage.setItem(CHAVE_ABERTA, "0"); } catch (e) { /* idem */ }
    }

    function carregarEstrofes(numeroCanto) {
      inputEstrofe.disabled = true;
      botaoIr.disabled = true;
      definirStatus("Carregando estrofes…");
      fetch("/canto/" + encodeURIComponent(numeroCanto) + "/estrofes/?versao=modernizado")
        .then(function (resposta) {
          if (!resposta.ok) throw new Error("resposta não OK");
          return resposta.json();
        })
        .then(function (dados) {
          indiceAtual = (dados && dados.indice) || {};
          var numeros = Object.keys(indiceAtual)
            .map(Number)
            .filter(function (n) { return !isNaN(n); });
          var maxEstrofe = numeros.length ? Math.max.apply(null, numeros) : null;

          if (maxEstrofe) {
            inputEstrofe.max = String(maxEstrofe);
            inputEstrofe.placeholder = "1–" + maxEstrofe;
            inputEstrofe.disabled = false;
            botaoIr.disabled = false;
            definirStatus("");
          } else {
            definirStatus("Este canto ainda não tem estrofes indexadas.", true);
          }
        })
        .catch(function () {
          definirStatus("Não foi possível carregar as estrofes deste canto.", true);
        });
    }

    function carregarCantos(numeroCantoPreferido) {
      selectCanto.disabled = true;
      definirStatus("Carregando cantos…");
      fetch("/cantos/")
        .then(function (resposta) {
          if (!resposta.ok) throw new Error("resposta não OK");
          return resposta.json();
        })
        .then(function (dados) {
          var cantos = (dados && dados.cantos) || [];
          selectCanto.innerHTML = "";

          if (cantos.length === 0) {
            definirStatus("Nenhum canto cadastrado ainda.", true);
            return;
          }

          cantos.forEach(function (c) {
            var opcao = document.createElement("option");
            opcao.value = c.numero;
            opcao.textContent =
              c.titulo && String(c.titulo).trim() ? c.titulo : "Canto " + c.numero;
            selectCanto.appendChild(opcao);
          });
          selectCanto.disabled = false;
          cantosCarregados = true;

          var existeCantoPreferido = cantos.some(function (c) {
            return String(c.numero) === String(numeroCantoPreferido);
          });
          var cantoInicial = existeCantoPreferido ? numeroCantoPreferido : cantos[0].numero;
          selectCanto.value = cantoInicial;
          carregarEstrofes(cantoInicial);
        })
        .catch(function () {
          definirStatus("Não foi possível carregar a lista de cantos.", true);
        });
    }

    function irParaEstrofe() {
      var n = parseInt(inputEstrofe.value, 10);
      if (!n || !Object.prototype.hasOwnProperty.call(indiceAtual, String(n))) {
        definirStatus("Não encontrei essa estrofe. Confira o número.", true);
        return;
      }
      var numeroCanto = selectCanto.value;
      var pagina = indiceAtual[String(n)];
      try { sessionStorage.setItem(CHAVE_CANTO, numeroCanto); } catch (e) { /* ok sem persistir */ }
      window.location.href =
        "/canto/" + encodeURIComponent(numeroCanto) + "/?p=" + encodeURIComponent(pagina) +
        "&estrofe=" + encodeURIComponent(n);
    }

    selectCanto.addEventListener("change", function () {
      carregarEstrofes(selectCanto.value);
    });

    botaoIr.addEventListener("click", irParaEstrofe);
    inputEstrofe.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") irParaEstrofe();
    });

    linkCantos.addEventListener("click", function (ev) {
      ev.preventDefault();
      if (barra.classList.contains("barra-estrofes--aberta")) {
        fecharBarra();
        return;
      }
      abrirBarra();
      if (!cantosCarregados) {
        var cantoSalvo = null;
        try { cantoSalvo = sessionStorage.getItem(CHAVE_CANTO); } catch (e) { /* sem storage */ }
        carregarCantos(cantoSalvo);
      }
    });

    // Mantém a barra aberta ao navegar entre páginas de leitura.
    var estadoAberto = null;
    try { estadoAberto = sessionStorage.getItem(CHAVE_ABERTA); } catch (e) { /* sem storage */ }

    if (estadoAberto === "1") {
      abrirBarra();
      var cantoSalvoInicial = null;
      try { cantoSalvoInicial = sessionStorage.getItem(CHAVE_CANTO); } catch (e) { /* sem storage */ }
      carregarCantos(cantoSalvoInicial);
    }
  }

  // Executa assim que o DOM estiver pronto, não importa se o <script>
  // foi carregado no <head> (com "defer") ou no fim do <body>.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
