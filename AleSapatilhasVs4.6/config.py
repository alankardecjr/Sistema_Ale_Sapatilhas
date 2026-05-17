"""
config.py — Constantes e convenções do projeto Alê Sapatilhas ERP/PDV.

Centralizar nomes mágicos aqui facilita manutenção e demonstra organização
típica de sistemas comerciais (camada de configuração separada da UI e do BD).

Arquitetura em camadas (visão para estudo / portfólio):
    ┌─────────────────────────────────────────┐
    │  main.py          → Shell / navegação   │
    │  cadastro_*       → Telas de negócio    │
    │  gerenciar_*      → Financeiro (CRUD)   │
    │  ui_utils.py      → Visual / UX         │
    │  database.py      → Persistência SQLite │
    │  config.py        → Constantes          │
    └─────────────────────────────────────────┘

Regra de ouro: PDV altera venda/estoque; financeiro altera pagamentos.
"""

# --- Tipos de contato (tabela clientes — cadastro unificado) ---
TIPO_CLIENTE = "Cliente"
TIPO_FORNECEDOR = "Fornecedor"

# --- Domínio financeiro ---
TIPO_RECEITA = "Receita"
TIPO_DESPESA = "Despesa"

STATUS_FINANCEIRO_ABERTO = ("Pendente", "Atrasado")
STATUS_FINANCEIRO_PAGO = "Pago"
STATUS_FINANCEIRO_CANCELADO = "Cancelado"

# --- Vendas ---
STATUS_VENDA_FINALIZADA = "Finalizada"
STATUS_VENDA_CANCELADA = "Cancelada"
STATUS_VENDA_PENDENTE = "Pendente"

# --- Estoque mínimo para alerta no dashboard ---
LIMITE_ESTOQUE_ALERTA = 3

# --- Formas de pagamento padronizadas (espelhar nas Combobox das telas) ---
FORMAS_PAGAMENTO = (
    "Dinheiro", "PIX", "Cartão de Débito", "Cartão de Crédito", "Crediário", "Boleto", "Outros"
)
