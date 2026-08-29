## ALTERAÇÕES 08/02/2025

- Primeira etapa de integração TEI-XML → HTML. Ainda exploratório, sem impacto no fluxo atual
- A ideia é que os textos possam ser inseridos por meio de Editor no Django Admin
- Para saber melhor: https://github.com/Suthiery/LusiadasDigital/tree/feature/tei-editor

## ALTERAÇÕES 20/12/2025

## CSS

- o CSS das páginas foi migrado para arquivos .css dentro do diretório static > css
- cada página tem seu .css, porém, quando o estilo era igual em todas as páginas eu coloquei em style.css pra não ficar repetido

## BLOCOS HTML

- substitui partes do código html que são iguais em todas as páginas por template tags (essas marcações {%})
- São estes: Head (cabeçalho), Header (ou hero), Nav (menu de navegação do topo da página) e Footer (rodapé)
- Para propósito de edição, o html se encontra no diretório templates > blocos

## IMAGENS

- as imagens foram migradas para o diretório images em seus respectivos diretório

## ALTERAÇÕES 19/08/2026

### Correções Recentes

- **Bug de Troca de Colunas:** Resolvido o problema onde a alteração de versão em uma coluna afetava a outra. Os arquivos isolados foram substituídos por um template unificado (`partials/texto.html`) que recebe o conteúdo dinamicamente por parâmetro.
- **Prevenção de Erro 500 (TEI-XML):** Implementado tratamento de erro (`try/except`) no parser do XML. Agora, em vez de derrubar a aplicação, um XML malformado no banco de dados exibe um aviso amigável na interface.
- **Tratamento de Erro 404 (URLs):** Adicionada validação estrita de parâmetros na _view_ de leitura. O sistema agora retorna corretamente um erro 404 (Página Não Encontrada) caso receba atributos inválidos na URL.
