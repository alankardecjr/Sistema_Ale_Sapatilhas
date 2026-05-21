"""
database.py — Camada de persistência (SQLite).

Responsabilidades:
  - Schema, migrações incrementais e conexão com PRAGMA foreign_keys
  - Regras de negócio que envolvem transação (venda + estoque + financeiro)
  - Consultas para relatórios e listagens da interface

Padrão de retorno em operações críticas: tupla (sucesso: bool, mensagem: str)
para a UI exibir feedback sem acoplar messagebox aqui (separação de camadas).
"""

import sqlite3
import os
from datetime import datetime

import config

# --- Configuração do Banco de Dados (sempre na pasta do projeto) ---
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(_BASE_DIR, "AleSapatilhasVs4.8.1db")

def conectar():
    """Estabelece a conexão com suporte a chaves estrangeiras."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def _migrar_schema(cursor):
    """Aplica alterações incrementais sem perder dados existentes."""
    cursor.execute("PRAGMA table_info(produtos)")
    cols_prod = [row[1] for row in cursor.fetchall()]
    if "fornecedor_id" not in cols_prod:
        cursor.execute("ALTER TABLE produtos ADD COLUMN fornecedor_id INTEGER REFERENCES clientes (id)")

    cursor.execute("PRAGMA table_info(financeiro)")
    cols_fin = [row[1] for row in cursor.fetchall()]
    if "fornecedor_id" not in cols_fin:
        cursor.execute("ALTER TABLE financeiro ADD COLUMN fornecedor_id INTEGER REFERENCES clientes (id)")

    cursor.execute("PRAGMA table_info(vendas)")
    cols_vendas = [row[1] for row in cursor.fetchall()]
    if "estoque_baixado" not in cols_vendas:
        cursor.execute("ALTER TABLE vendas ADD COLUMN estoque_baixado INTEGER DEFAULT 0")

def criar_tabelas():
    """Cria a estrutura completa do ERP com foco em rastreabilidade financeira."""
    with conectar() as conn:
        cursor = conn.cursor()
        
        # --- PRODUTOS ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            tipo TEXT CHECK(tipo IN ('Calçados', 'Confecções')) DEFAULT 'Calçados',
            produto TEXT NOT NULL,
            cor TEXT NOT NULL,
            tamanho INTEGER NOT NULL,
            precocusto REAL DEFAULT 0,
            precovenda REAL NOT NULL,
            quantidade INTEGER DEFAULT 0,
            categoria TEXT,
            material TEXT,
            fornecedor TEXT,
            status_item TEXT DEFAULT 'Disponível',
            foto TEXT DEFAULT '',
            ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

        # --- CLIENTES ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT CHECK(tipo IN ('Cliente', 'Fornecedor')) DEFAULT 'Cliente',
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE,
            telefone TEXT NOT NULL,
            email TEXT,
            aniversario DATE,
            tamanho_calcado INTEGER,
            endereco_completo TEXT,
            bairro TEXT,
            cidade TEXT,
            cep TEXT,
            observacao TEXT,
            limite_credito REAL DEFAULT 0,
            data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
            status_cliente TEXT DEFAULT 'Ativo' CHECK(status_cliente IN ('Vip', 'Ativo', 'Inativo', 'Bloqueado'))
        )""")

        # --- INTERAÇÕES CRM ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cliente_interacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            data_interacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            tipo_contato TEXT CHECK(tipo_contato IN ('WhatsApp', 'Telefone', 'E-mail', 'Presencial')),
            assunto TEXT, 
            detalhes TEXT,
            vendedor_responsavel TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )""")

        # --- VENDAS ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            valor_bruto REAL NOT NULL,
            desconto REAL DEFAULT 0,
            valor_total REAL NOT NULL,
            forma_pagamento TEXT NOT NULL, 
            qtd_parcelas INTEGER DEFAULT 1,
            data_venda DATETIME DEFAULT CURRENT_TIMESTAMP,
            status_venda TEXT DEFAULT 'Finalizada' CHECK(status_venda IN ('Finalizada', 'Cancelada', 'Pendente')),
            estoque_baixado INTEGER DEFAULT 0,
            vendedor TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )""")

        # --- ITENS DA VENDA ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_venda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            preco_unitario REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (venda_id) REFERENCES vendas (id) ON DELETE CASCADE,
            FOREIGN KEY (produto_id) REFERENCES produtos (id)
        )""")

        # --- FINANCEIRO ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT CHECK(tipo IN ('Receita', 'Despesa')),
            venda_id INTEGER,
            cliente_id INTEGER,
            id_agrupador INTEGER, 
            entidade_nome TEXT, 
            descricao TEXT,
            valor REAL NOT NULL,
            valor_base REAL,
            valor_pago REAL DEFAULT 0,
            encargos REAL DEFAULT 0,
            descontos REAL DEFAULT 0,
            forma_pagamento TEXT,
            recorrencia TEXT DEFAULT 'Não Recorrente',
            total_parcelas INTEGER DEFAULT 1,
            parcelas_atual INTEGER DEFAULT 1,  -- Mantido nomenclatura existente
            data_vencimento DATE NOT NULL,
            data_pagamento DATE,
            categoria TEXT,
            status TEXT DEFAULT 'Pendente' CHECK(status IN ('Pendente', 'Pago', 'Atrasado', 'Cancelado')),
            data_lancamento DATE DEFAULT CURRENT_DATE,
            tipo_encargos TEXT DEFAULT 'Valor Fixo',
            valor_encargos REAL DEFAULT 0,
            tipo_descontos TEXT DEFAULT 'Valor Fixo',
            valor_descontos REAL DEFAULT 0,
            FOREIGN KEY (venda_id) REFERENCES vendas (id) ON DELETE CASCADE,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)   
        )""")

        # --- ANOTAÇÕES ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS anotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL UNIQUE,
            conteudo TEXT,
            data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

        # --- PAGAMENTOS (Log de auditoria) ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            financeiro_id INTEGER,
            valor_pago REAL NOT NULL,
            juros_pagos REAL DEFAULT 0,
            descontos_pagos REAL DEFAULT 0,
            forma_pagamento TEXT NOT NULL,
            data_pagamento DATETIME DEFAULT CURRENT_TIMESTAMP,
            conta_bancaria TEXT,
            observacao TEXT,
            FOREIGN KEY (venda_id) REFERENCES vendas (id),
            FOREIGN KEY (financeiro_id) REFERENCES financeiro (id)
        )""")

        # Triggers de Estoque 
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_estoque_status
        AFTER UPDATE OF quantidade ON produtos
        BEGIN
            UPDATE produtos SET status_item = 'Esgotado' WHERE id = NEW.id AND quantidade <= 0;
            UPDATE produtos SET status_item = 'Disponível' WHERE id = NEW.id AND quantidade > 0 AND status_item = 'Esgotado';
        END;
        """)

        # Verificação preventiva de colunas extras
        cursor.execute("PRAGMA table_info(produtos)")
        colunas_produtos = [row[1] for row in cursor.fetchall()]
        if "foto" not in colunas_produtos:
            cursor.execute("ALTER TABLE produtos ADD COLUMN foto TEXT DEFAULT ''")

        _migrar_schema(cursor)
        conn.commit()

def obter_nome_contato(contato_id):
    if not contato_id:
        return None
    with conectar() as conn:
        row = conn.execute("SELECT nome FROM clientes WHERE id = ?", (contato_id,)).fetchone()
        return row[0] if row else None

def listar_contatos(tipo=None, termo=""):
    with conectar() as conn:
        cursor = conn.cursor()
        sql = "SELECT id, tipo, nome, telefone, status_cliente FROM clientes WHERE 1=1"
        params = []
        if tipo:
            sql += " AND tipo = ?"
            params.append(tipo)
        if termo:
            sql += " AND (nome LIKE ? OR telefone LIKE ? OR cpf LIKE ?)"
            params.extend([f"%{termo}%", f"%{termo}%", f"%{termo}%"])
        sql += " ORDER BY nome ASC"
        cursor.execute(sql, params)
        return cursor.fetchall()

# --- Funções Auxiliares de Cálculo de Data ---
def adicionar_meses(data_obj, meses):
    ano = data_obj.year + (data_obj.month + meses - 1) // 12
    mes = (data_obj.month + meses - 1) % 12 + 1
    ultimo_dia = [31, 29 if ano % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes-1]
    dia = min(data_obj.day, ultimo_dia)
    return datetime(ano, mes, dia)

def calcular_valor_com_ajustes(valor_base, t_enc, v_enc, t_desc, v_desc):
    enc = v_enc if t_enc == 'Valor Fixo' else round(valor_base * (v_enc / 100), 2)
    des = v_desc if t_desc == 'Valor Fixo' else round(valor_base * (v_desc / 100), 2)
    return round(valor_base + enc - des, 2), enc, des


# --- Gerenciamento Comercial e de Estoque ---
def cadastrar_produto(sku, tipo, produto, cor, tamanho, precocusto, precovenda, quantidade, categoria, material, fornecedor, foto="", fornecedor_id=None):
    if fornecedor_id and not fornecedor:
        fornecedor = obter_nome_contato(fornecedor_id) or ""
    try:
        with conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, produto, cor, tamanho, precocusto, precovenda, categoria, material, fornecedor, status_item, foto, quantidade FROM produtos WHERE sku = ?", (sku,))
            existente = cursor.fetchone()
            if existente:
                mesmo_item = (
                    existente[1] == produto and existente[2] == cor and str(existente[3]) == str(tamanho) and
                    float(existente[4]) == float(precocusto) and float(existente[5]) == float(precovenda) and existente[6] == categoria and
                    existente[7] == material and existente[8] == fornecedor and existente[9] == 'Disponível'
                )
                if mesmo_item:
                    cursor.execute("UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?", (quantidade, existente[0]))
                    conn.commit()
                    return True
                # Se SKU já existe, mas atributos mudaram, gera um novo SKU único
                base = sku
                suffix = 1
                novo_sku = f"{base}_{suffix}"
                while cursor.execute("SELECT 1 FROM produtos WHERE sku = ?", (novo_sku,)).fetchone():
                    suffix += 1
                    novo_sku = f"{base}_{suffix}"
                sku = novo_sku

            cursor.execute("""
                INSERT INTO produtos (sku, tipo, produto, cor, tamanho, precocusto, precovenda, quantidade, categoria, material, fornecedor, foto, fornecedor_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sku, tipo, produto, cor, tamanho, precocusto, precovenda, quantidade, categoria, material, fornecedor, foto, fornecedor_id))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

def exibir_produtos():
    # --- Recupera a lista completa de produtos cadastrados com seus principais detalhes técnicos e comerciais ---
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, sku, tipo, produto, cor, tamanho, precocusto, precovenda, quantidade, categoria, material, fornecedor, status_item, foto FROM produtos ORDER BY produto ASC")
        return cursor.fetchall()

def atualizar_produto(produto_id, **kwargs):
    # --- Atualiza campos específicos de um produto dinamicamente e registra o horário da última modificação ---
    with conectar() as conn:
        cursor = conn.cursor()
        campos = ", ".join(f"{k} = ?" for k in kwargs.keys())
        valores = list(kwargs.values()) + [produto_id]
        cursor.execute(f"UPDATE produtos SET {campos}, ultima_atualizacao = CURRENT_TIMESTAMP WHERE id = ?", valores)
        conn.commit()

# --- Funções de Clientes ---
def cadastrar_cliente(nome, cpf, tel, email, niver, tam, endereco, bairro, city, cep, obs, limite=0, tipo='Cliente'):
    # --- Registra contato unificado (Cliente ou Fornecedor) ---
    if tipo not in ('Cliente', 'Fornecedor'):
        tipo = 'Cliente'
    try:
        with conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO clientes (tipo, nome, cpf, telefone, email, aniversario, tamanho_calcado, endereco_completo, bairro, cidade, cep, observacao, limite_credito)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tipo, nome, cpf, tel, email, niver, tam, endereco, bairro, city, cep, obs, limite))
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return False
        
def exibir_clientes():
    # --- Lista todos os clientes cadastrados trazendo informações de contato, status e histórico de cadastro ---
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, tipo, nome, cpf, telefone, email, aniversario, tamanho_calcado, endereco_completo, bairro, cidade, cep, observacao, limite_credito, data_cadastro, status_cliente FROM clientes ORDER BY nome ASC")
        return cursor.fetchall()

def atualizar_cliente(cliente_id, **kwargs):
    # --- Modifica os dados de um cliente existente de forma flexível utilizando argumentos nomeados ---
    with conectar() as conn:
        cursor = conn.cursor()
        campos = ", ".join(f"{k} = ?" for k in kwargs.keys())
        valores = list(kwargs.values()) + [cliente_id]
        cursor.execute(f"UPDATE clientes SET {campos} WHERE id = ?", valores)
        conn.commit()

def registrar_interacao(cliente_id, tipo, assunto, detalhes, vendedor):
    with conectar() as conn:
        conn.execute("INSERT INTO cliente_interacoes (cliente_id, tipo_contato, assunto, detalhes, vendedor_responsavel) VALUES (?,?,?,?,?)",
                     (cliente_id, tipo, assunto, detalhes, vendedor))

# --- Funções de Vendas e Motores Financeiros ---
def realizar_venda_crediario(cliente_id, lista_produtos, parcelas, desc_venda=0):
    """Lógica de venda que alimenta a tabela 'receitas' via crediário.""" 
    with conectar() as conn:
        cursor = conn.cursor()
        total_bruto = sum(p['qtd'] * p['preco'] for p in lista_produtos)
        total_liquido = total_bruto - desc_venda
        
        cursor.execute("INSERT INTO vendas (cliente_id, valor_bruto, desconto, valor_total, forma_pagamento, qtd_parcelas) VALUES (?,?,?,?,?,?)",
                       (cliente_id, total_bruto, desc_venda, total_liquido, 'Crediário', parcelas))
        venda_id = cursor.lastrowid

        valor_parc = round(total_liquido / parcelas, 2)
        for i in range(parcelas):
            venc = adicionar_meses(datetime.now(), i).strftime("%Y-%m-%d") # Chamada Corrigida sem a String 'Mensal'

            cursor.execute("""INSERT INTO financeiro (tipo, venda_id, cliente_id, descricao, valor_base, valor, data_vencimento, parcelas_atual, total_parcelas, categoria, status) 
                      VALUES ('Receita', ?,?,?,?,?,?,?,?, 'Venda', 'Pendente')""", 
                   (venda_id, cliente_id, f"Parcela {i+1}/{parcelas} - Venda #{venda_id}", valor_parc, valor_parc, venc, i+1, parcelas))    
        conn.commit()

def realizar_venda_pdv(cliente_id, lista_produtos, desconto_total=0):
    """
    Registra venda no PDV sem dados de pagamento (status Pendente).
    Gera títulos financeiros em aberto para liquidação em Gerenciar Receitas.
    Retorno: (sucesso, mensagem, venda_id)
    """
    import config as cfg
    with conectar() as conn:
        cursor = conn.cursor()
        try:
            for item in lista_produtos:
                cursor.execute("SELECT quantidade, produto FROM produtos WHERE id = ?", (item['id'],))
                res = cursor.fetchone()
                if not res or res[0] < item['qtd']:
                    return False, f"Estoque insuficiente: {res[1] if res else 'Produto não encontrado'}", None

            total_bruto = sum(p['qtd'] * p['preco'] for p in lista_produtos)
            total_liquido = round(total_bruto - desconto_total, 2)

            cursor.execute("""
                INSERT INTO vendas (
                    cliente_id, valor_bruto, desconto, valor_total, forma_pagamento, qtd_parcelas,
                    status_venda, estoque_baixado
                ) VALUES (?, ?, ?, ?, ?, 1, ?, 0)
            """, (cliente_id, total_bruto, desconto_total, total_liquido,
                  cfg.FORMA_PAGAMENTO_PDV_PENDENTE, cfg.STATUS_VENDA_PDV_PENDENTE))
            venda_id = cursor.lastrowid

            for p in lista_produtos:
                cursor.execute(
                    "INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, subtotal) VALUES (?, ?, ?, ?, ?)",
                    (venda_id, p['id'], p['qtd'], p['preco'], p['qtd'] * p['preco']),
                )

            cursor.execute("SELECT nome FROM clientes WHERE id = ?", (cliente_id,))
            nome_cli = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO financeiro (
                    tipo, venda_id, cliente_id, id_agrupador, entidade_nome, descricao, valor, valor_base,
                    parcelas_atual, total_parcelas, data_vencimento, categoria, recorrencia, status
                ) VALUES ('Receita', ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, 'Venda', 'À receber', 'Pendente')
            """, (
                venda_id, cliente_id, venda_id, nome_cli,
                f"Venda #{venda_id} — aguardando pagamento",
                total_liquido, total_liquido,
                datetime.now().strftime("%Y-%m-%d"),
            ))

            conn.commit()
            return True, "Venda registrada. Confirme o pagamento em Gerenciar Receitas.", venda_id
        except Exception as e:
            conn.rollback()
            return False, f"Erro ao registrar venda: {str(e)}", None


def realizar_venda_segura(cliente_id, lista_produtos, forma_pgto, parcelas=1, desconto_total=0):
    """
  Transação atômica de venda: valida estoque, grava venda/itens, baixa estoque e gera receitas.

    Retorno: (sucesso: bool, mensagem: str, venda_id: int|None)
    Em erro faz rollback de toda a operação.
    """
    with conectar() as conn:
        cursor = conn.cursor()
        try:
            for item in lista_produtos:
                cursor.execute("SELECT quantidade, produto FROM produtos WHERE id = ?", (item['id'],))
                res = cursor.fetchone()
                if not res or res[0] < item['qtd']:
                    return False, f"Estoque insuficiente: {res[1] if res else 'Produto não encontrado'}", None
           
            total_bruto = sum(p['qtd'] * p['preco'] for p in lista_produtos)
            total_liquido = round(total_bruto - desconto_total, 2)
            
            cursor.execute("""INSERT INTO vendas (cliente_id, valor_bruto, desconto, valor_total, forma_pagamento, qtd_parcelas)
                              VALUES (?, ?, ?, ?, ?, ?)""", (cliente_id, total_bruto, desconto_total, total_liquido, forma_pgto, parcelas))
            venda_id = cursor.lastrowid

            for p in lista_produtos:
                cursor.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?", (p['qtd'], p['id']))
                cursor.execute("INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, subtotal) VALUES (?, ?, ?, ?, ?)",
                               (venda_id, p['id'], p['qtd'], p['preco'], p['qtd'] * p['preco']))

            valor_parcela = round(total_liquido / parcelas, 2)
            for i in range(parcelas):
                if i == parcelas - 1:
                    valor_parcela = round(total_liquido - (valor_parcela * (parcelas - 1)), 2)
                
                vencimento = adicionar_meses(datetime.now(), i).strftime("%Y-%m-%d")
                
                cursor.execute("""
                    INSERT INTO financeiro (
                        tipo, venda_id, cliente_id, id_agrupador, entidade_nome, descricao, valor, valor_base, 
                        parcelas_atual, total_parcelas, data_vencimento, categoria, recorrencia, status
                    ) VALUES ('Receita', ?, ?, ?, (SELECT nome FROM clientes WHERE id=?), ?, ?, ?, ?, ?, ?, 'Venda', 'Parcelado', 'Pendente')
                """, (venda_id, cliente_id, venda_id, cliente_id, f"Venda #{venda_id} - Parcela {i+1}/{parcelas}", 
                      valor_parcela, valor_parcela, i+1, parcelas, vencimento))

            conn.commit()
            return True, "Venda finalizada com sucesso!", venda_id
        except Exception as e:
            conn.rollback()
            return False, f"Erro ao verificar venda: {str(e)}", None

def baixar_estoque_venda(venda_id, cursor=None):
    """
    Baixa estoque dos itens da venda (uma única vez).
    Chamado ao confirmar pagamento em Gerenciar Receitas.
    Retorno: (sucesso, mensagem)
    """
    def _executar(cur, conn):
        cur.execute("SELECT status_venda, estoque_baixado FROM vendas WHERE id = ?", (venda_id,))
        row = cur.fetchone()
        if not row:
            return False, "Venda não encontrada."
        if row[0] == config.STATUS_VENDA_CANCELADA:
            return False, "Venda cancelada."
        if row[1]:
            return True, "Estoque já baixado para esta venda."

        cur.execute("SELECT produto_id, quantidade FROM itens_venda WHERE venda_id = ?", (venda_id,))
        itens = cur.fetchall()
        if not itens:
            return False, "Venda sem itens."

        for produto_id, qtd in itens:
            cur.execute("SELECT quantidade, produto FROM produtos WHERE id = ?", (produto_id,))
            res = cur.fetchone()
            if not res or res[0] < qtd:
                return False, f"Estoque insuficiente ao confirmar pagamento: {res[1] if res else 'Produto não encontrado'}"
            cur.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?", (qtd, produto_id))

        cur.execute(
            "UPDATE vendas SET estoque_baixado = 1, status_venda = ? WHERE id = ?",
            (config.STATUS_VENDA_FINALIZADA, venda_id),
        )
        return True, "Estoque baixado."

    if cursor is not None:
        ok, msg = _executar(cursor, None)
        return ok, msg

    with conectar() as conn:
        try:
            ok, msg = _executar(conn.cursor(), conn)
            if ok:
                conn.commit()
            else:
                conn.rollback()
            return ok, msg
        except Exception as e:
            conn.rollback()
            return False, f"Erro ao baixar estoque: {str(e)}"


def cancelar_venda(venda_id, motivo="Cancelamento solicitado"):
    """
    Cancela uma venda, devolve os itens ao estoque e 
    cancela as parcelas pendentes no financeiro.
    """
    with conectar() as conn:
        cursor = conn.cursor()
        try:
            # 1. Verificar se a venda existe e se já não está cancelada
            cursor.execute("SELECT status_venda FROM vendas WHERE id = ?", (venda_id,))
            venda = cursor.fetchone()
            
            if not venda:
                return False, "Venda não encontrada."
            if venda[0] == 'Cancelada':
                return False, "Esta venda já foi cancelada anteriormente."
          
            cursor.execute("SELECT estoque_baixado FROM vendas WHERE id = ?", (venda_id,))
            estoque_baixado = cursor.fetchone()[0]
            if estoque_baixado:
                cursor.execute("SELECT produto_id, quantidade FROM itens_venda WHERE venda_id = ?", (venda_id,))
                for produto_id, qtd in cursor.fetchall():
                    cursor.execute(
                        "UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?",
                        (qtd, produto_id),
                    )

            # 3. Tratar o Financeiro
            # Cancelamos parcelas que ainda não foram pagas
            cursor.execute("""
                UPDATE financeiro 
                SET status = 'Cancelado', descricao = descricao || ' (VENDA CANCELADA)'
                WHERE venda_id = ? AND status != 'Pago'
            """, (venda_id,))

            # Nota: Parcelas já PAGAS permanecem como 'Pago', mas a venda muda de status.
            # Se desejar estornar o dinheiro já pago, seria necessário criar uma 'Despesa' de estorno.

            # 4. Atualizar o status da venda
            cursor.execute("UPDATE vendas SET status_venda = 'Cancelada' WHERE id = ?", (venda_id,))

            cursor.execute("SELECT cliente_id FROM vendas WHERE id = ?", (venda_id,))
            cliente_id = cursor.fetchone()[0]
            cursor.execute(
                """INSERT INTO cliente_interacoes
                   (cliente_id, tipo_contato, assunto, detalhes, vendedor_responsavel)
                   VALUES (?, ?, ?, ?, ?)""",
                (cliente_id, "Presencial", "Cancelamento de Venda",
                 f"Venda #{venda_id} cancelada. Motivo: {motivo}", "Sistema"),
            )

            conn.commit()
            return True, f"Venda #{venda_id} cancelada e estoque atualizado."
 
        except Exception as e:
            conn.rollback()
            return False, f"Erro ao cancelar venda: {str(e)}"

def obter_itens_venda(venda_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT iv.produto_id, p.produto, p.cor, p.tamanho, iv.quantidade, iv.preco_unitario, iv.subtotal
            FROM itens_venda iv
            JOIN produtos p ON iv.produto_id = p.id
            WHERE iv.venda_id = ?
        """, (venda_id,))
        return cursor.fetchall()

def obter_venda_por_id(venda_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.id, v.cliente_id, c.nome, c.telefone, c.cpf, v.valor_bruto, v.desconto, v.valor_total,
                   v.forma_pagamento, v.qtd_parcelas, v.data_venda, v.status_venda
            FROM vendas v
            JOIN clientes c ON v.cliente_id = c.id
            WHERE v.id = ?
        """, (venda_id,))
        return cursor.fetchone()

def atualizar_venda_comercial(venda_id, cliente_id, lista_produtos, desconto_total=0):
    """Atualiza itens e totais da venda; estoque é recalculado. Financeiro pago exige ajuste manual."""
    with conectar() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT status_venda, estoque_baixado FROM vendas WHERE id = ?", (venda_id,))
            row = cursor.fetchone()
            if not row:
                return False, "Venda não encontrada."
            if row[0] == 'Cancelada':
                return False, "Venda cancelada não pode ser editada."
            estoque_baixado = bool(row[1])

            cursor.execute("SELECT COUNT(*) FROM financeiro WHERE venda_id = ? AND status = 'Pago'", (venda_id,))
            if cursor.fetchone()[0] > 0:
                return False, "Há parcelas já recebidas. Ajuste pagamentos em Gerenciar Receitas antes de alterar itens."

            if estoque_baixado:
                cursor.execute("SELECT produto_id, quantidade FROM itens_venda WHERE venda_id = ?", (venda_id,))
                for produto_id, qtd in cursor.fetchall():
                    cursor.execute("UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?", (qtd, produto_id))
            cursor.execute("DELETE FROM itens_venda WHERE venda_id = ?", (venda_id,))

            for item in lista_produtos:
                cursor.execute("SELECT quantidade, produto FROM produtos WHERE id = ?", (item['id'],))
                res = cursor.fetchone()
                if not res or res[0] < item['qtd']:
                    conn.rollback()
                    return False, f"Estoque insuficiente: {res[1] if res else 'Produto não encontrado'}"
                if estoque_baixado:
                    cursor.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?", (item['qtd'], item['id']))
                cursor.execute("""
                    INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (venda_id, item['id'], item['qtd'], item['preco'], item['qtd'] * item['preco']))

            total_bruto = sum(p['qtd'] * p['preco'] for p in lista_produtos)
            total_liquido = round(total_bruto - desconto_total, 2)
            cursor.execute("SELECT forma_pagamento, qtd_parcelas FROM vendas WHERE id = ?", (venda_id,))
            fp, qp = cursor.fetchone()
            cursor.execute("""
                UPDATE vendas SET cliente_id = ?, valor_bruto = ?, desconto = ?, valor_total = ?
                WHERE id = ?
            """, (cliente_id, total_bruto, desconto_total, total_liquido, venda_id))
            parcelas = qp or 1
            cursor.execute("DELETE FROM financeiro WHERE venda_id = ? AND status != 'Pago'", (venda_id,))
            valor_parcela = round(total_liquido / parcelas, 2)
            cursor.execute("SELECT nome FROM clientes WHERE id = ?", (cliente_id,))
            nome_cli = cursor.fetchone()[0]
            for i in range(parcelas):
                if i == parcelas - 1:
                    valor_parcela = round(total_liquido - (valor_parcela * (parcelas - 1)), 2)
                vencimento = adicionar_meses(datetime.now(), i).strftime("%Y-%m-%d")
                cursor.execute("""
                    INSERT INTO financeiro (
                        tipo, venda_id, cliente_id, id_agrupador, entidade_nome, descricao, valor, valor_base,
                        parcelas_atual, total_parcelas, data_vencimento, categoria, recorrencia, status
                    ) VALUES ('Receita', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Venda', 'Parcelado', 'Pendente')
                """, (venda_id, cliente_id, venda_id, nome_cli, f"Venda #{venda_id} - Parcela {i+1}/{parcelas}",
                      valor_parcela, valor_parcela, i + 1, parcelas, vencimento))

            conn.commit()
            return True, "Venda atualizada com sucesso."
        except Exception as e:
            conn.rollback()
            return False, f"Erro ao atualizar venda: {str(e)}"

def obter_financeiro_por_id(financeiro_id):
    with conectar() as conn:
        return conn.execute("SELECT * FROM financeiro WHERE id = ?", (financeiro_id,)).fetchone()

def listar_parcelas_venda(venda_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, parcelas_atual, total_parcelas, data_vencimento, data_pagamento, valor, valor_pago, status
            FROM financeiro WHERE venda_id = ? AND tipo = 'Receita' ORDER BY parcelas_atual ASC
        """, (venda_id,))
        return cursor.fetchall()

def registrar_pagamento_financeiro(financeiro_id, valor_pago, forma_pgto, data_pagamento=None, status=None):
    """
    Baixa total ou parcial de título (receita ou despesa).
    valor_pago é SOMADO ao já registrado — suporta múltiplos recebimentos parciais.
    """
    hoje = datetime.now().strftime("%Y-%m-%d")
    data_pagamento = data_pagamento or hoje
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor, valor_pago, tipo FROM financeiro WHERE id = ?", (financeiro_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Lançamento não encontrado."
        valor_titulo, valor_ja_pago, tipo = row
        valor_pago = round(float(valor_pago), 2)
        total_pago = round((valor_ja_pago or 0) + valor_pago, 2)
        if total_pago > valor_titulo + 0.01:
            return False, "Valor pago excede o saldo do título."
        if status is None:
            if total_pago >= valor_titulo - 0.01:
                status = 'Pago'
            elif total_pago > 0:
                status = 'Pendente'
            else:
                status = 'Pendente'
        cursor.execute("""
            UPDATE financeiro SET valor_pago = ?, status = ?, data_pagamento = ?, forma_pagamento = ?
            WHERE id = ?
        """, (total_pago, status, data_pagamento if total_pago > 0 else None, forma_pgto, financeiro_id))
        conn.commit()
        return True, "Pagamento registrado."

# --- Financeiro e relatórios ---
def obter_todos_registros_financeiros():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, tipo, entidade_nome, descricao, valor, data_vencimento, data_pagamento, forma_pagamento, categoria, recorrencia, status FROM financeiro ORDER BY data_vencimento ASC")
        return cursor.fetchall()

def quitar_titulo_financeiro(financeiro_id, forma_pgto):
    with conectar() as conn:
        row = conn.execute("SELECT valor, valor_pago FROM financeiro WHERE id = ?", (financeiro_id,)).fetchone()
        if not row:
            return False, "Lançamento não encontrado."
        saldo = round(row[0] - (row[1] or 0), 2)
        if saldo <= 0:
            saldo = row[0]
    return registrar_pagamento_financeiro(financeiro_id, saldo, forma_pgto)

# --- Insere uma nova despesa no financeiro com recorrência e/ou parcelamento mensal ---
def cadastrar_despesa(fornecedor, descricao, categoria, valor, recorrencia, vencimento, forma_pagamento, status, parcelas=1,
                      data_lancamento=None, data_pagamento=None, tipo_encargos='Valor Fixo', valor_encargos=0.0,
                      tipo_descontos='Valor Fixo', valor_descontos=0.0, valor_base=None, fornecedor_id=None, valor_pago=0.0):

# --- Cria lançamentos de saída financeira no sistema, permitindo o rateio de valores em várias parcelas mensais ---
    def normalizar_data(data_str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try: return datetime.strptime(data_str, fmt)
            except ValueError: continue
        raise ValueError(f"Formato inválido: {data_str}")

    data_inicial = normalizar_data(vencimento)
    if valor_base is None: valor_base = valor

    encargos_total = round(valor_base * (valor_encargos / 100), 2) if tipo_encargos == 'Porcentagem' else round(valor_encargos, 2)
    descontos_total = round(valor_base * (valor_descontos / 100), 2) if tipo_descontos == 'Porcentagem' else round(valor_descontos, 2)
    valor_final = round(valor_base + encargos_total - descontos_total, 2)
    valor_parc = round(valor_final / parcelas, 2) if recorrencia == 'Parcelar' else valor_final

    data_lancamento = datetime.now().strftime('%Y-%m-%d') if data_lancamento is None else normalizar_data(data_lancamento).strftime('%Y-%m-%d')
    if data_pagamento: data_pagamento = normalizar_data(data_pagamento).strftime('%Y-%m-%d')

    if fornecedor_id and not fornecedor:
        fornecedor = obter_nome_contato(fornecedor_id) or fornecedor
    vp_inicial = round(float(valor_pago or 0), 2) if status == 'Pago' else 0.0

    with conectar() as conn:
        cursor = conn.cursor()
        id_agrupador = None
        for i in range(parcelas):
            data_venc = adicionar_meses(data_inicial, i).strftime("%Y-%m-%d")
            vp = vp_inicial if i == 0 else 0.0
            st = status if i == 0 else 'Pendente'
            dp = data_pagamento if i == 0 and vp > 0 else None
            cursor.execute("""
                INSERT INTO financeiro (tipo, fornecedor_id, entidade_nome, descricao, valor, valor_base, valor_pago,
                                       parcelas_atual, total_parcelas, data_vencimento, data_pagamento, forma_pagamento,
                                       categoria, status, recorrencia, data_lancamento, tipo_encargos, valor_encargos,
                                       tipo_descontos, valor_descontos, id_agrupador)
                VALUES ('Despesa', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fornecedor_id, fornecedor, descricao if parcelas == 1 else f"{descricao} ({i+1}/{parcelas})",
                  valor_parc, valor_base, vp, i + 1, parcelas, data_venc, dp, forma_pagamento, categoria, st,
                  recorrencia, data_lancamento, tipo_encargos, valor_encargos, tipo_descontos, valor_descontos, id_agrupador))
            if id_agrupador is None:
                id_agrupador = cursor.lastrowid
                cursor.execute("UPDATE financeiro SET id_agrupador = ? WHERE id = ?", (id_agrupador, id_agrupador))
        conn.commit()
        return True, "Despesa cadastrada com sucesso!"
def listar_despesas():
    # --- Retorna todas as despesas registradas no sistema com seus detalhes ---
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, entidade_nome, descricao, valor, categoria, data_vencimento, 
                   forma_pagamento, status, parcelas_atual, total_parcelas
            FROM financeiro 
            WHERE tipo = 'Despesa'
            ORDER BY data_vencimento DESC
        """)
        return cursor.fetchall()

def atualizar_despesa(despesa_id, **kwargs):
    # --- Modifica os dados de uma despesa existente de forma flexível ---
    with conectar() as conn:
        cursor = conn.cursor()
        campos = ", ".join(f"{k} = ?" for k in kwargs.keys())
        valores = list(kwargs.values()) + [despesa_id]
        cursor.execute(f"UPDATE financeiro SET {campos} WHERE id = ? AND tipo = 'Despesa'", valores)
        conn.commit()

def deletar_despesa(despesa_id):
    # --- Remove uma despesa do sistema (incluindo todas as parcelas relacionadas) ---
    try:
        with conectar() as conn:
            cursor = conn.cursor()
            # Busca o número total de parcelas para deletar todas
            cursor.execute("""
                SELECT id, total_parcelas FROM financeiro 
                WHERE id = ? AND tipo = 'Despesa'
            """, (despesa_id,))
            resultado = cursor.fetchone()
            
            if not resultado:
                return False, "Despesa não encontrada."
            
            cursor.execute("SELECT id_agrupador FROM financeiro WHERE id = ? AND tipo = 'Despesa'", (despesa_id,))
            agr = cursor.fetchone()
            if agr and agr[0]:
                cursor.execute("DELETE FROM financeiro WHERE tipo = 'Despesa' AND id_agrupador = ?", (agr[0],))
            else:
                cursor.execute("DELETE FROM financeiro WHERE id = ? AND tipo = 'Despesa'", (despesa_id,))
            
            conn.commit()
            return True, "Despesa deletada com sucesso!"
    except Exception as e:
        return False, f"Erro ao deletar despesa: {str(e)}"

def buscar_despesa_por_termo(termo):
    # --- Busca despesas por fornecedor ou descrição ---
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, entidade_nome, descricao, valor, categoria, data_vencimento, 
                   forma_pagamento, status, parcelas_atual, total_parcelas
            FROM financeiro 
            WHERE tipo = 'Despesa' AND (
                entidade_nome LIKE ? OR descricao LIKE ?
            )
            ORDER BY data_vencimento DESC
        """, (f"%{termo}%", f"%{termo}%"))
        return cursor.fetchall()

def obter_despesa_por_id(despesa_id):
    # --- Retorna os dados de uma despesa específica ---
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, entidade_nome, descricao, valor, categoria, data_vencimento, 
                   forma_pagamento, status, parcelas_atual, total_parcelas
            FROM financeiro 
            WHERE id = ? AND tipo = 'Despesa'
        """, (despesa_id,))
        return cursor.fetchone()

def exibir_produtos_com_fornecedor():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.sku, p.tipo, p.produto, p.cor, p.tamanho, p.precocusto, p.precovenda, p.quantidade,
                   p.categoria, p.material, COALESCE(c.nome, p.fornecedor, ''), p.status_item, p.foto
            FROM produtos p
            LEFT JOIN clientes c ON p.fornecedor_id = c.id
            ORDER BY p.produto ASC
        """)
        return cursor.fetchall()

def _saldo_titulo(valor, valor_pago):
    """Saldo em aberto de um título (valor nominal menos amortizações)."""
    return round(float(valor or 0) - float(valor_pago or 0), 2)


def listar_titulos_abertos(tipo, limite=200):
    """
    Contas a receber (Receita) ou a pagar (Despesa) com saldo pendente.
    Ordenação por vencimento — padrão de relatórios financeiros do varejo.
    """
    with conectar() as conn:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(config.STATUS_FINANCEIRO_ABERTO))
        cursor.execute(f"""
            SELECT id, entidade_nome, descricao, valor, valor_pago, data_vencimento, status,
                   (valor - COALESCE(valor_pago, 0)) AS saldo
            FROM financeiro
            WHERE tipo = ? AND status IN ({placeholders})
            ORDER BY date(data_vencimento) ASC
            LIMIT ?
        """, (tipo, *config.STATUS_FINANCEIRO_ABERTO, limite))
        return cursor.fetchall()


def dashboard_resumo():
    """Indicadores rápidos para o painel inicial (KPIs operacionais)."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT produto, quantidade FROM produtos WHERE quantidade < ? AND status_item != 'Indisponível'",
            (config.LIMITE_ESTOQUE_ALERTA,),
        )
        alertas = cursor.fetchall()
        cursor.execute("""
            SELECT COALESCE(SUM(valor - COALESCE(valor_pago, 0)), 0)
            FROM financeiro WHERE tipo = ? AND status IN ('Pendente', 'Atrasado')
        """, (config.TIPO_RECEITA,))
        a_receber = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COALESCE(SUM(valor - COALESCE(valor_pago, 0)), 0)
            FROM financeiro WHERE tipo = ? AND status IN ('Pendente', 'Atrasado')
        """, (config.TIPO_DESPESA,))
        a_pagar = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vendas WHERE status_venda = ?", (config.STATUS_VENDA_FINALIZADA,))
        vendas_ok = cursor.fetchone()[0]
        return {
            "alertas_estoque": alertas,
            "total_a_receber": float(a_receber or 0),
            "total_a_pagar": float(a_pagar or 0),
            "vendas_finalizadas": vendas_ok,
        }

def relatorio_vendas_geral():
    """Extrato de vendas com tipo predominante dos itens (Calçados / Confecções)."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.id, c.nome, v.valor_total, v.forma_pagamento, v.qtd_parcelas, v.data_venda, v.vendedor, v.status_venda,
                   COALESCE(
                       (SELECT p.tipo FROM itens_venda iv
                        JOIN produtos p ON iv.produto_id = p.id
                        WHERE iv.venda_id = v.id
                        GROUP BY p.tipo ORDER BY SUM(iv.quantidade) DESC LIMIT 1),
                       '—'
                   ) AS tipo_venda
            FROM vendas v
            JOIN clientes c ON v.cliente_id = c.id
            ORDER BY v.data_venda DESC
        """)
        return cursor.fetchall()


# --- Anotações (persistência em SQLite) ---
def listar_anotacoes(ordem_alfabetica=True):
    sql = "SELECT id, titulo, conteudo, data_atualizacao FROM anotacoes"
    sql += " ORDER BY titulo ASC" if ordem_alfabetica else " ORDER BY data_atualizacao DESC"
    with conectar() as conn:
        return conn.execute(sql).fetchall()


def buscar_anotacao_por_titulo(titulo):
    with conectar() as conn:
        return conn.execute(
            "SELECT id, titulo, conteudo, data_atualizacao FROM anotacoes WHERE titulo LIKE ?",
            (f"%{titulo}%",),
        ).fetchall()


def salvar_anotacao(titulo, conteudo, anotacao_id=None):
    titulo = (titulo or "").strip()
    if not titulo:
        return False, "Informe um título para a nota."
    try:
        with conectar() as conn:
            if anotacao_id:
                conn.execute(
                    "UPDATE anotacoes SET titulo = ?, conteudo = ?, data_atualizacao = CURRENT_TIMESTAMP WHERE id = ?",
                    (titulo, conteudo, anotacao_id),
                )
            else:
                conn.execute(
                    "INSERT INTO anotacoes (titulo, conteudo) VALUES (?, ?)",
                    (titulo, conteudo),
                )
            conn.commit()
        return True, "Nota salva."
    except sqlite3.IntegrityError:
        return False, "Já existe uma nota com este título."


def excluir_anotacao(anotacao_id):
    with conectar() as conn:
        conn.execute("DELETE FROM anotacoes WHERE id = ?", (anotacao_id,))
        conn.commit()
    return True, "Nota excluída."


def obter_anotacao_por_id(anotacao_id):
    with conectar() as conn:
        return conn.execute(
            "SELECT id, titulo, conteudo, data_atualizacao FROM anotacoes WHERE id = ?",
            (anotacao_id,),
        ).fetchone()
def fluxo_caixa_mensal(mes, ano):
    """Consolida entradas e saídas do período para o fluxo de caixa."""
    with conectar() as conn:
        cursor = conn.cursor()
        filtro = f"{ano}-{str(mes).zfill(2)}%"
        
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN tipo='Receita' AND status='Pago' THEN valor_pago ELSE 0 END), 0) as entradas,
                COALESCE(SUM(CASE WHEN tipo='Despesa' AND status='Pago' THEN valor_pago ELSE 0 END), 0) as saidas,
                COALESCE(SUM(CASE WHEN tipo='Receita' AND status='Pendente' THEN (valor - valor_pago) ELSE 0 END), 0) as a_receber,
                COALESCE(SUM(CASE WHEN tipo='Despesa' AND status='Pendente' THEN (valor - valor_pago) ELSE 0 END), 0) as a_pagar
            FROM financeiro 
            WHERE data_vencimento LIKE ? OR data_pagamento LIKE ?
        """, (filtro, filtro))
        return cursor.fetchone()

def lancar_despesa(descricao, valor, categoria, vencimento, parcelas=1, fornecedor="Estoque"):
    """Lançamento rápido de despesa (ex.: reposição de estoque)."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    if isinstance(vencimento, str) and "/" in vencimento:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                vencimento = datetime.strptime(vencimento, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
    else:
        vencimento = hoje
    return cadastrar_despesa(
        fornecedor, descricao, categoria, valor, 'Não Recorrente', vencimento,
        'Dinheiro', 'Pago', parcelas=parcelas, data_pagamento=hoje, valor_pago=valor
    )

def listar_itens():
    """Recupera produtos disponíveis para o checkout."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, produto, cor, tamanho, precocusto, precovenda, quantidade, foto "
            "FROM produtos WHERE status_item != 'Indisponível' ORDER BY produto ASC"
        )
        return cursor.fetchall()

if __name__ == "__main__":
    criar_tabelas()
    print("✓ Banco de Dados Ale Sapatilhas Vs4.8.1 - Ativo.")