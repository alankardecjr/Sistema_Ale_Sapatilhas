"""
test_sistema.py — Testes automatizados (sem interface gráfica).

Executa fluxos críticos do ERP em banco SQLite temporário.
Uso: python test_sistema.py
"""

import os
import sys
import tempfile
import traceback

# Garante import a partir da pasta do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
import config
import ui_utils


class ResultadoTestes:
    """Acumula sucessos e falhas da bateria de testes."""

    def __init__(self):
        self.ok = 0
        self.falhas = []

    def registrar(self, nome, condicao, detalhe=""):
        if condicao:
            self.ok += 1
            print(f"  [OK] {nome}")
        else:
            self.falhas.append((nome, detalhe))
            print(f"  [FALHA] {nome}: {detalhe}")

    def resumo(self):
        total = self.ok + len(self.falhas)
        print(f"\n{'='*50}")
        print(f"Total: {self.ok}/{total} testes passaram")
        if self.falhas:
            print("\nFalhas:")
            for nome, det in self.falhas:
                print(f"  - {nome}: {det}")
            return False
        print("Todos os testes passaram.")
        return True


def configurar_banco_teste():
    """Aponta o módulo database para um arquivo temporário isolado."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db.DB_NAME = path
    db.criar_tabelas()
    return path


def test_ui_utils(r):
    """Valida utilitários de UI e mapeamentos."""
    r.registrar("tipo Calçado -> BD", ui_utils.tipo_produto_para_bd("Calçado") == "Calçados")
    r.registrar("tipo Vestuário -> BD", ui_utils.tipo_produto_para_bd("Vestuário") == "Confecções")
    r.registrar("filtro data hoje", ui_utils.filtro_data_periodo("Dia", "19/05/2026") in (True, False))
    r.registrar("paleta tem chaves", "bg_fundo" in ui_utils.get_paleta())


def test_cliente_produto(r):
    """Cadastro de cliente, produto e variação."""
    cid = db.cadastrar_cliente(
        "Cliente Teste", "11122233344", "11999990000", "t@t.com",
        None, 38, "Rua A", "Centro", "SP", "01000", "obs", 500, "Cliente",
    )
    r.registrar("cadastrar cliente", bool(cid))

    sku1 = "SAP0001PRE"
    ok = db.cadastrar_produto(
        sku1, "Calçados", "Sapatilha Teste", "Preto", "37",
        50, 120, 5, "Sapatilhas", "Couro", "Forn X", "",
    )
    r.registrar("cadastrar produto", ok)

    sku2 = "SAP0002AZU"
    ok2 = db.cadastrar_produto(
        sku2, "Calçados", "Sapatilha Teste", "Azul", "37",
        50, 120, 3, "Sapatilhas", "Couro", "", "",
    )
    r.registrar("cadastrar variação cor", ok2)

    itens = db.listar_itens()
    r.registrar("listar_itens com foto", len(itens) >= 2 and len(itens[0]) >= 8)


def test_venda_pdv_estoque(r, cid):
    """PDV pendente não baixa estoque; baixa só após pagamento."""
    produtos = db.listar_itens()
    if not produtos:
        r.registrar("pdv estoque - produtos", False, "sem produtos")
        return
    pid = produtos[0][0]
    qtd_antes = None
    with db.conectar() as conn:
        qtd_antes = conn.execute("SELECT quantidade FROM produtos WHERE id=?", (pid,)).fetchone()[0]

    lista = [{"id": pid, "qtd": 1, "preco": float(produtos[0][5])}]
    res, msg, vid = db.realizar_venda_pdv(cid, lista, 0)
    r.registrar("realizar_venda_pdv", res and vid is not None, msg)
    if not vid:
        return

    with db.conectar() as conn:
        qtd_apos_pdv = conn.execute("SELECT quantidade FROM produtos WHERE id=?", (pid,)).fetchone()[0]
        eb = conn.execute("SELECT estoque_baixado FROM vendas WHERE id=?", (vid,)).fetchone()[0]
    r.registrar("pdv não baixa estoque", qtd_apos_pdv == qtd_antes and eb == 0)

    if vid:
        ok, msg_b = db.baixar_estoque_venda(vid)
        with db.conectar() as conn:
            qtd_apos_baixa = conn.execute("SELECT quantidade FROM produtos WHERE id=?", (pid,)).fetchone()[0]
            eb2 = conn.execute("SELECT estoque_baixado FROM vendas WHERE id=?", (vid,)).fetchone()[0]
        r.registrar("baixar_estoque_venda", ok and eb2 == 1, msg_b)
        r.registrar("estoque reduzido após pagamento", qtd_apos_baixa == qtd_antes - 1)


def test_venda(r, cid):
    """Venda atômica com baixa de estoque."""
    produtos = db.listar_itens()
    if not produtos:
        r.registrar("venda - estoque", False, "sem produtos")
        return None
    pid = produtos[0][0]
    lista = [{"id": pid, "qtd": 1, "preco": float(produtos[0][5])}]
    res, msg, vid = db.realizar_venda_segura(cid, lista, "PIX", 1, 0)
    r.registrar("realizar_venda_segura", res and vid is not None, msg)
    if vid:
        v = db.obter_venda_por_id(vid)
        r.registrar("obter_venda_por_id", v is not None)
        itens_v = db.obter_itens_venda(vid)
        r.registrar("obter_itens_venda", len(itens_v) >= 1)
        parcelas = db.listar_parcelas_venda(vid)
        r.registrar("listar_parcelas_venda", len(parcelas) >= 1)
    return vid


def test_despesa_receita(r):
    """Lançamento financeiro de despesa."""
    ok, msg = db.cadastrar_despesa(
        "Fornecedor Opcional", "Despesa teste", "Outros", 100.0,
        "Não Recorrente", "2026-12-31", "PIX", "Pendente", 1,
        data_lancamento="2026-05-19", valor_pago=0,
    )
    despesas = db.listar_despesas()
    r.registrar("cadastrar despesa sem vínculo", ok and len(despesas) >= 1, msg)


def test_atualizacao_produto(r):
    """Atualização parcial de estoque."""
    prods = db.exibir_produtos()
    if not prods:
        r.registrar("atualizar produto", False, "lista vazia")
        return
    pid = prods[0][0]
    db.atualizar_produto(pid, quantidade=99, status_item="Disponível")
    with db.conectar() as conn:
        q = conn.execute("SELECT quantidade FROM produtos WHERE id=?", (pid,)).fetchone()[0]
    r.registrar("atualizar_produto quantidade", q == 99)


def test_anotacoes(r):
    ok, msg = db.salvar_anotacao("Nota Teste A", "Conteúdo da nota")
    r.registrar("salvar anotacao", ok, msg)
    lista = db.listar_anotacoes()
    r.registrar("listar anotacoes", any(n[1] == "Nota Teste A" for n in lista))
    busca = db.buscar_anotacao_por_titulo("Teste")
    r.registrar("buscar anotacao", len(busca) >= 1)
    if busca:
        db.excluir_anotacao(busca[0][0])


def test_senha_fluxo_config(r):
    """Senha lida/gravada em arquivo local temporário."""
    import json
    import config as cfg
    path_antigo = cfg.SECRETS_PATH
    senha_antiga = cfg.SENHA_FLUXO_CAIXA
    tmp = os.path.join(tempfile.gettempdir(), "test_secrets_erp.json")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"senha_fluxo_caixa": "teste_p4_99"}, f)
        cfg.SECRETS_PATH = tmp
        cfg.SENHA_FLUXO_CAIXA = cfg.obter_senha_fluxo_caixa()
        r.registrar("obter senha arquivo", cfg.SENHA_FLUXO_CAIXA == "teste_p4_99")
        ok, _ = cfg.salvar_senha_fluxo_caixa("nova_p4_88")
        r.registrar("salvar senha arquivo", ok and cfg.obter_senha_fluxo_caixa() == "nova_p4_88")
    finally:
        cfg.SECRETS_PATH = path_antigo
        cfg.SENHA_FLUXO_CAIXA = senha_antiga
        if os.path.exists(tmp):
            os.remove(tmp)


def test_cancelar_venda(r, cid):
    produtos = db.listar_itens()
    if not produtos:
        return
    pid = produtos[0][0]
    with db.conectar() as conn:
        q0 = conn.execute("SELECT quantidade FROM produtos WHERE id=?", (pid,)).fetchone()[0]

    res, _, vid = db.realizar_venda_pdv(cid, [{"id": pid, "qtd": 1, "preco": 50.0}], 0)
    if not res:
        r.registrar("cancelar - criar venda", False)
        return

    ok, msg = db.cancelar_venda(vid)
    with db.conectar() as conn:
        q1 = conn.execute("SELECT quantidade FROM produtos WHERE id=?", (pid,)).fetchone()[0]
        st = conn.execute("SELECT status_venda FROM vendas WHERE id=?", (vid,)).fetchone()[0]
    r.registrar("cancelar venda pendente", ok and st == "Cancelada", msg)
    r.registrar("cancelar pendente não altera estoque", q1 == q0)

    res2, _, vid2 = db.realizar_venda_pdv(cid, [{"id": pid, "qtd": 1, "preco": 50.0}], 0)
    if not res2:
        r.registrar("cancelar paga - criar venda", False)
        return
    db.baixar_estoque_venda(vid2)
    with db.conectar() as conn:
        q2 = conn.execute("SELECT quantidade FROM produtos WHERE id=?", (pid,)).fetchone()[0]
    ok2, msg2 = db.cancelar_venda(vid2)
    with db.conectar() as conn:
        q3 = conn.execute("SELECT quantidade FROM produtos WHERE id=?", (pid,)).fetchone()[0]
    r.registrar("cancelar paga devolve estoque", ok2 and q3 == q2 + 1, msg2)


def test_pdv_desconto(r, cid):
    produtos = db.listar_itens()
    if not produtos:
        return
    pid = produtos[0][0]
    lista = [{"id": pid, "qtd": 1, "preco": 100.0}]
    res, _, vid = db.realizar_venda_pdv(cid, lista, desconto_total=15.0)
    if res and vid:
        v = db.obter_venda_por_id(vid)
        r.registrar("pdv desconto gravado", v and abs(v[6] - 15.0) < 0.01 and abs(v[7] - 85.0) < 0.01)
        db.cancelar_venda(vid)


def test_imports_modulos(r):
    """Garante que módulos de tela importam sem erro."""
    try:
        import main  # noqa: F401
        import cadastro_produtos  # noqa: F401
        import cadastro_clientes  # noqa: F401
        import cadastro_vendas  # noqa: F401
        import gerenciar_despesas  # noqa: F401
        import gerenciar_receitas  # noqa: F401
        r.registrar("imports módulos UI", True)
    except Exception as e:
        r.registrar("imports módulos UI", False, str(e))


def main():
    print("Testes Alê Sapatilhas ERP — banco temporário\n")
    r = ResultadoTestes()
    db_path = None
    try:
        db_path = configurar_banco_teste()
        test_ui_utils(r)
        test_imports_modulos(r)
        test_cliente_produto(r)
        test_despesa_receita(r)
        test_atualizacao_produto(r)
        prods = db.exibir_clientes()
        cid = prods[0][0] if prods else db.cadastrar_cliente(
            "C2", "99988877766", "11888887777", "", None, 0,
            "", "", "", "", "", 0, "Cliente",
        )
        test_anotacoes(r)
        test_senha_fluxo_config(r)
        test_venda_pdv_estoque(r, cid)
        test_pdv_desconto(r, cid)
        test_cancelar_venda(r, cid)
        test_venda(r, cid)
    except Exception:
        traceback.print_exc()
        r.registrar("exceção não tratada", False, traceback.format_exc()[-200:])
    finally:
        if db_path and os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

    sucesso = r.resumo()
    sys.exit(0 if sucesso else 1)


if __name__ == "__main__":
    main()
