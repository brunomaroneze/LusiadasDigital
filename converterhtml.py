import xml.etree.ElementTree as ET
import os

# Define os nomes dos arquivos de entrada e saída
INPUT_XML_FILENAME = "LusiadasEsquerda.xml"
OUTPUT_HTML_FILENAME = "lusiadas.html"

# Define o namespace TEI padrão
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"
NAMESPACES = {'tei': TEI_NAMESPACE} # Mapeia um prefixo 'tei' para o URI do namespace

def get_local_tag_name(element_tag):
    """
    Extrai o nome local de uma tag XML, ignorando o namespace se presente.
    Ex: '{http://www.tei-c.org/ns/1.0}div' -> 'div'
        'head' -> 'head'
    """
    if '}' in element_tag:
        return element_tag.split('}', 1)[1]
    return element_tag

def convert_tei_to_html(xml_string):
    """
    Converte uma string XML TEI dos Lusíadas em uma string HTML formatada.
    """
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        return f"<html><body><h1>Erro ao parsear o XML: {e}</h1></body></html>"

    html_lines = []

    # Adiciona a estrutura básica do HTML e CSS para formatação
    html_lines.append("<!DOCTYPE html>")
    html_lines.append("<html lang='pt'>")
    html_lines.append("<head>")
    html_lines.append("    <meta charset='UTF-8'>")
    html_lines.append("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    
    # Para o título, precisamos procurar o primeiro <head> no namespace
    title_element = root.find(f".//tei:head", NAMESPACES)
    title_text = "".join(title_element.itertext()).strip() if title_element is not None else "Os Lusíadas"
    html_lines.append(f"    <title>{title_text}</title>")
    
    html_lines.append("    <style>")
    html_lines.append("        body { font-family: Georgia, serif; line-height: 1.6; max-width: 800px; margin: 20px auto; padding: 0 15px; background-color: #fcfcfc; color: #333; }")
    html_lines.append("        h1, h2 { text-align: center; margin-bottom: 0.5em; }")
    html_lines.append("        h1 { font-size: 2.2em; color: #1a1a1a; margin-top: 1em; }")
    html_lines.append("        h2 { font-size: 1.8em; color: #444; margin-bottom: 1.5em; }")
    html_lines.append("        hr { border: 0; height: 1px; background: #eee; margin: 1.5em 0; }")
    html_lines.append("        .stanza { margin-bottom: 1.5em; /* Garante separação visual entre as estrofes */ }")
    html_lines.append("        .verse { margin: 0; padding: 0; text-indent: -1em; padding-left: 1em; /* Formata para que o texto comece após o número, se houver, e o restante se alinhe */ }")
    html_lines.append("    </style>")
    html_lines.append("</head>")
    html_lines.append("<body>")

    # Encontra o div do canto, AGORA USANDO O NAMESPACE
    canto_div = root.find(f".//tei:div[@type='canto']", NAMESPACES)

    if canto_div is not None:
        # Primeiro, processa os elementos <head> para criar os títulos
        first_head_processed = False
        # Precisa usar o namespace para encontrar 'head' também
        for header_elem in canto_div.findall(f'tei:head', NAMESPACES):
            header_content_parts = []
            
            # Itera sobre os nós dentro do <head>. AQUI ESTÁ A CORREÇÃO.
            for node in header_elem.iter():
                # Usa a função auxiliar para obter o nome local da tag
                local_node_tag = get_local_tag_name(node.tag)
                
                if local_node_tag == 'lb':
                    header_content_parts.append('<br/>')
                elif node.text and node.text.strip():
                    header_content_parts.append(node.text.strip())
                if node.tail and node.tail.strip():
                    header_content_parts.append(node.tail.strip())
            
            full_header_text = "".join(filter(None, header_content_parts))
            full_header_text = full_header_text.replace(" <br/>", "<br/>").replace("<br/> ", "<br/>")

            if not first_head_processed:
                html_lines.append(f"    <h1>{full_header_text}</h1>")
                first_head_processed = True
            else:
                html_lines.append(f"    <h2>{full_header_text}</h2>")
        
        html_lines.append("    <hr/>")

        # Processa os elementos filhos do div do canto
        for element in canto_div:
            # Obtém o nome local da tag do elemento para comparação
            local_element_tag = get_local_tag_name(element.tag)

            if local_element_tag == 'lg':  # Se for uma estrofe
                html_lines.append("    <div class='stanza'>")
                for verse_elem in element.findall(f'tei:l', NAMESPACES): # 'l' também no namespace
                    verse_text = "".join(verse_elem.itertext()).strip()
                    html_lines.append(f"        <p class='verse'>{verse_text}</p>")
                html_lines.append("    </div>")
            # Para 'fw' e 'pb', que são elementos TEI, também seria bom usar o local_element_tag
            elif local_element_tag in ['fw', 'pb', 'head', 'lb']:
                continue
            # Quaisquer outras tags não especificadas serão ignoradas por padrão
    else:
        # Mensagem de erro mais detalhada
        html_lines.append(f"    <p>Erro: Não foi encontrado o div do canto com 'type=\"canto\"' no namespace '{TEI_NAMESPACE}'.</p>")
        html_lines.append(f"    <p>Verifique se o seu arquivo XML ('{INPUT_XML_FILENAME}') utiliza o namespace TEI correto e se o elemento &lt;div type=\"canto\"&gt; está presente e bem formado.</p>")
        html_lines.append(f"    <p>Raiz do XML: {root.tag}, Atributos: {root.attrib}</p>")

    html_lines.append("</body>")
    html_lines.append("</html>")

    return "\n".join(html_lines)

# --- Parte principal do script para ler e escrever arquivos ---
if __name__ == "__main__":
    xml_content = ""
    
    # 1. Tenta ler o arquivo XML
    try:
        with open(INPUT_XML_FILENAME, "r", encoding="utf-8") as f:
            xml_content = f.read()
        print(f"Arquivo '{INPUT_XML_FILENAME}' lido com sucesso.")
    except FileNotFoundError:
        print(f"Erro: O arquivo '{INPUT_XML_FILENAME}' não foi encontrado na pasta atual.")
        print("Certifique-se de que 'LusiadasEsquerda.xml' está na mesma pasta que o script.")
        exit()
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao ler o arquivo XML: {e}")
        exit()

    # 2. Converte o conteúdo XML para HTML
    html_output = convert_tei_to_html(xml_content)

    # 3. Salva o resultado HTML em um arquivo
    try:
        with open(OUTPUT_HTML_FILENAME, "w", encoding="utf-8") as f:
            f.write(html_output)
        print(f"Conversão concluída. HTML salvo em '{OUTPUT_HTML_FILENAME}'.")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo HTML '{OUTPUT_HTML_FILENAME}': {e}")