"""
populardb.py — Script de carga de dados de demonstração (seed).

Uso: python populardb.py
Apaga registros das tabelas principais e recria clientes/produtos/vendas de exemplo.
Não executar em produção com dados reais sem backup.
"""

import database
import random
from datetime import datetime

def popular_banco():
    print("=== Iniciando Povoamento do Banco de Dados AleSapatilhas.db ===")
    database.criar_tabelas()

    # --- Limpeza Controlada ---
    with database.conectar() as conn:
        cursor = conn.cursor()
        tabelas = ["pagamentos", "financeiro", "itens_venda", "vendas", "produtos", "clientes", "cliente_interacoes"]
        for tabela in tabelas:
            cursor.execute(f"DELETE FROM {tabela}")
        cursor.execute("DELETE FROM sqlite_sequence")  # Reseta chaves primárias AUTOINCREMENT
        conn.commit()
    print("✓ Banco de dados limpo com sucesso.")

    # --- FORNECEDORES ---
    # Cadastrando os fornecedores primeiro na tabela unificada de clientes para obter IDs reais
    print("-> Cadastrando fornecedores...")
    fornecedores_fake = [
        ("Fábrica A", "00111222000199", "11977776661", "contato@fabrical.com"),
        ("Fábrica B", "00111222000198", "11977776662", "contato@fabricab.com"),
        ("Fábrica C", "00111222000197", "11977776663", "contato@fabricac.com"),
        ("Imobiliária", "00111222000191", "1133334444", "aluguel@imobiliaria.com"),
        ("Coelba", "00111222000190", "08000112233", "atendimento@coelba.com"),
        ("Vivo", "00111222000189", "1058", "empresas@vivo.com"),
        ("Marketing Digital", "00111222000188", "11999998888", "agencia@marketing.com"),
    ]
    
    fornecedores_mapeados = {}
    for f_nome, f_cnpj, f_tel, f_email in fornecedores_fake:
        f_id = database.cadastrar_cliente(
            nome=f_nome, cpf=f_cnpj, tel=f_tel, email=f_email,
            niver=None, tam=None, endereco="", bairro="", city="", cep="",
            obs="Fornecedor homologado", limite=0, tipo="Fornecedor"
        )
        fornecedores_mapeados[f_nome] = f_id

    # --- CLIENTES (8 Clientes) ---
    print("-> Cadastrando clientes...")
    clientes_fake = [
        ("Maria Silva", "12345678901", "11988887771", "maria.silva@email.com", "1990-05-15", 35, "Rua das Flores, 10", "Centro", "São Paulo", "01001-000", "Cliente VIP", 500.0),
        ("Ana Oliveira", "23456789012", "11988887772", "ana.oliveira@email.com", "1985-08-20", 36, "Av. Brasil, 500", "Jardins", "São Paulo", "01430-000", "Pagamento em dia", 300.0),
        ("Carla Souza", "34567890123", "11988887773", "carla.souza@email.com", "1992-12-10", 37, "Rua Chile, 12", "Mooca", "São Paulo", "03102-000", "Gosta de cores vivas", 200.0),
        ("Juliana Lima", "45678901234", "11988887774", "juliana.lima@email.com", "1988-03-05", 34, "Rua B, 102", "Lapa", "São Paulo", "05001-000", "Novidades semanais", 100.0),
    ]

    for c in clientes_fake:
        database.cadastrar_cliente(
            nome=c[0], cpf=c[1], tel=c[2], email=c[3], niver=c[4], tam=c[5],
            endereco=c[6], bairro=c[7], city=c[8], cep=c[9], obs=c[10], limite=c[11],
            tipo='Cliente'  # Explicitado para segurança da assinatura
        )

    # --- PRODUTOS (15 Produtos) ---
    print("-> Cadastrando produtos...")
    produtos_fake = [
        ("SAP-001", "Calçados", "Sapatilha Verniz", "Preta", 35, 40.0, 89.90, 18, "Casual", "Sintético", "Fábrica A", "img01.jpg"),
        ("SAP-002", "Calçados", "Sapatilha Matelassê", "Bege", 36, 45.0, 95.00, 20, "Clássico", "Napa", "Fábrica B", "img02.jpg"),
        ("MUL-001", "Calçados", "Mule Bico Fino", "Caramelo", 37, 50.0, 110.00, 12, "Mule", "Couro", "Fábrica A", "img03.jpg"),
        ("SCP-001", "Calçados", "Scarpin Salto Baixo", "Nude", 38, 60.0, 150.00, 10, "Festa", "Verniz", "Fábrica B", "img05.jpg"),
        ("RAS-001", "Calçados", "Rasteira Pedraria", "Dourada", 35, 35.0, 75.00, 16, "Verão", "Sintético", "Fábrica D", "img08.jpg"),
        ("TEN-001", "Calçados", "Tênis Casual", "Branco", 38, 55.0, 129.90, 11, "Esportivo", "Couro", "Fábrica F", "img10.jpg"),
        ("SNE-001", "Calçados", "Tênis Esportivo", "Cinza", 39, 48.0, 139.90, 14, "Esportivo", "Malha", "Fábrica G", "img11.jpg"),
        ("MOC-001", "Calçados", "Mocassim Luxo", "Marrom", 37, 42.0, 129.00, 8, "Casual", "Couro", "Fábrica C", "img12.jpg"),
        ("BNK-001", "Calçados", "Bota Cano Curto", "Preto", 38, 70.0, 179.90, 9, "Inverno", "Couro", "Fábrica E", "img13.jpg"),
        ("ESP-001", "Calçados", "Espadrille Rafia", "Natural", 36, 38.0, 99.90, 7, "Verão", "Rafia", "Fábrica H", "img14.jpg"),
        ("SAP-003", "Calçados", "Sapatilha Soft", "Azul", 34, 40.0, 85.00, 5, "Casual", "Tecido", "Fábrica A", ""),
        ("RAS-002", "Calçados", "Chinelo Slim", "Rosa", 36, 20.0, 45.00, 25, "Verão", "Borracha", "Fábrica D", ""),
        ("SCP-002", "Calçados", "Scarpin Lux", "Vermelho", 37, 80.0, 199.00, 4, "Festa", "Nobuck", "Fábrica B", ""),
        ("TEN-002", "Calçados", "Tênis Plataforma", "Branco", 35, 65.0, 159.00, 6, "Casual", "Lona", "Fábrica F", ""),
        ("MOC-002", "Calçados", "Mocassim Drive", "Azul Marinho", 40, 55.0, 115.00, 10, "Casual", "Couro", "Fábrica C", ""),
    ]

    for p in produtos_fake:
        f_id = fornecedores_mapeados.get(p[10])  # Obtém o ID do fornecedor correspondente
        database.cadastrar_produto(
            sku=p[0], tipo=p[1], produto=p[2], cor=p[3], tamanho=p[4],
            precocusto=p[5], precovenda=p[6], quantidade=p[7], categoria=p[8],
            material=p[9], fornecedor=p[10], foto=p[11], fornecedor_id=f_id
        )

    # --- DESPESAS (5 Despesas estruturadas) ---
    print("-> Cadastrando despesas...")
    hoje = datetime.now().strftime("%Y-%m-%d")
    despesas_fake = [
        ("Imobiliária", "Aluguel Loja", "Infraestrutura", 3000.0, "Mensal", hoje, "PIX", "Pendente", 1),
        ("Coelba", "Energia", "Utilidades", 450.0, "Mensal", hoje, "Boleto", "Pendente", 1),
        ("Vivo", "Internet Fiber", "Comunicação", 150.0, "Mensal", hoje, "Cartão", "Pendente", 1),
        ("Fábrica A", "Compra de Estoque", "Produtos", 1200.0, "Parcelar", hoje, "Boleto", "Pendente", 3),
        ("Marketing Digital", "Anúncios Meta", "Marketing", 600.0, "Parcelar", hoje, "PIX", "Pendente", 2),
    ]

    for d in despesas_fake:
        f_id = fornecedores_mapeados.get(d[0])
        database.cadastrar_despesa(
            fornecedor=d[0],
            descricao=d[1],
            categoria=d[2],
            valor=d[3],
            recorrencia=d[4],
            vencimento=d[5],
            forma_pagamento=d[6],
            status=d[7],
            parcelas=d[8],
            fornecedor_id=f_id
        )

    # --- 5 VENDAS OPERACIONAIS ---
    print("-> Registrando 5 vendas estratégicas...")
    with database.conectar() as conn:
        cursor = conn.cursor()
        clientes_ids = [row[0] for row in cursor.execute("SELECT id FROM clientes WHERE tipo='Cliente'").fetchall()]
        produtos_pool = [{"id": r[0], "preco": r[1]} for r in cursor.execute("SELECT id, precovenda FROM produtos WHERE quantidade > 0").fetchall()]

    if clientes_ids and produtos_pool:
        for i in range(5):
            c_id = clientes_ids[i % len(clientes_ids)]
            
            # Venda 1 e 2 simulando parcelamento em Crediário 3x
            if i < 2:
                forma, parc = "Crediário", 3
            else:
                forma, parc = random.choice(["Pix", "Cartão"]), 1
            
            p_sorteado = random.choice(produtos_pool)
            itens = [{"id": p_sorteado["id"], "qtd": 1, "preco": p_sorteado["preco"]}]
            
            database.realizar_venda_segura(
                cliente_id=c_id, 
                lista_produtos=itens, 
                forma_pgto=forma, 
                parcelas=parc, 
                desconto_total=5.0
            )

    # --- AUDITORIA FINANCEIRA (Baixas de Demonstração) ---
    print("-> Simulando conciliação e auditoria financeira...")
    with database.conectar() as conn:
        cursor = conn.cursor()
        
        # Quita de forma controlada o primeiro título de Despesa encontrado
        id_desp_row = cursor.execute("SELECT id FROM financeiro WHERE tipo='Despesa' LIMIT 1").fetchone()
        if id_desp_row:
            database.quitar_titulo_financeiro(id_desp_row[0], "PIX")
            
        # Quita uma parcela de receita de forma parcial para fins de teste
        id_rec_row = cursor.execute("SELECT id FROM financeiro WHERE tipo='Receita' LIMIT 1").fetchone()
        if id_rec_row:
            database.quitar_titulo_financeiro(id_rec_row[0], "Pix")
        
    print("\n✅ Base de Testes AleSapatilhas.db populada e auditada com sucesso!")

if __name__ == "__main__":
    popular_banco()