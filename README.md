# Lusíadas Digital

**Versão 0.1.0**

O Lusíadas Digital é uma plataforma de leitura e estudo de *Os Lusíadas*, de Luís de Camões. O projeto desenvolve uma interface digital para a edição filológica da obra, aproximando textos, imagens e recursos de comparação.

## Funcionalidades

- Leitura dos cantos em duas colunas, com seleção independente do conteúdo de cada uma.
- Exibição das versões modernizada, original A e original B, além de espaços para imagens das duas edições.
- Comparação entre versões textuais, com opção de realçar diferenças.
- Navegação por canto, página e estrofe.
- Visualização dos elementos pré-textuais da edição de 1572.
- Administração de cantos, páginas de texto TEI-XML e imagens pelo Django Admin.
- Importação de textos TEI-XML para o banco de dados, com relatório de integridade.

As imagens dependem de arquivos e registros cadastrados. A paginação dos textos importados é sintética: ela agrupa estrofes e **não corresponde à paginação dos fac-símiles**.

## Tecnologias e estrutura

O site utiliza Python, Django, SQLite, lxml e Pillow. As dependências estão listadas em [requirements.txt](requirements.txt).

- `lusiadas/`: configurações e rotas principais do Django.
- `homepage/`: aplicação, modelos, páginas, testes e comandos de importação.
- `LusiadasTextos/`: arquivos XML e outros materiais textuais.
- `static/`: CSS, JavaScript e imagens estáticas.
- `media/`: arquivos de mídia, incluindo imagens cadastradas no Admin.

## Execução local

É necessário Python 3.12 ou superior. Na raiz do projeto:

1. Crie e ative um ambiente virtual:

   ```sh
   python -m venv .venv
   ```

   No Windows, use `.venv\Scripts\activate`; no Linux ou macOS, use `source .venv/bin/activate`.

2. Instale as dependências:

   ```sh
   python -m pip install -r requirements.txt
   ```

3. Crie um arquivo `.env` a partir de [`.env.example`](.env.example). Para desenvolvimento, defina `DEBUG=True`, inclua `localhost,127.0.0.1` em `ALLOWED_HOSTS` e gere uma chave própria para `SECRET_KEY`:

   ```sh
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

4. Prepare o banco e importe os textos:

   ```sh
   python manage.py migrate
   python manage.py importar_tudo
   ```

5. Inicie o servidor de desenvolvimento:

   ```sh
   python manage.py runserver
   ```

   Acesse `http://127.0.0.1:8000/`. Para usar o Admin em `/admin/`, crie um usuário com `python manage.py createsuperuser`.

## Importação dos textos

O comando `importar_tudo` utiliza os arquivos `LusiadasModernizado.xml`, `LusiadasEsquerda.xml` e `LusiadasDireita.xml`, na pasta `LusiadasTextos/`. Ele identifica os cantos pela posição no arquivo, não pelo atributo `n`.

Para verificar os XMLs sem alterar o banco:

```sh
python manage.py importar_tudo --so-relatorio
```

O relatório aponta erros e avisos de integridade; sua apresentação não impede automaticamente a importação. Na importação, o comando atualiza ou cria páginas e remove páginas das versões importadas que deixaram de existir nos XMLs, respeitando o filtro `--cantos` quando informado. Ele também remove cantos sem textos nem imagens. **Faça backup do banco antes de importar sobre dados existentes.** As opções estão documentadas em [importar_tudo.py](homepage/management/commands/importar_tudo.py).

## Dados e produção

O banco local `db.sqlite3` e os arquivos `.env` e `.env.prod` são ignorados pelo Git. Portanto, o banco e os segredos não acompanham o push. Na VPS, configure um `.env` próprio com `DEBUG=False`, uma chave secreta exclusiva, os hosts permitidos e as origens CSRF necessárias; não publique esse arquivo.

Em produção, use um servidor WSGI apropriado, configure HTTPS e a entrega dos arquivos estáticos e de mídia, execute as migrations e `collectstatic` e mantenha backups do banco e da mídia. O servidor de desenvolvimento `runserver` não deve ser usado em produção.
