# Ale Sapatilhas ERP

Sistema desktop de gestão comercial desenvolvido em Python para pequenas lojas de calçados e confecções.

O repositório foi preparado para avaliação técnica: o código principal está no nível raiz, não há arquivos sensíveis rastreados e a execução é direta com `requirements.txt`.

---

## Funcionalidades

- Cadastro de clientes
- Cadastro de produtos
- Registro de vendas
- Controle de estoque
- Controle financeiro
- Gestão de receitas e despesas
- Relatórios simples e consultas
- Interface com Tkinter

---

## Tecnologias utilizadas

- Python
- Tkinter
- SQLite
- Git
- GitHub

---

## Como executar

1. Clone o repositório:

```bash
git clone https://github.com/alankardecjr/ale-sapatilhas-erp.git
```

2. Acesse a pasta do projeto:

```bash
cd ale-sapatilhas-erp
```

3. Crie e ative um ambiente virtual (opcional, mas recomendado):

```bash
python -m venv venv
.\venv\Scripts\Activate
```

4. Instale as dependências:

```bash
pip install -r requirements.txt
```

5. Execute o sistema:

```bash
python main.py
```

---

## Estrutura do repositório

```text
.
├── cadastro_clientes.py
├── cadastro_produtos.py
├── cadastro_vendas.py
├── config.py
├── database.py
├── executar_testes.bat
├── gerenciar_despesas.py
├── gerenciar_receitas.py
├── INDICE_DOCUMENTACAO.md
├── main.py
├── populardb.py
├── README.md
├── requirements.txt
├── secrets.local.json.example
├── test_sistema.py
├── ui_utils.py
├── notas_salvas/
└── images/
```

- `secrets.local.json.example`: modelo de arquivo de configuração local.
- `notes_salvas/`: pasta de notas versionada com `.gitkeep`.

---

## Observações para recrutadores

- O projeto está configurado para ser analisado facilmente.
- Não há arquivos de banco de dados (`*.db`) ou segredos (`secrets.local.json`) versionados.
- A arquitetura atual é simples, com foco em funcionalidades e execução direta.

---

## Sobre o desenvolvedor

Desenvolvido por Alan Kardec, em transição de carreira para TI.

O objetivo deste projeto é demonstrar organização de código, uso de Python e a capacidade de estruturar uma aplicação funcional com interface, persistência e controles básicos.
