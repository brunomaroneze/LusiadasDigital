from lxml import etree
import re
from difflib import SequenceMatcher

# --- Adicione a definição do namespace XML aqui ---
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0" # Definindo o namespace TEI

# --- Funções de Pré-processamento (mantidas inalteradas) ---
def preprocess_old_version_l(l_element):
    full_text_parts = []
    
    if l_element.text:
        full_text_parts.append(l_element.text)
    
    for child in l_element:
        child_tag_local = child.tag.split('}')[-1]
        if child_tag_local == 'lb' and child.get('break') == 'no':
            if child.tail:
                full_text_parts.append(child.tail)
        else:
            if child.tail:
                if full_text_parts and not re.match(r'[\s\-.,:;?!&]$', full_text_parts[-1]):
                    full_text_parts.append(" ")
                full_text_parts.append(child.tail)

    full_line_text = "".join(full_text_parts).strip()
    
    full_line_text = full_line_text.replace('&amp;', '&')

    tokens = []
    for match_str in re.findall(r"([^\s.,:;?!&]+|[.,:;?!&])", full_line_text):
        if match_str:
            is_punct = bool(re.match(r"[.,:;?!&]", match_str))
            original_text = match_str
            comparable_text = original_text.lower()
            
            if original_text == '&':
                comparable_text = 'e'
            
            tokens.append((original_text, comparable_text, is_punct))
        
    return tokens

def preprocess_modern_l(l_element):
    tokens = []
    for child in l_element.xpath('./tei:w | ./tei:pc', namespaces={'tei': TEI_NAMESPACE}):
        tag = child.tag.split('}')[-1]
        original_text = child.text
        comparable_text = original_text.lower()
        is_punct = (tag == 'pc')
        attrs = child.attrib
        tokens.append((tag, original_text, comparable_text, is_punct, attrs))
    return tokens

def _align_target_to_base(base_tokens_full, target_tokens_full, base_comparable, target_comparable):
    matcher = SequenceMatcher(None, base_comparable, target_comparable)
    
    aligned_target = [None] * len(base_comparable)
    insertions_before_base_idx = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                aligned_target[i1 + k] = target_tokens_full[j1 + k]
        elif tag == 'replace':
            len_base_block = i2 - i1
            len_target_block = j2 - j1
            
            for k in range(len_base_block):
                if k < len_target_block:
                    aligned_target[i1 + k] = target_tokens_full[j1 + k]
            
            if len_target_block > len_base_block:
                insertions_before_base_idx.append((i2, target_tokens_full[j1 + len_base_block:j2]))
        elif tag == 'insert':
            insertions_before_base_idx.append((i1, target_tokens_full[j1:j2]))

    return aligned_target, insertions_before_base_idx

# --- Função Principal de Colação (mantida inalterada) ---
def collate_lus(modern_xml_path, vesq_xml_path, vdir_xml_path):
    parser = etree.XMLParser(remove_blank_text=True) 
    
    tree_mod = etree.parse(modern_xml_path, parser)
    tree_vesq = etree.parse(vesq_xml_path, parser)
    tree_vdir = etree.parse(vdir_xml_path, parser)

    root_mod = tree_mod.getroot()
    root_vesq = tree_vesq.getroot()
    root_vdir = tree_vdir.getroot()

    wit_ids = {
        'VMod': '#VMod',
        'VEsq': '#VEsq',
        'VDir': '#VDir'
    }
    
    tei_root = etree.Element('{'+TEI_NAMESPACE+'}TEI', nsmap={'tei': TEI_NAMESPACE, 'xml': XML_NAMESPACE})
    text_elem = etree.SubElement(tei_root, '{'+TEI_NAMESPACE+'}text')
    collated_body = etree.SubElement(text_elem, '{'+TEI_NAMESPACE+'}body')

    namespaces = {'tei': TEI_NAMESPACE}

    canto1_mod = root_mod.xpath('//tei:div[@type="canto" and @n="1"]', namespaces=namespaces)
    canto1_vesq = root_vesq.xpath('//tei:div[@type="canto" and @n="1"]', namespaces=namespaces)
    canto1_vdir = root_vdir.xpath('//tei:div[@type="canto" and @n="1"]', namespaces=namespaces)

    if not canto1_mod or not canto1_vesq or not canto1_vdir:
        raise ValueError("Não foi possível encontrar o Canto 1 em uma ou mais versões. Verifique os caminhos e o XML.")

    canto1_mod = canto1_mod[0]
    canto1_vesq = canto1_vesq[0]
    canto1_vdir = canto1_vdir[0]
    
    collated_div = etree.SubElement(collated_body, '{'+TEI_NAMESPACE+'}div', type='canto', n='1')
    
    head_elements_mod = canto1_mod.xpath('./tei:head', namespaces=namespaces)
    if head_elements_mod:
        canto_head_text = head_elements_mod[-1].text
        new_head = etree.SubElement(collated_div, '{'+TEI_NAMESPACE+'}head')
        new_head.text = canto_head_text
    
    estrofes_mod = canto1_mod.xpath('./tei:lg[@type="estrofe"]', namespaces=namespaces)
    estrofes_vesq = canto1_vesq.xpath('./tei:lg[@type="estrofe"]', namespaces=namespaces)
    estrofes_vdir = canto1_vdir.xpath('./tei:lg[@type="estrofe"]', namespaces=namespaces)

    if not estrofes_mod or not estrofes_vesq or not estrofes_vdir:
        raise ValueError("Não foi possível encontrar estrofes em uma ou mais versões do Canto 1.")

    max_estrofes = max(len(estrofes_mod), len(estrofes_vesq), len(estrofes_vdir))

    for i in range(max_estrofes):
        estrofe_mod = estrofes_mod[i] if i < len(estrofes_mod) else None
        estrofe_vesq = estrofes_vesq[i] if i < len(estrofes_vesq) else None
        estrofe_vdir = estrofes_vdir[i] if i < len(estrofes_vdir) else None

        estrofe_n = estrofe_mod.get('n') if estrofe_mod is not None else \
                    (estrofe_vesq.get('n') if estrofe_vesq is not None else (estrofe_vdir.get('n') if estrofe_vdir is not None else None))
        
        if estrofe_n is None: continue

        collated_lg = etree.SubElement(collated_div, '{'+TEI_NAMESPACE+'}lg', type='estrofe', n=estrofe_n)

        versos_mod = estrofe_mod.xpath('./tei:l', namespaces=namespaces) if estrofe_mod is not None else []
        versos_vesq = estrofe_vesq.xpath('./tei:l', namespaces=namespaces) if estrofe_vesq is not None else []
        versos_vdir = estrofe_vdir.xpath('./tei:l', namespaces=namespaces) if estrofe_vdir is not None else []
        
        max_lines = max(len(versos_mod), len(versos_vesq), len(versos_vdir))

        for j in range(max_lines):
            l_mod = versos_mod[j] if j < len(versos_mod) else None
            l_vesq = versos_vesq[j] if j < len(versos_vesq) else None
            l_vdir = versos_vdir[j] if j < len(versos_vdir) else None

            tokens_mod_full = preprocess_modern_l(l_mod) if l_mod is not None else []
            tokens_vesq_full = preprocess_old_version_l(l_vesq) if l_vesq is not None else []
            tokens_vdir_full = preprocess_old_version_l(l_vdir) if l_vdir is not None else []

            collated_l = collate_line(tokens_mod_full, tokens_vesq_full, tokens_vdir_full, wit_ids)
            collated_lg.append(collated_l)

    tei_header = etree.SubElement(tei_root, '{'+TEI_NAMESPACE+'}teiHeader')
    file_desc = etree.SubElement(tei_header, '{'+TEI_NAMESPACE+'}fileDesc')
    title_stmt = etree.SubElement(file_desc, '{'+TEI_NAMESPACE+'}titleStmt')
    etree.SubElement(title_stmt, '{'+TEI_NAMESPACE+'}title').text = 'Os Lusíadas Colacionado (VMod, VEsq, VDir)'
    publication_stmt = etree.SubElement(file_desc, '{'+TEI_NAMESPACE+'}publicationStmt')
    etree.SubElement(publication_stmt, '{'+TEI_NAMESPACE+'}p').text = 'Colação automatizada.'
    
    profile_desc = etree.SubElement(tei_header, '{'+TEI_NAMESPACE+'}profileDesc')
    partic_desc = etree.SubElement(profile_desc, '{'+TEI_NAMESPACE+'}particDesc')

    for wit_key, wit_uri in wit_ids.items():
        person = etree.SubElement(partic_desc, '{'+TEI_NAMESPACE+'}person', {etree.QName(XML_NAMESPACE, "id"): wit_key.lstrip('#')})
        etree.SubElement(person, '{'+TEI_NAMESPACE+'}persName').text = f'Versão {wit_key.lstrip("#")}'

    return etree.tostring(tei_root, pretty_print=True, encoding='utf-8', xml_declaration=True).decode('utf-8')

# --- collate_line (MODIFICADA para inserções de pontuação) ---
def collate_line(tokens_mod_full, tokens_vesq_full, tokens_vdir_full, wit_ids):
    """
    Cola os tokens de um único verso, aninhando <app> dentro de <w> para palavras
    e dentro de <pc> para pontuação quando há variação ou inserção.
    """
    collated_l = etree.Element('{'+TEI_NAMESPACE+'}l')

    mod_comparable = [t[2] for t in tokens_mod_full]
    esq_comparable = [t[1] for t in tokens_vesq_full]
    dir_comparable = [t[1] for t in tokens_vdir_full]

    aligned_esq_to_mod, esq_inserts = _align_target_to_base(tokens_mod_full, tokens_vesq_full, mod_comparable, esq_comparable)
    aligned_dir_to_mod, dir_inserts = _align_target_to_base(tokens_mod_full, tokens_vdir_full, mod_comparable, dir_comparable)

    all_inserts_data = []
    for base_idx, ins_tokens in esq_inserts:
        all_inserts_data.append((base_idx, 'VEsq', ins_tokens))
    for base_idx, ins_tokens in dir_inserts:
        all_inserts_data.append((base_idx, 'VDir', ins_tokens))
    all_inserts_data.sort(key=lambda x: x[0])

    insert_ptr = 0

    for mod_idx in range(len(tokens_mod_full) + 1):
        # Processar inserções que devem ocorrer ANTES ou NO PONTO do token VMod atual
        current_insert_blocks = {} # {source_wit: list_of_inserted_token_full_data}
        while insert_ptr < len(all_inserts_data) and all_inserts_data[insert_ptr][0] == mod_idx:
            _, source_wit, inserted_tokens_full_data = all_inserts_data[insert_ptr]
            current_insert_blocks.setdefault(source_wit, []).extend(inserted_tokens_full_data) # Armazena dados completos do token
            insert_ptr += 1

        if current_insert_blocks:
            # Verificar se TODAS as inserções neste bloco são APENAS pontuação
            is_pure_punctuation_insert = True
            for wit_tokens in current_insert_blocks.values():
                for token_data in wit_tokens:
                    if not token_data[2]: # token_data[2] é 'is_punct'
                        is_pure_punctuation_insert = False
                        break
                if not is_pure_punctuation_insert:
                    break

            parent_for_app_insert = collated_l
            if is_pure_punctuation_insert:
                # Se for só pontuação, criar um <pc> wrapper
                wrapper_pc = etree.Element('{'+TEI_NAMESPACE+'}pc')
                collated_l.append(wrapper_pc)
                parent_for_app_insert = wrapper_pc
            
            app = etree.SubElement(parent_for_app_insert, '{'+TEI_NAMESPACE+'}app')
            rdg_mod_empty = etree.SubElement(app, '{'+TEI_NAMESPACE+'}rdg', wit=wit_ids['VMod'])
            
            grouped_insert_rdgs = {}
            if 'VEsq' in current_insert_blocks:
                # Join original_text from full token data
                text = " ".join([t[0] for t in current_insert_blocks['VEsq']])
                grouped_insert_rdgs.setdefault(text, []).append(wit_ids['VEsq'])
            if 'VDir' in current_insert_blocks:
                text = " ".join([t[0] for t in current_insert_blocks['VDir']])
                grouped_insert_rdgs.setdefault(text, []).append(wit_ids['VDir'])
            
            for text_val, wits_list in grouped_insert_rdgs.items():
                rdg = etree.SubElement(app, '{'+TEI_NAMESPACE+'}rdg', wit=" ".join(wits_list))
                rdg.text = text_val


        if mod_idx < len(tokens_mod_full):
            mod_token = tokens_mod_full[mod_idx]
            esq_token = aligned_esq_to_mod[mod_idx]
            dir_token = aligned_dir_to_mod[mod_idx]

            mod_original_text = mod_token[1]
            esq_original_text = esq_token[0] if esq_token else None
            dir_original_text = dir_token[0] if dir_token else None

            mod_tag = mod_token[0]
            mod_attrs = mod_token[4]

            if (esq_original_text is not None and dir_original_text is not None and
                mod_original_text == esq_original_text and 
                mod_original_text == dir_original_text):
                
                elem = etree.Element('{'+TEI_NAMESPACE+'}' + mod_tag, mod_attrs)
                elem.text = mod_original_text
                collated_l.append(elem)
            else:
                parent_for_app = collated_l
                
                if mod_tag == 'w':
                    wrapper_w = etree.Element('{'+TEI_NAMESPACE+'}w', mod_attrs)
                    collated_l.append(wrapper_w)
                    parent_for_app = wrapper_w
                elif mod_tag == 'pc':
                    wrapper_pc = etree.Element('{'+TEI_NAMESPACE+'}pc')
                    collated_l.append(wrapper_pc)
                    parent_for_app = wrapper_pc
                
                app = etree.SubElement(parent_for_app, '{'+TEI_NAMESPACE+'}app')

                readings_data = {
                    wit_ids['VMod']: mod_original_text,
                    wit_ids['VEsq']: esq_original_text,
                    wit_ids['VDir']: dir_original_text
                }

                grouped_rdgs = {}
                for wit_id, text in readings_data.items():
                    grouped_rdgs.setdefault(text, []).append(wit_id)

                ordered_keys = sorted(grouped_rdgs.keys(), 
                                      key=lambda k: 0 if wit_ids['VMod'] in grouped_rdgs[k] else 1)
                
                for key in ordered_keys:
                    wits_list = grouped_rdgs[key]
                    rdg = etree.SubElement(app, '{'+TEI_NAMESPACE+'}rdg', wit=" ".join(sorted(wits_list)))
                    if key is not None:
                        rdg.text = key

    return collated_l

# --- Exemplo de Uso (mantido inalterado) ---
modern_file_path = 'LusiadasModernizadoLematizado.xml'
vesq_file_path = 'LusiadasEsquerda.xml'
vdir_file_path = 'LusiadasDireita.xml'

collated_xml = collate_lus(modern_file_path, vesq_file_path, vdir_file_path)

print(collated_xml)

output_file_path = 'lus_collated_full.xml'
with open(output_file_path, 'w', encoding='utf-8') as f:
    f.write(collated_xml)
print(f"\nXML colacionado salvo em '{output_file_path}'")