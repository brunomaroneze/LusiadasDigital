def txt_to_tei(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    tei_lines = []
    stanza_number = 9  # Começa a contagem das estrofes a partir do número necessário
    verse_counter = 0

    for line in lines:
        line = line.strip()

        # Ignora linhas em branco
        if line == "":
            continue

        # Copia linhas que começam com <fw> ou <pb/> diretamente para o arquivo TEI
        if line.startswith('<fw') or line.startswith('<pb'):
            tei_lines.append(line)
            continue

        # Inicia uma nova estrofe a cada 8 versos
        if verse_counter == 0:
            tei_lines.append('<lg type="estrofe" n="{}">'.format(stanza_number))

        # Adiciona um verso
        tei_lines.append('<l>{}</l>'.format(line))
        verse_counter += 1

        # Fecha a estrofe após 8 versos
        if verse_counter == 8:
            tei_lines.append('</lg>')
            stanza_number += 1
            verse_counter = 0

    # Fecha a última estrofe se não estiver fechada
    if verse_counter > 0:
        tei_lines.append('</lg>')

    # Salva o arquivo TEI
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write('\n'.join(tei_lines))


# Uso do script
input_txt = 'lusiadas_pelicano_direita.txt'
output_tei = 'Lusíadas_pelicano_à_direita_tei.xml'
txt_to_tei(input_txt, output_tei)