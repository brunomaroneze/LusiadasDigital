import spacy
from lxml import etree
import os
import sys

# --- 1. Configuração e Carregamento do spaCy ---
try:
    nlp = spacy.load("pt_core_news_lg")
    print("Modelo spaCy 'pt_core_news_lg' carregado com sucesso.")
except OSError:
    print("Erro: Modelo spaCy 'pt_core_news_lg' não encontrado.")
    print("Por favor, execute: python -m spacy download pt_core_news_lg")
    sys.exit(1)

# Namespace TEI para lxml
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"
ET_NAMESPACE = "{%s}" % TEI_NAMESPACE

def lemmatize_and_tag_tei(input_filepath, output_filepath):
    """
    Lematiza e adiciona categorias gramaticais (POS e MSD) a um arquivo TEI XML,
    usando <w> para palavras e <pc> para pontuação.

    Args:
        input_filepath (str): Caminho para o arquivo XML de entrada (Lusíadas).
        output_filepath (str): Caminho para salvar o arquivo XML processado.
    """
    try:
        # 1. Carregar o arquivo XML
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(input_filepath, parser)
        root = tree.getroot()
        print(f"Arquivo XML '{input_filepath}' carregado.")

        # 2. Encontrar todos os elementos <l> (linha) dentro do corpo do texto
        l_elements = root.findall(f".//{ET_NAMESPACE}l")
        print(f"Encontradas {len(l_elements)} linhas (<l> elementos) para processar.")

        # 3. Iterar sobre cada elemento <l>
        for i, l_elem in enumerate(l_elements):
            original_text = "".join(l_elem.itertext()).strip()

            if not original_text:
                continue

            doc = nlp(original_text)

            l_elem.clear()
            l_elem.text = None

            last_appended_node = None

            for token in doc:
                if token.is_punct:
                    pc_elem = etree.SubElement(l_elem, ET_NAMESPACE + "pc")
                    pc_elem.set("pos", token.pos_)
                    
                    # CORREÇÃO AQUI: Use str(token.morph)
                    morph_str = str(token.morph)
                    if morph_str: # morph_str será uma string vazia se não houver dados morfológicos
                        pc_elem.set("msd", morph_str)
                    
                    pc_elem.text = token.text
                    last_appended_node = pc_elem
                elif token.is_space:
                    space_text = token.text
                    if last_appended_node is not None:
                        last_appended_node.tail = (last_appended_node.tail or "") + space_text
                    else:
                        l_elem.text = (l_elem.text or "") + space_text
                else: # É uma palavra
                    w_elem = etree.SubElement(l_elem, ET_NAMESPACE + "w")
                    w_elem.set("lemma", token.lemma_)
                    w_elem.set("pos", token.pos_)

                    # CORREÇÃO AQUI: Use str(token.morph)
                    morph_str = str(token.morph)
                    if morph_str: # morph_str será uma string vazia se não houver dados morfológicos
                        w_elem.set("msd", morph_str)

                    w_elem.text = token.text
                    last_appended_node = w_elem

                if token.whitespace_:
                    if last_appended_node is not None:
                        last_appended_node.tail = (last_appended_node.tail or "") + token.whitespace_
                    elif l_elem.text is None and len(l_elem) == 0:
                         l_elem.text = (l_elem.text or "") + token.whitespace_

            if (i + 1) % 100 == 0:
                print(f"Processadas {i + 1} linhas...")

        # 4. Salvar o arquivo XML modificado
        tree_string = etree.tostring(
            tree,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8"
        ).decode("utf-8")

        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(tree_string)

        print(f"Processamento concluído. Arquivo salvo em '{output_filepath}'")

    except etree.XMLSyntaxError as e:
        print(f"Erro de sintaxe XML: {e}")
    except FileNotFoundError:
        print(f"Erro: Arquivo '{input_filepath}' não encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

# --- Uso do script ---
if __name__ == "__main__":
    # O conteúdo e arquivos de teste permanecem os mesmos
    input_file = "LusiadasModernizado.xml"
    output_file = "LusiadasModernizadoLematizado.xml"

    lemmatize_and_tag_tei(input_file, output_file)

    print("\n--- Verificando o resultado da primeira linha com <pc> ---")
    try:
        tree = etree.parse(output_file)
        root = tree.getroot()
        first_l = root.find(f".//{ET_NAMESPACE}l")
        if first_l is not None:
            print(etree.tostring(first_l, pretty_print=True, encoding="utf-8").decode("utf-8"))
        else:
            print("Nenhum elemento <l> encontrado no arquivo de saída.")
    except Exception as e:
        print(f"Erro ao verificar o arquivo de saída: {e}")