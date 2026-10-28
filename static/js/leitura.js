/* leitura.js — comportamentos da tela de leitura em colunas.

   1. Estrofe correspondente: ao passar o mouse (ou focar com o teclado) numa
      estrofe, ela e a estrofe de mesmo número na outra coluna são realçadas
      (classe .estrofe--par).
   2. Verso correspondente: ao passar o mouse num verso, ele e o verso de mesma
      posição dentro da estrofe correspondente, na outra coluna, ficam em
      amarelo claro (classe .verso--par), por cima do realce da estrofe.
      Ambos só atuam quando as duas colunas mostram texto.
   3. Realçar diferenças: o botão liga/desliga a classe .mostrar-diferencas no
      .layout (o HTML já traz os <span class="dif">); a escolha é lembrada
      entre visitas (localStorage, se disponível).
   4. Tamanho da letra: botões A− / A+ (e clique no percentual para voltar ao
      padrão); a escolha é lembrada entre visitas.
   5. Alinhamento: com as duas colunas lado a lado, iguala a altura dos títulos,
      das estrofes de mesmo número e dos versos de mesma posição, para que
      cada estrofe (e cada verso) fique na mesma linha nas duas colunas, mesmo
      quando uma edição quebra um verso em duas linhas.
   6. Atalhos: seta ← / → vão para a página anterior / seguinte
      (links com rel="prev" / rel="next" da barra de navegação). */
(function () {
  "use strict";

  var layout = document.querySelector(".lusiadas .layout");
  if (!layout) return;

  // ---------- 1 e 2. estrofe e verso correspondentes ----------
  var realcadas = [];

  function limpar() {
    realcadas.forEach(function (el) { el.classList.remove("estrofe--par", "verso--par"); });
    realcadas = [];
  }

  function marcar(el, classe) {
    el.classList.add(classe);
    realcadas.push(el);
  }

  function posicaoDoVerso(estrofe, verso) {
    return Array.prototype.indexOf.call(estrofe.querySelectorAll(".verso"), verso);
  }

  function realcar(estrofe, verso) {
    limpar();
    var numero = estrofe.getAttribute("data-estrofe");
    if (!numero) return;

    var posicao = verso ? posicaoDoVerso(estrofe, verso) : -1;

    marcar(estrofe, "estrofe--par");
    if (verso) marcar(verso, "verso--par");

    // procura a mesma estrofe (e o mesmo verso) na OUTRA coluna
    var colunaAtual = estrofe.closest(".coluna");
    var colunas = layout.querySelectorAll(".coluna");
    for (var i = 0; i < colunas.length; i++) {
      if (colunas[i] === colunaAtual) continue;
      var par = colunas[i].querySelector('.estrofe[data-estrofe="' + CSS.escape(numero) + '"]');
      if (!par) continue;
      marcar(par, "estrofe--par");
      if (posicao >= 0) {
        var versoPar = par.querySelectorAll(".verso")[posicao];
        if (versoPar) marcar(versoPar, "verso--par");
      }
    }
  }

  layout.addEventListener("mouseover", function (e) {
    if (!e.target.closest) return;
    var estrofe = e.target.closest(".estrofe");
    if (estrofe && layout.contains(estrofe)) realcar(estrofe, e.target.closest(".verso"));
  });

  layout.addEventListener("mouseout", function (e) {
    var estrofe = e.target.closest && e.target.closest(".estrofe");
    if (!estrofe) return;
    if (e.relatedTarget && estrofe.contains(e.relatedTarget)) return; // ainda dentro
    limpar();
  });

  layout.addEventListener("focusin", function (e) {
    var estrofe = e.target.closest && e.target.closest(".estrofe");
    if (estrofe) realcar(estrofe, null);
  });

  layout.addEventListener("focusout", limpar);

  // ---------- 3. realçar diferenças entre versões ----------
  var botaoDif = document.querySelector(".alternar-diferencas");
  if (botaoDif) {
    var CHAVE = "lusiadas:realcar-diferencas";

    function definirDif(ligado) {
      layout.classList.toggle("mostrar-diferencas", ligado);
      botaoDif.setAttribute("aria-pressed", ligado ? "true" : "false");
    }

    var salvo = null;
    try { salvo = window.localStorage.getItem(CHAVE); } catch (err) { /* storage bloqueado */ }
    definirDif(salvo === "1");

    botaoDif.addEventListener("click", function () {
      var ligado = !layout.classList.contains("mostrar-diferencas");
      definirDif(ligado);
      try { window.localStorage.setItem(CHAVE, ligado ? "1" : "0"); } catch (err) { /* ignora */ }
    });
  }

  // ---------- 5. alinhamento entre as colunas ----------
  var lado = window.matchMedia("(min-width: 901px)"); // abaixo disso as colunas se empilham

  function alturaMinima(pares) {
    // lê todas as alturas antes de escrever (evita refluxos repetidos)
    var alturas = pares.map(function (par) {
      return Math.max(par[0].getBoundingClientRect().height, par[1].getBoundingClientRect().height);
    });
    pares.forEach(function (par, i) {
      par[0].style.minHeight = alturas[i] + "px";
      par[1].style.minHeight = alturas[i] + "px";
    });
  }

  function alinhar() {
    layout.querySelectorAll(".conteudo h3, .estrofe, .verso").forEach(function (el) {
      el.style.minHeight = "";
    });
    if (!lado.matches) return;

    var conteudos = layout.querySelectorAll(".coluna .conteudo");
    if (conteudos.length < 2) return;
    var a = conteudos[0], b = conteudos[1];

    var titulos = [], estrofes = [], versos = [];

    // títulos (<h3>), na ordem em que aparecem
    var h3a = a.querySelectorAll("h3"), h3b = b.querySelectorAll("h3");
    for (var i = 0; i < Math.min(h3a.length, h3b.length); i++) titulos.push([h3a[i], h3b[i]]);

    // estrofes de mesmo número e, dentro delas, versos de mesma posição
    var porNumero = {};
    b.querySelectorAll(".estrofe[data-estrofe]").forEach(function (e) {
      var n = e.getAttribute("data-estrofe");
      if (!(n in porNumero)) porNumero[n] = e;
    });
    a.querySelectorAll(".estrofe[data-estrofe]").forEach(function (ea) {
      var eb = porNumero[ea.getAttribute("data-estrofe")];
      if (!eb) return;
      estrofes.push([ea, eb]);
      var va = ea.querySelectorAll(":scope > .verso"), vb = eb.querySelectorAll(":scope > .verso");
      for (var k = 0; k < Math.min(va.length, vb.length); k++) versos.push([va[k], vb[k]]);
    });

    if (!titulos.length && !estrofes.length) return;
    alturaMinima(titulos.concat(versos));  // 1º títulos e versos...
    alturaMinima(estrofes);                // ...depois as estrofes inteiras (nº de versos pode diferir)
  }

  var agendado = false;
  function agendarAlinhamento() {
    if (agendado) return;
    agendado = true;
    window.requestAnimationFrame(function () { agendado = false; alinhar(); });
  }

  window.addEventListener("resize", agendarAlinhamento);
  if (lado.addEventListener) lado.addEventListener("change", agendarAlinhamento);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(agendarAlinhamento);
  window.addEventListener("load", agendarAlinhamento);
  alinhar();

  // ---------- 4. tamanho da letra ----------
  var grupoTamanho = document.querySelector(".tamanho-letra");
  var ESCALAS = [0.85, 1, 1.15, 1.3, 1.5];
  var PADRAO = 1;
  var CHAVE_TAMANHO = "lusiadas:tamanho-letra";
  var indice = PADRAO;

  function definirTamanho(novo) {
    indice = Math.max(0, Math.min(ESCALAS.length - 1, novo));
    layout.style.setProperty("--escala-fonte", ESCALAS[indice]);
    if (grupoTamanho) {
      grupoTamanho.querySelector('[data-acao="padrao"]').textContent = Math.round(ESCALAS[indice] * 100) + "%";
      grupoTamanho.querySelector('[data-acao="diminuir"]').disabled = indice === 0;
      grupoTamanho.querySelector('[data-acao="aumentar"]').disabled = indice === ESCALAS.length - 1;
    }
    agendarAlinhamento();  // linhas quebram em outros pontos, então realinha
  }

  var guardado = null;
  try { guardado = window.localStorage.getItem(CHAVE_TAMANHO); } catch (err) { /* storage bloqueado */ }
  var inicial = parseInt(guardado, 10);
  definirTamanho(isNaN(inicial) ? PADRAO : inicial);

  if (grupoTamanho) {
    grupoTamanho.addEventListener("click", function (e) {
      var botao = e.target.closest("button[data-acao]");
      if (!botao || botao.disabled) return;
      var acao = botao.getAttribute("data-acao");
      definirTamanho(acao === "aumentar" ? indice + 1 : acao === "diminuir" ? indice - 1 : PADRAO);
      try { window.localStorage.setItem(CHAVE_TAMANHO, String(indice)); } catch (err) { /* ignora */ }
    });
  }

  // ---------- 6. setas do teclado ----------
  document.addEventListener("keydown", function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;

    var alvo = e.target;
    var tag = alvo && alvo.tagName;
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || (alvo && alvo.isContentEditable)) return;

    var link = document.querySelector(
      e.key === "ArrowLeft" ? 'a[rel="prev"]' : 'a[rel="next"]'
    );
    if (link) {
      e.preventDefault();
      window.location.href = link.href;
    }
  });
})();
