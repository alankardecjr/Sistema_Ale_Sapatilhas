"""
config.py — Constantes e convenções do projeto Alê Sapatilhas ERP/PDV.

Centralizar nomes mágicos aqui facilita manutenção e demonstra organização
típica de sistemas comerciais (camada de configuração separada da UI e do BD).

A senha do fluxo de caixa fica em secrets.local.json (não versionado).
Copie secrets.local.json.example para secrets.local.json na primeira instalação.

Regra de ouro: PDV altera venda/estoque; financeiro altera pagamentos.
"""

import json
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRETS_PATH = os.path.join(_BASE_DIR, "secrets.local.json")
SECRETS_EXAMPLE_PATH = os.path.join(_BASE_DIR, "secrets.local.json.example")

# Fallback apenas se secrets.local.json não existir (troque no primeiro uso)
_SENHA_FLUXO_FALLBACK = "1234"

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

FORMAS_CARTAO = ("Cartão de Débito", "Cartão de Crédito")

FORMA_PAGAMENTO_PDV_PENDENTE = "À definir"
STATUS_VENDA_PDV_PENDENTE = "Pendente"


def obter_senha_fluxo_caixa():
    """Lê senha do arquivo local; cria a partir do exemplo se necessário."""
    if os.path.isfile(SECRETS_PATH):
        try:
            with open(SECRETS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            senha = str(data.get("senha_fluxo_caixa", "")).strip()
            if senha:
                return senha
        except (json.JSONDecodeError, OSError):
            pass
    return _SENHA_FLUXO_FALLBACK


def salvar_senha_fluxo_caixa(nova_senha):
    """Persiste senha em secrets.local.json (uso em Configurações)."""
    nova_senha = (nova_senha or "").strip()
    if not nova_senha:
        return False, "Informe uma senha válida."
    try:
        with open(SECRETS_PATH, "w", encoding="utf-8") as f:
            json.dump({"senha_fluxo_caixa": nova_senha}, f, indent=2, ensure_ascii=False)
        global SENHA_FLUXO_CAIXA
        SENHA_FLUXO_CAIXA = nova_senha
        return True, "Senha do fluxo de caixa atualizada."
    except OSError as e:
        return False, f"Não foi possível salvar: {e}"


def secrets_configurado():
    """True se o operador já definiu senha em arquivo local."""
    return os.path.isfile(SECRETS_PATH)


# Compatibilidade com código que importa config.SENHA_FLUXO_CAIXA
SENHA_FLUXO_CAIXA = obter_senha_fluxo_caixa()
