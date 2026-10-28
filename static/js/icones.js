/* icones.js — substitui a biblioteca Lucide (≈450 KB, carregada de um CDN em
   todas as páginas) por um script local de ~1 KB.

   Só implementa o que o site usa: <i data-lucide="nome"> vira o <svg> inline
   correspondente e window.lucide.createIcons() continua existindo, então o
   código do rodapé não precisa mudar. Ícones fora da lista abaixo são
   ignorados (mesmo comportamento da Lucide atual para facebook/instagram/
   twitter, que foram removidos da biblioteca).

   Para usar um ícone novo: copie o conteúdo do SVG em lucide.dev e
   acrescente em ICONES. Caminhos da Lucide v1.61.0 (licença ISC). */
(function () {
  var NS = "http://www.w3.org/2000/svg";
  var ICONES = {
    "map-pin":
      '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
    "message-circle":
      '<path d="M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719"/>',
    "arrow-up": '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>'
  };

  window.lucide = {
    createIcons: function () {
      var alvos = document.querySelectorAll("[data-lucide]");
      for (var i = 0; i < alvos.length; i++) {
        var el = alvos[i];
        var nome = el.getAttribute("data-lucide");
        if (!ICONES[nome]) continue;

        var svg = document.createElementNS(NS, "svg");
        svg.setAttribute("xmlns", NS);
        svg.setAttribute("width", el.getAttribute("width") || "24");
        svg.setAttribute("height", el.getAttribute("height") || "24");
        svg.setAttribute("viewBox", "0 0 24 24");
        svg.setAttribute("fill", "none");
        svg.setAttribute("stroke", "currentColor");
        svg.setAttribute("stroke-width", "2");
        svg.setAttribute("stroke-linecap", "round");
        svg.setAttribute("stroke-linejoin", "round");
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("class", ("lucide lucide-" + nome + " " + (el.getAttribute("class") || "")).trim());
        svg.innerHTML = ICONES[nome];
        el.parentNode.replaceChild(svg, el);
      }
    }
  };
})();
