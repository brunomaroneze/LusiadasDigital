# LusiadasDigital
Esta pasta reúne os arquivos do projeto Lusíadas Digital.

Versão 0.1.0 - Primeiro teste para exibição.

Versão 0.1.1 - Inclusão das imagens das páginas.
## Autoridades da edição modernizada

`autoridades.xml` reúne as fichas de pessoas, personagens mitológicos e lugares.
As ocorrências em `LusiadasModernizado.xml` usam, por exemplo,
`ref="autoridades.xml#jupiter"` para apontar para a ficha com
`xml:id="jupiter"`. As edições direita e esquerda não usam esse catálogo.

- Para ampliar uma ficha, acrescente uma nota, imagem ou coordenada à entrada
  correspondente e preserve seu `xml:id`.
- Para uma entidade nova, crie uma entrada em `listPerson` ou `listPlace` com
  um `xml:id` único. Reutilize esse identificador em todas as ocorrências.
- Para reconhecer automaticamente uma nova forma, acrescente-a ao dicionário
  em `marcar_os_lusiadas10.py`, com o mesmo identificador da ficha. O script
  usa o catálogo como destino dos vínculos, e o reconhecimento segue suas
  regras de marcação.
- Na raiz do repositório, execute
  `python3 marcar_os_lusiadas10.py LusiadasTextos/LusiadasModernizado.xml --canto 2`
  para gerar uma prévia do processamento do Canto II. Confira as ocorrências
  ambíguas no terminal e os vínculos no XML antes de aplicar mudanças.
- Valide a edição modernizada com `tei_Lusiadas.rng`. O catálogo é um documento
  TEI separado, organizado em `standOff`, e pode ser validado com o esquema
  geral TEI P5 (`tei_all.rng`). Confira também se cada fragmento depois
  de `autoridades.xml#` corresponde a um `xml:id` no catálogo.
