# text/views.py

from django.shortcuts import render, get_object_or_404
from django.conf import settings
import os
import xml.etree.ElementTree as ET

# Importe seus modelos quando os criar (ex: Canto, Estrofe)
# from .models import Canto, Estrofe

# Função para listar os cantos (ou para a página inicial do app 'text')
def canto_list(request):
    # Por enquanto, vamos simular uma lista de cantos, ou ler do XML diretamente
    # Idealmente, você buscaria isso do seu banco de dados depois de importar os XMLs.

    # Exemplo simples de como listar arquivos na pasta LusiadasTextos
    cantos_disponiveis = []
    try:
        for filename in os.listdir(settings.LUSIADAS_DATA_DIR):
            if filename.startswith('canto_') and filename.endswith('.xml'):
                # Extrair o número do canto do nome do arquivo (ex: 'canto_1.xml' -> 1)
                try:
                    canto_num = int(filename.split('_')[1].split('.')[0])
                    cantos_disponiveis.append({'numero': canto_num, 'nome_arquivo': filename})
                except ValueError:
                    pass # Ignora arquivos com nomes inesperados
        cantos_disponiveis.sort(key=lambda x: x['numero']) # Ordena por número do canto
    except FileNotFoundError:
        cantos_disponiveis = [{"numero": 0, "nome_arquivo": "Nenhum arquivo XML de canto encontrado!"}]


    context = {
        'cantos': cantos_disponiveis,
        'page_title': "Texto da Obra - Cantos"
    }
    return render(request, 'text/canto_list.html', context)

# Função para exibir detalhes de um canto específico
def canto_detail(request, canto_numero):
    # Por enquanto, vamos ler o XML diretamente.
    # No futuro, você buscaria isso do seu banco de dados usando seus modelos.

    caminho_xml = os.path.join(settings.LUSIADAS_DATA_DIR, f'canto_{canto_numero}.xml')
    canto_data = None
    erro = None

    if os.path.exists(caminho_xml):
        try:
            tree = ET.parse(caminho_xml)
            root = tree.getroot() # A tag raiz do seu XML para um canto

            # Exemplo: Adapte a lógica abaixo à estrutura do seu XML
            # Aqui estamos assumindo que o XML de um canto tem tags para título e estrofes
            titulo_canto = root.find('titulo').text if root.find('titulo') is not None else f"Canto {canto_numero}"
            estrofes = []
            for estrofe_elem in root.findall('estrofe'): # Supondo que você tem tags <estrofe>
                estrofe_num = estrofe_elem.get('numero')
                versos_list = [verso.text for verso in estrofe_elem.findall('verso')] # Supondo tags <verso>
                estrofes.append({'numero': estrofe_num, 'versos': versos_list})

            canto_data = {
                'numero': canto_numero,
                'titulo': titulo_canto,
                'estrofes': estrofes,
            }

        except ET.ParseError as e:
            erro = f"Erro ao fazer parse do XML: {e}"
        except Exception as e:
            erro = f"Ocorreu um erro ao ler o canto {canto_numero}: {e}"
    else:
        erro = f"O arquivo 'canto_{canto_numero}.xml' não foi encontrado."

    context = {
        'canto': canto_data,
        'erro': erro,
        'page_title': f"Canto {canto_numero}",
    }
    return render(request, 'text/canto_detail.html', context)


# Exemplo para uma futura estrofe_detail, caso decida implementá-la
# def estrofe_detail(request, canto_numero, estrofe_numero):
#     # Implementação similar a canto_detail, mas focando em uma estrofe específica
#     pass