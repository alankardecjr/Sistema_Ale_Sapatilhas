# Alê Sapatilhas — ERP / PDV

Sistema desktop de gestão para loja de calçados e confecções, desenvolvido em **Python** com **Tkinter** e **SQLite**.

**Versão atual do código:** `AleSapatilhasVs4.8`

---

## Novidades (Vs 4.8)

| Módulo | Atualização |
|--------|-------------|
| **PDV** | Layout em duas colunas; busca de cliente com popup; **desconto em R$** no carrinho; estoque baixa só após pagamento em Receitas |
| **Receitas** | Encargos de operadora (%), valor líquido, cartão débito/crédito, editar itens da venda |
| **Main** | Coluna tipo em produtos e vendas; filtros sem confirmação excessiva; senha no fluxo de caixa |
| **Anotações** | Persistência em SQLite (tabela `anotacoes`) |
| **Segurança** | Senha do fluxo em `secrets.local.json` (não versionado); senha padrão inicial `1234` se não existir o arquivo |
| **Segurança Extra** | Alteração de senha exige senha atual, nova senha e confirmação. |

---

## Funcionalidades

| Área | O que o sistema faz |
|------|---------------------|
| **PDV** | Carrinho, cliente, desconto; finalizar gera venda pendente e abre Receitas |
| **Receitas** | Pagamento, parcelas, encargos cartão; baixa de estoque na confirmação |
| **Estoque** | SKU, grade cor/tamanho, tipo Calçado/Vestuário |
| **Financeiro** | Despesas, fluxo de caixa, contas a receber/pagar |
| **Ferramentas** | Calculadora, calendário, anotações, alterar senha do caixa |

---

## Requisitos

- **Python 3.10+**
- **Tkinter** (incluso no Python para Windows)
- **Pillow** (opcional, miniaturas no PDV): `pip install Pillow`

---

## Instalação e execução

```powershell
cd c:\VisualCode\Projeto_ERP_PDV\AleSapatilhasVs4.8

pip install -r requirements.txt

# Senha do fluxo de caixa (obrigatório em produção)
copy secrets.local.json.example secrets.local.json
# Edite secrets.local.json e defina "senha_fluxo_caixa"
# Se não existir o arquivo, a senha inicial padrão é 1234.

# (Opcional) Dados de demonstração
python populardb.py

python main.py
```

O banco `AleSapatilhasVs4.8db` é criado na pasta do módulo. **Não versione** o arquivo `.db` nem `secrets.local.json` (veja `.gitignore`).

> O sistema exibe datas em formato `DD/MM/YYYY` em todas as telas de usuário.

---

## Fluxo operacional

1. Cadastre **contatos** e **produtos**.
2. **Gerar vendas (PDV)** → cliente + itens + desconto → **Finalizar venda**.
3. Em **Gerenciar Receitas** → informe pagamento (senha do fluxo) → estoque é baixado.
4. **Contas a pagar** / **Fluxo de caixa** para despesas e visão financeira.

---

## Regra de ouro

| Módulo | Responsabilidade |
|--------|------------------|
| `cadastro_vendas.py` | PDV: itens e venda pendente (sem baixa de estoque) |
| `gerenciar_receitas.py` | Pagamento e baixa de estoque |
| `database.py` | Transações SQLite |

---

## Testes automatizados

```powershell
cd AleSapatilhasVs4.8
python test_sistema.py
```

Cobre: cliente, produto, PDV/estoque, desconto, cancelamento, anotações, senha local, despesa e venda legada.

---

## Estrutura

```
Projeto_ERP_PDV/
├── README.md
├── .gitignore
└── AleSapatilhasVs4.8/
    ├── main.py
    ├── config.py
    ├── database.py
    ├── ui_utils.py
    ├── cadastro_*.py
    ├── gerenciar_*.py
    ├── test_sistema.py
    ├── secrets.local.json.example
    └── AleSapatilhasVs4.8db   (local, não commitar)
```

---

## Licença

Projeto educacional / portfólio — **Alê Sapatilhas Vs 4.8**.
