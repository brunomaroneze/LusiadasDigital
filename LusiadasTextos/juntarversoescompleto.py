from lxml import etree
import re
from difflib import SequenceMatcher

# --- Adicione a definição do namespace XML aqui ---
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0" # Definindo o namespace TEI

# --- 1. Funções de Pré-processamento (mantidas inalteradas) ---
def preprocess_old_version_l(l_element):
    """
    Extrai o texto de um elemento <l> de uma versão antiga,
    tratando <lb break="no"/> e tokenizando em palavras e pontuação.
    Retorna uma lista de tuplas (original_text, comparable_text, is_punct, tag, attrs).
    """
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
            original_text = match_str
            comparable_text = original_text.lower()
            attrs = {}
            
            if original_text == '&':
                is_punct = False
                tag = 'w'
                comparable_text = 'e'
                attrs = {'lemma': 'e', 'pos': 'CCONJ'}
            else:
                is_punct = bool(re.match(r"[.,:;?!&]", original_text))
                tag = 'pc' if is_punct else 'w'
            
            tokens.append((original_text, comparable_text, is_punct, tag, attrs))
        
    return tokens

def preprocess_modern_l(l_element):
    """
    Extrai tokens de um elemento <l> da versão modernizada.
    Retorna uma lista de tuplas (tag, original_text, comparable_text, is_punct, attrs).
    """
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

# --- 2. Função Principal de Colação (mantida inalterada, exceto correção de typo) ---
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
    title_stmt = etree.SubElement(file_desc, '{'+TEI_NAMESPACE+'}titleStmt') # Correção do typo: file_header para file_desc
    etree.SubElement(title_stmt, '{'+TEI_NAMESPACE+'}title').text = 'Os Lusíadas Colacionado (VMod, VEsq, VDir)'
    publication_stmt = etree.SubElement(file_desc, '{'+TEI_NAMESPACE+'}publicationStmt')
    etree.SubElement(publication_stmt, '{'+TEI_NAMESPACE+'}p').text = 'Colação automatizada.'
    
    profile_desc = etree.SubElement(tei_header, '{'+TEI_NAMESPACE+'}profileDesc')
    partic_desc = etree.SubElement(profile_desc, '{'+TEI_NAMESPACE+'}particDesc')

    for wit_key, wit_uri in wit_ids.items():
        person = etree.SubElement(partic_desc, '{'+TEI_NAMESPACE+'}person', {etree.QName(XML_NAMESPACE, "id"): wit_key.lstrip('#')})
        etree.SubElement(person, '{'+TEI_NAMESPACE+'}persName').text = f'Versão {wit_key.lstrip("#")}'

    return etree.tostring(tei_root, pretty_print=True, encoding='utf-8', xml_declaration=True).decode('utf-8')

# --- collate_line (MODIFICADA para <w>/<pc> dentro de <rdg> E tratamento de atributos/inserções) ---
def collate_line(tokens_mod_full, tokens_vesq_full, tokens_vdir_full, wit_ids):
    collated_l = etree.Element('{'+TEI_NAMESPACE+'}l')

    mod_comparable = [t[2] for t in tokens_mod_full]
    esq_comparable = [t[1] for t in tokens_vesq_full] 
    dir_comparable = [t[1] for t in tokens_vdir_full]

    aligned_esq_to_mod, esq_inserts = _align_target_to_base(tokens_mod_full, tokens_vesq_full, mod_comparable, esq_comparable)
    aligned_dir_to_mod, dir_inserts = _align_target_to_base(tokens_mod_full, tokens_vdir_full, mod_comparable, dir_comparable)

    all_inserts_data = []
    # Inserções são blocos de tokens, vamos mantê-los como blocos para agrupamento
    for base_idx, ins_tokens_list in esq_inserts:
        all_inserts_data.append((base_idx, 'VEsq', ins_tokens_list))
    for base_idx, ins_tokens_list in dir_inserts:
        all_inserts_data.append((base_idx, 'VDir', ins_tokens_list))
    all_inserts_data.sort(key=lambda x: x[0])

    insert_ptr = 0

    for mod_idx in range(len(tokens_mod_full) + 1):
        current_insert_blocks = {} # {block_representation_tuple: [list_of_wit_ids]}
        # Agrupar inserções no mesmo ponto da base
        while insert_ptr < len(all_inserts_data) and all_inserts_data[insert_ptr][0] == mod_idx:
            _, source_wit, inserted_tokens_full_data_block = all_inserts_data[insert_ptr]
            
            # CRIAR REPRESENTAÇÃO HASHABLE DO BLOCO DE TOKENS
            # Cada token_data é (original_text, comparable_text, is_punct, tag, attrs)
            # Precisamos converter 'attrs' para frozenset para que o tuple seja hashable.
            hashable_block_parts = []
            for token_data in inserted_tokens_full_data_block:
                # Assuming token_data is (original_text, comparable_text, is_punct, tag, attrs)
                # Ensure attrs is the last element and is a dict
                if len(token_data) == 5 and isinstance(token_data[4], dict):
                    hashable_token = token_data[:-1] + (frozenset(token_data[4].items()),)
                else: # Fallback if attrs is not a dict or token structure is different
                    hashable_token = tuple(token_data)
                hashable_block_parts.append(hashable_token)
            
            block_representation = tuple(hashable_block_parts) # This tuple of tuples is now hashable
            
            current_insert_blocks.setdefault(block_representation, []).append(wit_ids[source_wit])
            insert_ptr += 1

        if current_insert_blocks:
            app = etree.Element('{'+TEI_NAMESPACE+'}app')
            collated_l.append(app)
            
            # Adicionar o rdg vazio para VMod primeiro
            rdg_mod_empty = etree.SubElement(app, '{'+TEI_NAMESPACE+'}rdg', wit=wit_ids['VMod'])
            
            # Criar rdgs agrupados para as inserções (não VMod)
            # current_insert_blocks: {block_representation_tuple: [list_of_wit_ids]}
            
            # Ordenar keys para consistência, garantindo que não seja a VMod (já tratada)
            # e que keys vazias ou None sejam tratadas.
            ordered_insert_keys = sorted(current_insert_blocks.keys(), 
                                         key=lambda k: (0 if k else 1, str(k))) # 0 para não-vazio, 1 para vazio, depois lexicográfico
            
            for block_key in ordered_insert_keys:
                wits_list = current_insert_blocks[block_key]
                # Não criar rdg para VMod aqui, já foi feito
                if wit_ids['VMod'] in wits_list:
                    continue 

                rdg = etree.SubElement(app, '{'+TEI_NAMESPACE+'}rdg', wit=" ".join(sorted(wits_list)))
                
                # Reconstruir os elementos <w> ou <pc> a partir do block_key
                for token_data_tuple in block_key:
                    original_text = token_data_tuple[0]
                    tag_type = token_data_tuple[3]
                    # attrs aqui é um frozenset, precisa converter de volta para dict
                    attrs = dict(token_data_tuple[4])
                    
                    inner_elem = etree.Element('{'+TEI_NAMESPACE+'}' + tag_type, attrs)
                    inner_elem.text = original_text
                    rdg.append(inner_elem)
            

        if mod_idx < len(tokens_mod_full):
            mod_token = tokens_mod_full[mod_idx]
            esq_token = aligned_esq_to_mod[mod_idx]
            dir_token = aligned_dir_to_mod[mod_idx]

            mod_original_text = mod_token[1]
            esq_original_text = esq_token[0] if esq_token else None
            dir_original_text = dir_token[0] if dir_token else None

            mod_tag = mod_token[0]
            mod_attrs = mod_token[4]

            esq_tag = esq_token[3] if esq_token else None
            esq_attrs = esq_token[4] if esq_token else {}
            dir_tag = dir_token[3] if dir_token else None
            dir_attrs = dir_token[4] if dir_token else {}


            if (esq_original_text is not None and dir_original_text is not None and
                mod_original_text == esq_original_text and 
                mod_original_text == dir_original_text and
                mod_tag == esq_tag and mod_tag == dir_tag): 
                
                elem = etree.Element('{'+TEI_NAMESPACE+'}' + mod_tag, mod_attrs)
                elem.text = mod_original_text
                collated_l.append(elem)
            else:
                app = etree.Element('{'+TEI_NAMESPACE+'}app')
                collated_l.append(app)

                grouped_rdgs = {} 
                
                # Para VMod
                mod_key = (mod_original_text, mod_tag, frozenset(mod_attrs.items()))
                grouped_rdgs.setdefault(mod_key, []).append(wit_ids['VMod'])
                
                # Para VEsq
                if esq_original_text is not None:
                    esq_key_attrs = mod_attrs if esq_tag == 'w' else esq_attrs # Usar attrs da VMod se for palavra, senão os próprios (e.g. &)
                    esq_key = (esq_original_text, esq_tag, frozenset(esq_key_attrs.items()))
                else: # rdg vazio
                    esq_key = (None, None, frozenset())
                grouped_rdgs.setdefault(esq_key, []).append(wit_ids['VEsq'])

                # Para VDir
                if dir_original_text is not None:
                    dir_key_attrs = mod_attrs if dir_tag == 'w' else dir_attrs # Usar attrs da VMod se for palavra, senão os próprios (e.g. &)
                    dir_key = (dir_original_text, dir_tag, frozenset(dir_key_attrs.items()))
                else: # rdg vazio
                    dir_key = (None, None, frozenset())
                grouped_rdgs.setdefault(dir_key, []).append(wit_ids['VDir'])

                ordered_keys = sorted(grouped_rdgs.keys(), 
                                      key=lambda k: (0 if k[0] is not None and wit_ids['VMod'] in grouped_rdgs[k] else 
                                                     (2 if k[0] is None else 1),
                                                     k[0] or ''))

                for key in ordered_keys:
                    text_val, tag_type_val, attrs_tuple = key
                    wits_list = grouped_rdgs[key]
                    
                    rdg = etree.SubElement(app, '{'+TEI_NAMESPACE+'}rdg', wit=" ".join(sorted(wits_list)))
                    
                    if text_val is not None:
                        inner_elem = etree.Element('{'+TEI_NAMESPACE+'}' + tag_type_val, dict(attrs_tuple))
                        inner_elem.text = text_val
                        rdg.append(inner_elem)

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