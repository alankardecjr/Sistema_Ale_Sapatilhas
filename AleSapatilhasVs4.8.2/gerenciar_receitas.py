"""
gerenciar_receitas.py — Módulo financeiro de ENTRADAS (contas a receber).

Escopo:
  - Baixa de parcelas de vendas (venda_id no financeiro)
  - Receitas avulsas e ajustes com juros/descontos
  - Pagamento parcial: valor_pago acumulado até quitar o título

Complementa cadastro_vendas.py: o PDV gera a venda; aqui liquida-se o dinheiro.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import config
import database
import ui_utils


class JanelaGerenciarReceitas(tk.Toplevel):
    """
    Contas a receber: baixa de parcelas de vendas e receitas avulsas.

    on_sucesso: callback opcional (ex.: PDV após cadastrar pagamento).
    """
    def __init__(self, master, dados_receita=None, venda_id=None, on_sucesso=None):
        """Carrega receita, venda vinculada ou lista vazia para novo recebimento."""
        super().__init__(master)
        self.venda_id = venda_id
        self.on_sucesso = on_sucesso
        
        # --- Paleta de cores ---
        paleta = ui_utils.get_paleta()
        self.bg_fundo       = paleta["bg_fundo"]
        self.bg_card        = paleta["bg_card"]
        self.cor_borda      = paleta["cor_borda"]
        self.cor_texto      = paleta["cor_texto"]
        self.cor_lbl        = paleta["cor_lbl"]
        self.cor_destaque   = paleta["cor_destaque"]
        self.cor_btn_menu   = paleta["cor_btn_menu"]
        self.cor_btn_sair   = paleta["cor_btn_sair"]
        self.cor_btn_acao   = paleta["cor_btn_acao"]
        self.cor_hover_btn  = paleta["cor_hover_btn"]
        self.cor_hover_field = paleta["cor_hover_field"]

        self.title("Alê Sapatilhas - Gerenciamento de Receitas")
        self.configure(bg=self.bg_fundo)
        self.resizable(False, False)
        
        ui_utils.calcular_dimensoes_janela(self, largura_desejada=ui_utils.LARGURA_MODULO_PADRAO, altura_desejada=660)
        
        self.receita_id = dados_receita[0] if dados_receita else None
        self.cliente_selecionado_id = None
        self._liquido_editado_manual = False
        
        self.list_formas = ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Crediário", "Boleto", "Outros"]
        self.list_categorias = ["Venda", "Ajuste de Caixa", "Rendimento", "Outros"]
        self.list_recorrencia = ["Não Recorrente", "Fixo Mensal", "Parcelado"]
        self.list_status = ["Pendente", "Pago", "Atrasado", "Cancelado"]

        self.setup_styles()
        self.criar_widgets()
        
        if dados_receita:
            self.preencher_dados(dados_receita)
            if dados_receita[2]:
                self.venda_id = dados_receita[2]
        elif venda_id:
            self._carregar_por_venda(venda_id)
        self._rastreador = ui_utils.RastreadorAlteracoes(self._snapshot_receita)
        self._rastreador.marcar_limpo()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._fechar_janela)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground=self.bg_card, background=self.bg_card, arrowcolor=self.cor_destaque, bordercolor=self.cor_borda)
        style.configure("Compacta.Treeview", background="#F8FAFC", rowheight=24, font=("Segoe UI", 9))
        style.configure("Compacta.Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def formatar_data_para_bd(self, data_str):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try: return datetime.strptime(data_str, fmt).strftime("%Y-%m-%d")
            except ValueError: continue
        return None

    def formatar_data_exibicao(self, data_str):
        return ui_utils.formatar_data_exibicao(data_str)

    def aplicar_estilo_foco(self, ent):
        def on_enter(e):
            if ent.focus_get() != ent: ent.config(highlightbackground=self.cor_hover_field)
        def on_leave(e):
            if ent.focus_get() != ent: ent.config(highlightbackground=self.cor_borda)
        def on_focus_in(e): ent.config(highlightbackground=self.cor_destaque, highlightthickness=2)
        def on_focus_out(e): ent.config(highlightbackground=self.cor_borda, highlightthickness=1)
        ent.bind("<Enter>", on_enter); ent.bind("<Leave>", on_leave)
        ent.bind("<FocusIn>", on_focus_in); ent.bind("<FocusOut>", on_focus_out)

    def _manter_em_primeiro_plano(self):
        try:
            self.attributes("-topmost", True)
        except Exception as e:
            messagebox.showwarning("Aviso", f"Não foi possível manter esta janela em primeiro plano: {e}", parent=self)

    def criar_widgets(self):
        main_frame = tk.Frame(self, bg=self.bg_fundo, padx=15, pady=10)
        main_frame.pack(fill="both", expand=True)

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
      
        # Cabeçalho do Módulo
        tk.Label(main_frame, text=" 💰 Gerenciamento de Receitas (Entradas)", bg=self.bg_fundo, fg=self.cor_texto, font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
       
        # --- FORMULÁRIO DE LANÇAMENTO ---
        form_frame = tk.LabelFrame(main_frame, text=" Dados de Faturamento / Receita ", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 9, "bold"), padx=10, pady=10, relief="solid", borderwidth=1)
        form_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
        form_frame.columnconfigure(0, weight=1); form_frame.columnconfigure(1, weight=1); form_frame.columnconfigure(2, weight=1)

        def criar_campo_form(label, r, c, c_span=1):
            tk.Label(form_frame, text=label, bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=r, column=c, sticky="w", padx=5, pady=(4, 0))
            ent = tk.Entry(form_frame, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto, relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
            ent.grid(row=r+1, column=c, columnspan=c_span, sticky="ew", ipady=3, padx=5, pady=(0, 4))
            self.aplicar_estilo_foco(ent)
            return ent

        self.ent_cliente_nome = criar_campo_form("CLIENTE NOMINAL*", 0, 0, c_span=2)
        self.ent_desc = criar_campo_form("IDENTIFICAÇÃO / ORIGEM*", 0, 2, c_span=1)

        # Valores e Fluxo Financeiro de Auditoria
        self.ent_valor_base = criar_campo_form("VALOR DA VENDA (R$)*", 2, 0)
        self.ent_valor_base.bind("<KeyRelease>", lambda e: self.atualizar_calculos())
        
        self.ent_encargos = criar_campo_form("JUROS/MULTA (R$)", 2, 1)
        self.ent_encargos.insert(0, "0.00")
        self.ent_encargos.bind("<KeyRelease>", lambda e: self.atualizar_calculos())
        ui_utils.anexar_botao_calculadora(form_frame, self.ent_encargos, row=3, column=1, sticky="e")

        self.ent_descontos = criar_campo_form("DESCONTOS (R$)", 2, 2)
        self.ent_descontos.insert(0, "0.00")
        self.ent_descontos.bind("<KeyRelease>", lambda e: self.atualizar_calculos())
        ui_utils.anexar_botao_calculadora(form_frame, self.ent_descontos, row=3, column=2, sticky="e")

        self.ent_encargos_op_pct = criar_campo_form("% ENCARGOS OPERADORA", 4, 0)
        self.ent_encargos_op_pct.insert(0, "0.00")
        self.ent_encargos_op_pct.bind("<KeyRelease>", lambda e: self.atualizar_calculos())

        self.ent_valor_liquido = criar_campo_form("VALOR LÍQUIDO (FINANCEIRO)*", 4, 1)
        self.ent_valor_liquido.bind("<KeyRelease>", lambda e: self._liquido_manual())

        self.ent_valor_pago = criar_campo_form("VALOR PAGO (R$)*", 4, 2)
        self.ent_valor_pago.insert(0, "0.00")
        self.ent_valor_pago.bind("<KeyRelease>", lambda e: self.atualizar_calculos())

        # Datas Cadastrais e Operacionais
        self.ent_lancamento = criar_campo_form("DATA EMISSÃO", 6, 0)
        self.ent_lancamento.insert(0, datetime.now().strftime("%d/%m/%Y"))
        ui_utils.anexar_botao_calendario(form_frame, self.ent_lancamento, row=7, column=0, sticky="e")

        self.ent_vencimento = criar_campo_form("DATA VENCIMENTO*", 6, 1)
        self.ent_vencimento.insert(0, datetime.now().strftime("%d/%m/%Y"))
        ui_utils.anexar_botao_calendario(form_frame, self.ent_vencimento, row=7, column=1, sticky="e")

        self.ent_pagamento = criar_campo_form("DATA PAGAMENTO", 6, 2)
        ui_utils.anexar_botao_calendario(form_frame, self.ent_pagamento, row=7, column=2, sticky="e")

        tk.Label(form_frame, text="STATUS RECEBIMENTO*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=8, column=0, sticky="w", padx=5)
        self.cb_status = ttk.Combobox(form_frame, values=self.list_status, state="readonly", font=("Segoe UI", 9))
        self.cb_status.set("Pendente")
        self.cb_status.grid(row=9, column=0, sticky="ew", ipady=3, padx=5)

        tk.Label(form_frame, text="CATEGORIA FLUXO*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=8, column=1, sticky="w", padx=5)
        self.cb_cat = ttk.Combobox(form_frame, values=self.list_categorias, state="readonly", font=("Segoe UI", 9))
        self.cb_cat.set("Venda")
        self.cb_cat.grid(row=9, column=1, sticky="ew", ipady=3, padx=5)

        tk.Label(form_frame, text="FORMA PAGAMENTO*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=8, column=2, sticky="w", padx=5)
        self.cb_forma = ttk.Combobox(form_frame, values=self.list_formas, state="readonly", font=("Segoe UI", 9))
        self.cb_forma.set("PIX")
        self.cb_forma.grid(row=9, column=2, sticky="ew", ipady=3, padx=5)
        self.cb_forma.bind("<<ComboboxSelected>>", self._ao_mudar_forma_pagamento)

        tk.Label(form_frame, text="RECORRÊNCIA*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=10, column=0, sticky="w", padx=5)
        self.cb_recorrencia = ttk.Combobox(form_frame, values=self.list_recorrencia, state="readonly", font=("Segoe UI", 9))
        self.cb_recorrencia.set("Não Recorrente")
        self.cb_recorrencia.grid(row=11, column=0, sticky="ew", ipady=3, padx=5)
        self.cb_recorrencia.bind("<<ComboboxSelected>>", self.toggle_recorrencia)

        self.lbl_parc = tk.Label(form_frame, text="Nº PARCELAS*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold"))
        self.ent_parc = tk.Entry(form_frame, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto, relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
        self.ent_parc.insert(0, "1")
        self.ent_parc.bind("<KeyRelease>", lambda e: self.atualizar_calculos())
        ui_utils.configurar_entry_inteiro(self.ent_parc, self)

        self.lbl_painel_calculo = tk.Label(form_frame, text="Valor Líquido Esperado: R$ 0.00 | Saldo em Aberto: R$ 0.00", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 9, "bold"), anchor="w")
        self.lbl_painel_calculo.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(8, 0), padx=5)

        # --- SEÇÃO TREEVIEW: HISTÓRICO DE PARCELAS VINCULADAS ---
        tk.Label(main_frame, text="📑 Carnê / Fluxo Relacionado das Parcelas do Cliente", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 9, "bold")).grid(row=3, column=0, columnspan=3, sticky="w", pady=(15, 2), padx=5)
        self.tree_parcelas = ttk.Treeview(main_frame, columns=("id", "parc", "venc", "pagto", "liquido", "pago", "status"), show="headings", height=4, style="Compacta.Treeview")
        
        headers = {"id": "ID", "parc": "PARCELA", "venc": "VENCIMENTO", "pagto": "RECEBIDO EM", "liquido": "VLR LÍQUIDO", "pago": "VLR AMORTIZADO", "status": "STATUS"}
        for col, text in headers.items():
            self.tree_parcelas.heading(col, text=text)
            self.tree_parcelas.column(col, width=85, anchor="center")
        self.tree_parcelas.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5)
        self.tree_parcelas.bind("<<TreeviewSelect>>", self.carregar_parcela_selecionada)

        _pal = ui_utils.get_paleta()
        frame_rodape = tk.Frame(main_frame, bg=self.bg_fundo)
        frame_rodape.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        frame_rodape.columnconfigure((0, 1, 2, 3), weight=1, uniform="rodape_rec")
        self.btn_salvar = ui_utils.criar_botao_rodape(
            frame_rodape,
            ui_utils.texto_botao_salvar("Venda", bool(self.venda_id)),
            self.validar_e_salvar,
            "acao1",
            _pal,
        )
        self.btn_salvar.grid(row=0, column=0, sticky="ew", padx=(0, 4), ipady=6)
        self.btn_editar_itens = ui_utils.criar_botao_rodape(
            frame_rodape, "Editar Venda", self._editar_itens_venda, "acao2", _pal,
        )
        self.btn_editar_itens.grid(row=0, column=1, sticky="ew", padx=4, ipady=6)
        self.btn_editar_itens.config(state="normal" if self.venda_id else "disabled")
        self.btn_deletar = ui_utils.criar_botao_rodape(
            frame_rodape, "Estornar Venda", self.excluir_crud, "acao2", _pal,
        )
        self.btn_deletar.grid(row=0, column=2, sticky="ew", padx=4, ipady=6)
        self.btn_deletar.config(state="normal" if self.receita_id else "disabled")
        self.btn_cancelar = ui_utils.criar_botao_rodape(
            frame_rodape, "Fechar Janela", self._fechar_janela, "sair", _pal,
        )
        self.btn_cancelar.grid(row=0, column=3, sticky="ew", padx=(4, 0), ipady=6)
        frame_rodape.columnconfigure(3, weight=1)

    # --- LÓGICA ---

    def _snapshot_receita(self):
        return (
            self.ent_cliente_nome.get(),
            self.ent_desc.get(),
            self.ent_valor_base.get(),
            self.ent_valor_liquido.get(),
            self.cb_forma.get(),
            self.ent_parc.get(),
        )

    def _fechar_janela(self):
        if ui_utils.confirmar_fechar_formulario(self, self._rastreador):
            self.destroy()

    def _liquido_manual(self):
        self._liquido_editado_manual = True

    def _ao_mudar_forma_pagamento(self, event=None):
        forma = self.cb_forma.get()
        if forma == "Cartão de Débito":
            self.ent_parc.delete(0, tk.END)
            self.ent_parc.insert(0, "1")
            self.cb_recorrencia.set("Não Recorrente")
            self.toggle_recorrencia()
        elif forma == "Cartão de Crédito" or forma == "Crediário":
            self.cb_recorrencia.set("Parcelado")
            self.toggle_recorrencia()
            try:
                if int(self.ent_parc.get() or "1") < 2:
                    self.ent_parc.delete(0, tk.END)
                    self.ent_parc.insert(0, "2")
            except ValueError:
                self.ent_parc.delete(0, tk.END)
                self.ent_parc.insert(0, "2")
        self.atualizar_calculos()

    def _editar_itens_venda(self):
        if not self.venda_id:
            return
        v = database.obter_venda_por_id(self.venda_id)
        if not v:
            return
        from cadastro_vendas import JanelaCadastroVendas
        dados_venda = {"id": self.venda_id, "desconto": v[6], "forma": v[8], "parcelas": v[9]}
        JanelaCadastroVendas(self.master, dados_venda=dados_venda)

    def toggle_recorrencia(self, event=None):
        if self.cb_recorrencia.get() == "Parcelado":
            self.lbl_parc.grid(row=10, column=1, sticky="w", padx=5)
            self.ent_parc.grid(row=11, column=1, sticky="ew", ipady=3, padx=5)
        else:
            self.lbl_parc.grid_remove()
            self.ent_parc.grid_remove()
            self.ent_parc.delete(0, tk.END)
            self.ent_parc.insert(0, "1")
        self.atualizar_calculos()

    def _carregar_por_venda(self, venda_id):
        v = database.obter_venda_por_id(venda_id)
        if not v:
            return
        self.cliente_selecionado_id = v[1]
        self.ent_cliente_nome.delete(0, tk.END)
        self.ent_cliente_nome.insert(0, v[2])
        parcelas = database.listar_parcelas_venda(venda_id)
        if parcelas:
            fid = parcelas[0][0]
            d = database.obter_financeiro_por_id(fid)
            if d:
                self.preencher_dados(d)
        self.carregar_parcelas_por_venda(venda_id)

    def carregar_parcelas_por_venda(self, venda_id):
        self.tree_parcelas.delete(*self.tree_parcelas.get_children())
        for p in database.listar_parcelas_venda(venda_id):
            pid, pa, tot, venc, pag, val, vpago, st = p
            self.tree_parcelas.insert("", "end", values=(
                pid, f"{pa}/{tot}", self.formatar_data_exibicao(venc), self.formatar_data_exibicao(pag),
                f"R$ {val:.2f}", f"R$ {(vpago or 0):.2f}", st
            ))

    def validar_e_salvar(self):
        # CORREÇÃO DA SENHA:
        # Se a janela foi aberta a partir do PDV (onde self.master é a JanelaCadastroVendas)
        # NÃO solicita senha nenhuma para que a finalização ou reedição de itens flua direto.
        # Solicita senha APENAS se for uma modificação manual de registro já salvo aberta a partir do menu principal.
        from cadastro_vendas import JanelaCadastroVendas
        if self.receita_id and not isinstance(self.master, JanelaCadastroVendas):
            if not ui_utils.solicitar_senha_fluxo(self):
                return
                
        self.salvar_crud()

    def atualizar_calculos(self):
        try:
            v_base = float(self.ent_valor_base.get().replace(",", ".")) if self.ent_valor_base.get().strip() else 0.0
            enc = float(self.ent_encargos.get().replace(",", ".")) if self.ent_encargos.get().strip() else 0.0
            desc = float(self.ent_descontos.get().replace(",", ".")) if self.ent_descontos.get().strip() else 0.0
            pct_op = float(self.ent_encargos_op_pct.get().replace(",", ".")) if self.ent_encargos_op_pct.get().strip() else 0.0
            pado = float(self.ent_valor_pago.get().replace(",", ".")) if self.ent_valor_pago.get().strip() else 0.0
            parc = int(self.ent_parc.get()) if self.ent_parc.get().strip() else 1
        except ValueError:
            self.lbl_painel_calculo.config(text="Erro de digitação nos campos de faturamento.", fg="red")
            return

        if self.cb_forma.get() in config.FORMAS_CARTAO and pct_op > 0:
            enc_op = round(v_base * (pct_op / 100), 2)
            enc = round(enc + enc_op, 2)

        v_liquido = round(v_base + enc - desc, 2)
        if not getattr(self, "_liquido_editado_manual", False):
            self.ent_valor_liquido.delete(0, tk.END)
            self.ent_valor_liquido.insert(0, f"{v_liquido:.2f}")

        try:
            v_liq_campo = float(self.ent_valor_liquido.get().replace(",", "."))
        except ValueError:
            v_liq_campo = v_liquido

        devedor = round(v_liq_campo - pado, 2)
        if self.cb_recorrencia.get() == "Parcelado" and parc > 1:
            txt = (
                f"Valor líquido: R$ {v_liq_campo:.2f} | {parc}x de R$ {round(v_liq_campo / parc, 2):.2f} "
                f"| Saldo: R$ {devedor:.2f}"
            )
        else:
            txt = f"Valor líquido contabilizado: R$ {v_liq_campo:.2f} | Saldo pendente: R$ {devedor:.2f}"

        self.lbl_painel_calculo.config(text=txt, fg=self.cor_destaque)

    def carregar_parcelas_historico(self, nome, desc):
        self.tree_parcelas.delete(*self.tree_parcelas.get_children())
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, parcelas_atual || '/' || total_parcelas, data_vencimento, data_pagamento, valor, valor_pago, status 
                FROM financeiro WHERE entidade_nome=? AND descricao=? AND tipo='Receita' ORDER BY id ASC
            """, (nome, desc))
            for p in cursor.fetchall():
                v_enc = self.formatar_data_exibicao(p[2])
                v_pag = self.formatar_data_exibicao(p[3])
                self.tree_parcelas.insert("", "end", values=(p[0], p[1], v_enc, v_pag, f"R$ {p[4]:.2f}", f"R$ {p[5]:.2f}", p[6]))

    def carregar_parcela_selecionada(self, event=None):
        sel = self.tree_parcelas.selection()
        if not sel: return
        id_f = self.tree_parcelas.item(sel[0], "values")[0]
        
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM financeiro WHERE id=?", (id_f,))
            d = cursor.fetchone()
        if d: self.preencher_dados(d)

    def preencher_dados(self, d):
        self.receita_id = d[0]
        self.cliente_selecionado_id = d[3]
        self.venda_id = d[2]
        self.ent_cliente_nome.delete(0, tk.END); self.ent_cliente_nome.insert(0, d[5] if d[5] else "")
        self.ent_desc.delete(0, tk.END); self.ent_desc.insert(0, d[6] if d[6] else "")
        
        self.ent_valor_base.delete(0, tk.END); self.ent_valor_base.insert(0, f"{d[8]:.2f}" if d[8] is not None else f"{d[7]:.2f}")
        self.ent_valor_pago.delete(0, tk.END); self.ent_valor_pago.insert(0, f"{d[9]:.2f}")
        self.ent_encargos.delete(0, tk.END); self.ent_encargos.insert(0, f"{d[10]:.2f}")
        self.ent_descontos.delete(0, tk.END); self.ent_descontos.insert(0, f"{d[11]:.2f}")
        
        self.ent_lancamento.delete(0, tk.END); self.ent_lancamento.insert(0, self.formatar_data_exibicao(d[20]))
        self.ent_vencimento.delete(0, tk.END); self.ent_vencimento.insert(0, self.formatar_data_exibicao(d[16]))
        self.ent_pagamento.delete(0, tk.END); self.ent_pagamento.insert(0, self.formatar_data_exibicao(d[17]))
        
        self.cb_forma.set(d[12] if d[12] else "PIX")
        self.cb_recorrencia.set(d[13] if d[13] else "Não Recorrente")
        self.cb_cat.set(d[18] if d[18] else "Venda")
        self.cb_status.set(d[19])
        
        self.ent_parc.delete(0, tk.END)
        self.ent_parc.insert(0, str(d[14] if len(d) > 14 and d[14] else 1))
        if hasattr(self, "ent_encargos_op_pct"):
            self.ent_encargos_op_pct.delete(0, tk.END)
            self.ent_encargos_op_pct.insert(0, f"{float(d[22] or 0):.2f}" if len(d) > 22 else "0.00")
        self.ent_valor_liquido.delete(0, tk.END)
        self.ent_valor_liquido.insert(0, f"{float(d[7] or 0):.2f}")
        self._liquido_editado_manual = False
        self.toggle_recorrencia()
        self._rastreador.marcar_limpo()
        
        self.btn_deletar.config(state="normal")
        self.btn_salvar.config(text=ui_utils.texto_botao_salvar("Receita", True))
        ui_utils.atualizar_cor_botao_rodape(self.btn_salvar, "acao2", ui_utils.get_paleta())
        if self.venda_id:
            self.carregar_parcelas_por_venda(self.venda_id)
        else:
            self.carregar_parcelas_historico(d[5], d[6])

    def _redistribuir_parcelas_venda(self, cursor, venda_id, valor_liquido, parcelas):
        """Recria parcelas pendentes proporcionalmente ao valor líquido (cartão parcelado / fiado)."""
        cursor.execute(
            "DELETE FROM financeiro WHERE venda_id=? AND tipo='Receita' AND status != 'Pago'",
            (venda_id,),
        )
        cursor.execute(
            "SELECT c.nome, v.cliente_id FROM vendas v JOIN clientes c ON v.cliente_id = c.id WHERE v.id = ?",
            (venda_id,),
        )
        row = cursor.fetchone()
        if not row:
            return
        nome_cli, cliente_id = row
        valor_parcela = round(valor_liquido / parcelas, 2)
        for i in range(parcelas):
            if i == parcelas - 1:
                valor_parcela = round(valor_liquido - (valor_parcela * (parcelas - 1)), 2)
            vencimento = database.adicionar_meses(datetime.now(), i).strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO financeiro (
                    tipo, venda_id, cliente_id, id_agrupador, entidade_nome, descricao, valor, valor_base,
                    parcelas_atual, total_parcelas, data_vencimento, categoria, recorrencia, status
                ) VALUES ('Receita', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Venda', 'Parcelado', 'Pendente')
            """, (
                venda_id, cliente_id, venda_id, nome_cli,
                f"Venda #{venda_id} - Parcela {i + 1}/{parcelas}",
                valor_parcela, valor_parcela, i + 1, parcelas, vencimento,
            ))

    def salvar_crud(self):
        nome = self.ent_cliente_nome.get().strip()
        desc = self.ent_desc.get().strip()
        v_base = self.ent_valor_base.get().replace(",", ".")
        v_pago = self.ent_valor_pago.get().replace(",", ".")
        v_enc = self.ent_encargos.get().replace(",", ".")
        v_desc = self.ent_descontos.get().replace(",", ".")
        
        dat_lan = self.formatar_data_para_bd(self.ent_lancamento.get())
        dat_ven = self.formatar_data_para_bd(self.ent_vencimento.get())
        dat_pag = self.formatar_data_para_bd(self.ent_pagamento.get()) if self.ent_pagamento.get().strip() else None

        if not nome or not desc or not v_base or not dat_ven:
            messagebox.showwarning("Validação", "Os campos Cliente, Identificação, Valor Original e Vencimento são vitais.", parent=self)
            return

        try:
            val_base_f = float(v_base)
            val_pago_f = float(v_pago)
            enc_f = float(v_enc)
            desc_f = float(v_desc)
            parcelas_totais = int(self.ent_parc.get())
        except ValueError:
            messagebox.showerror("Erro", "Formato monetário corrompido.", parent=self)
            return

        try:
            pct_op = float(self.ent_encargos_op_pct.get().replace(",", "."))
        except ValueError:
            pct_op = 0.0
        if self.cb_forma.get() in config.FORMAS_CARTAO and pct_op > 0:
            enc_f = round(enc_f + val_base_f * (pct_op / 100), 2)

        try:
            valor_liquido_calculado = float(self.ent_valor_liquido.get().replace(",", "."))
        except ValueError:
            valor_liquido_calculado = round(val_base_f + enc_f - desc_f, 2)

        parcelas_totais = int(self.ent_parc.get() or 1)
        if self.cb_forma.get() == "Cartão de Débito":
            parcelas_totais = 1
        elif self.cb_forma.get() == "Cartão de Crédito" or self.cb_forma.get() == "Crediário":
            parcelas_totais = max(1, parcelas_totais)

        st = self.cb_status.get()
        if val_pago_f >= valor_liquido_calculado - 0.01:
            st = 'Pago'
            if not dat_pag:
                dat_pag = datetime.now().strftime("%Y-%m-%d")
        elif val_pago_f > 0:
            st = 'Pendente'

        with database.conectar() as conn:
            cursor = conn.cursor()
            if self.receita_id:
                cursor.execute("""
                    UPDATE financeiro SET cliente_id=?, entidade_nome=?, descricao=?, valor=?, valor_base=?, valor_pago=?,
                                          encargos=?, descontos=?, data_lancamento=?, data_vencimento=?, data_pagamento=?,
                                          forma_pagamento=?, categoria=?, status=?, recorrencia=?,
                                          total_parcelas=?, valor_encargos=?, tipo_encargos=?
                    WHERE id=? AND tipo='Receita'
                """, (
                    self.cliente_selecionado_id, nome, desc, valor_liquido_calculado, val_base_f, val_pago_f,
                    enc_f, desc_f, dat_lan, dat_ven, dat_pag, self.cb_forma.get(), self.cb_cat.get(), st,
                    self.cb_recorrencia.get(), parcelas_totais, pct_op, "Porcentagem", self.receita_id,
                ))
                if self.venda_id and self.cb_recorrencia.get() == "Parcelado" and parcelas_totais > 1:
                    self._redistribuir_parcelas_venda(cursor, self.venda_id, valor_liquido_calculado, parcelas_totais)
                elif self.venda_id:
                    cursor.execute(
                        "UPDATE financeiro SET valor=?, valor_base=?, total_parcelas=1 WHERE venda_id=? AND tipo='Receita' AND status!='Pago'",
                        (valor_liquido_calculado, val_base_f, self.venda_id),
                    )
                if self.venda_id and (val_pago_f > 0 or st == "Pago"):
                    ok_est, msg_est = database.baixar_estoque_venda(self.venda_id, cursor=cursor)
                    if not ok_est:
                        conn.rollback()
                        messagebox.showerror("Estoque", msg_est, parent=self)
                        return
                if self.venda_id:
                    cursor.execute(
                        "UPDATE vendas SET forma_pagamento=?, qtd_parcelas=?, valor_total=? WHERE id=?",
                        (self.cb_forma.get(), parcelas_totais, valor_liquido_calculado, self.venda_id),
                    )
                conn.commit()
                # Removemos alertas poluentes no ato da venda
                from cadastro_vendas import JanelaCadastroVendas
                if not isinstance(self.master, JanelaCadastroVendas):
                    messagebox.showinfo("Sucesso", "Recebimento registrado com sucesso.", parent=self)
            else:
                messagebox.showwarning(
                    "Receitas",
                    "Novas receitas são geradas apenas pelo PDV (Gerar Vendas).\n"
                    "Use esta tela para registrar pagamentos de títulos existentes.",
                    parent=self,
                )
                return

        if hasattr(self.master, "exibir_financeiro"):
            self.master.exibir_financeiro()
            
        cb = self.on_sucesso
        self.destroy() # Libera o fluxo imediatamente para o wait_window do PDV limpar os campos
        if cb:
            cb()

    def excluir_crud(self):
        if self.receita_id and ui_utils.confirmar(self, "Estorno Definitivo", "Deseja estornar e apagar este lançamento?"):
            with database.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM financeiro WHERE id=? AND tipo='Receita'", (self.receita_id,))
                conn.commit()
            messagebox.showinfo("Sucesso", "Título excluído do fluxo.", parent=self)
            if hasattr(self.master, "exibir_financeiro"): self.master.exibir_financeiro()
            self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    JanelaGerenciarReceitas(root)
    root.mainloop()