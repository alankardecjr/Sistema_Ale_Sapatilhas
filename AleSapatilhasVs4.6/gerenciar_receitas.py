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
import database
import ui_utils


class JanelaGerenciarReceitas(tk.Toplevel):
    """Formulário modal para recebimentos e manutenção de parcelas."""
    def __init__(self, master, dados_receita=None, venda_id=None):
        super().__init__(master)
        self.venda_id = venda_id
        
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
        
        ui_utils.calcular_dimensoes_janela(self, largura_desejada=700, altura_desejada=850)
        
        self.receita_id = dados_receita[0] if dados_receita else None
        self.cliente_selecionado_id = None
        
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
        else:
            self.pesquisar_clientes()
            
        self.grab_set()

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
        if not data_str: return ""
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try: return datetime.strptime(data_str, fmt).strftime("%d/%m/%Y")
            except ValueError: continue
        return data_str

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
        wrapper = tk.Frame(self, bg=self.bg_fundo)
        wrapper.pack(fill="both", expand=True)

        canvas = tk.Canvas(wrapper, bg=self.bg_fundo, highlightthickness=0)
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        main_frame = tk.Frame(canvas, bg=self.bg_fundo, padx=15, pady=10)
        self.canvas_frame = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(self.canvas_frame, width=e.width))

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
      
        # --- Helpers de estilo (Hover e Input) ---
        def aplicar_estilo_foco(ent):
            def on_enter(e):
                if self.focus_get() != ent: ent.config(highlightbackground=self.cor_hover_field)
            def on_leave(e):
                if self.focus_get() != ent: ent.config(highlightbackground=self.cor_borda)
            def on_focus_in(e): ent.config(highlightbackground=self.cor_destaque, highlightthickness=2)
            def on_focus_out(e): ent.config(highlightbackground=self.cor_borda, highlightthickness=1)
            ent.bind("<Enter>", on_enter)
            ent.bind("<Leave>", on_leave)
            ent.bind("<FocusIn>", on_focus_in)
            ent.bind("<FocusOut>", on_focus_out)

        # Cabeçalho do Módulo
        tk.Label(main_frame, text=" 💰 Gerenciamento de Receitas (Entradas)", bg=self.bg_fundo, fg=self.cor_texto, font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # --- SEÇÃO BUSCA DE CLIENTES ---
        search_frame = tk.LabelFrame(main_frame, text=" Pesquisa de Clientes Activos ", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 9, "bold"), padx=10, pady=5, relief="solid", borderwidth=1)
        search_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        search_frame.columnconfigure(0, weight=1)

        self.placeholder_busca = "🔍 Digite o nome ou telefone do cliente para buscar..."
        self.ent_busca_cli = tk.Entry(search_frame, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto, relief="flat", highlightthickness=1, highlightbackground=self.cor_borda)
        self.ent_busca_cli.grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 5))
        self.ent_busca_cli.insert(0, self.placeholder_busca)
        self.ent_busca_cli.config(fg="gray")
        
        self.ent_busca_cli.bind("<FocusIn>", lambda e: [self.ent_busca_cli.delete(0, tk.END), self.ent_busca_cli.config(fg=self.cor_texto)] if self.ent_busca_cli.get() == self.placeholder_busca else None)
        self.ent_busca_cli.bind("<FocusOut>", lambda e: [self.ent_busca_cli.insert(0, self.placeholder_busca), self.ent_busca_cli.config(fg="gray")] if not self.ent_busca_cli.get().strip() else None)
        self.ent_busca_cli.bind("<KeyRelease>", self.pesquisar_clientes)

        # Treeview Mínima Dinâmica de Clientes (Exibe 3 Linhas)
        self.tree_cli = ttk.Treeview(search_frame, columns=("id", "nome", "telefone", "status"), show="headings", height=3, style="Compacta.Treeview")
        self.tree_cli.heading("id", text="ID"); self.tree_cli.heading("nome", text="CLIENTE"); self.tree_cli.heading("telefone", text="TELEFONE"); self.tree_cli.heading("status", text="STATUS")
        self.tree_cli.column("id", width=40, anchor="center"); self.tree_cli.column("nome", width=250, anchor="w")
        self.tree_cli.column("telefone", width=120, anchor="center"); self.tree_cli.column("status", width=90, anchor="center")
        self.tree_cli.grid(row=1, column=0, sticky="ew", pady=(5, 5))
        self.tree_cli.bind("<<TreeviewSelect>>", self.selecionar_cliente)

        # Painel Minimalista de Metadados do Cliente
        self.lbl_detalhes_contato = tk.Label(search_frame, text="Nenhum cliente selecionado.", bg=self.bg_card, fg=self.cor_texto, font=("Segoe UI", 9, "italic"), relief="flat", anchor="w", justify="left", padx=10, pady=5)
        self.lbl_detalhes_contato.grid(row=2, column=0, sticky="ew", pady=2)

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
        self.ent_valor_base = criar_campo_form("VALOR ORIGINAL VENDA (R$)*", 2, 0)
        self.ent_valor_base.bind("<KeyRelease>", lambda e: self.atualizar_calculos())
        
        self.ent_encargos = criar_campo_form("JUROS / MULTA (R$)", 2, 1)
        self.ent_encargos.insert(0, "0.00")
        self.ent_encargos.bind("<KeyRelease>", lambda e: self.atualizar_calculos())
        
        self.ent_descontos = criar_campo_form("DESCONTO CONCEDIDO (R$)", 2, 2)
        self.ent_descontos.insert(0, "0.00")
        self.ent_descontos.bind("<KeyRelease>", lambda e: self.atualizar_calculos())

        self.ent_valor_pago = criar_campo_form("AMORTIZAÇÃO / VALOR AMORTIZADO", 4, 0)
        self.ent_valor_pago.insert(0, "0.00")
        self.ent_valor_pago.bind("<KeyRelease>", lambda e: self.atualizar_calculos())

        # Datas Cadastrais e Operacionais
        self.ent_lancamento = criar_campo_form("DATA EMISSÃO", 4, 1)
        self.ent_lancamento.insert(0, datetime.now().strftime("%d/%m/%Y"))
        
        self.ent_vencimento = criar_campo_form("DATA VENCIMENTO PARCELA*", 4, 2)
        self.ent_vencimento.insert(0, datetime.now().strftime("%d/%m/%Y"))
        
        self.ent_pagamento = criar_campo_form("DATA LIQUIDAÇÃO", 6, 0)

        # Comboboxes de Estado da Receita
        tk.Label(form_frame, text="STATUS RECEBIMENTO*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=6, column=1, sticky="w", padx=5)
        self.cb_status = ttk.Combobox(form_frame, values=self.list_status, state="readonly", font=("Segoe UI", 9))
        self.cb_status.set("Pendente")
        self.cb_status.grid(row=7, column=1, sticky="ew", ipady=3, padx=5)

        tk.Label(form_frame, text="CATEGORIA FLUXO*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=6, column=2, sticky="w", padx=5)
        self.cb_cat = ttk.Combobox(form_frame, values=self.list_categorias, state="readonly", font=("Segoe UI", 9))
        self.cb_cat.set("Venda")
        self.cb_cat.grid(row=7, column=2, sticky="ew", ipady=3, padx=5)

        tk.Label(form_frame, text="FORMA LIQUIDAÇÃO*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=8, column=0, sticky="w", padx=5)
        self.cb_forma = ttk.Combobox(form_frame, values=self.list_formas, state="readonly", font=("Segoe UI", 9))
        self.cb_forma.set("PIX")
        self.cb_forma.grid(row=9, column=0, sticky="ew", ipady=3, padx=5)

        tk.Label(form_frame, text="DIVISÃO DE PARCELAS*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=8, column=1, sticky="w", padx=5)
        self.cb_recorrencia = ttk.Combobox(form_frame, values=self.list_recorrencia, state="readonly", font=("Segoe UI", 9))
        self.cb_recorrencia.set("Não Recorrente")
        self.cb_recorrencia.grid(row=9, column=1, sticky="ew", ipady=3, padx=5)
        self.cb_recorrencia.bind("<<ComboboxSelected>>", self.toggle_recorrencia)

        self.lbl_parc = tk.Label(form_frame, text="Nº PARCELAS*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold"))
        self.ent_parc = tk.Entry(form_frame, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto, relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
        self.ent_parc.insert(0, "1")
        self.ent_parc.bind("<KeyRelease>", lambda e: self.atualizar_calculos())

        # Painéis de Cálculos Dinâmicos
        self.lbl_painel_calculo = tk.Label(form_frame, text="Valor Líquido Esperado: R$ 0.00 | Saldo em Aberto: R$ 0.00", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 9, "bold"), anchor="w")
        self.lbl_painel_calculo.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(8, 0), padx=5)

        # --- SEÇÃO TREEVIEW: HISTÓRICO DE PARCELAS VINCULADAS ---
        tk.Label(main_frame, text="📑 Carnê / Fluxo Relacionado das Parcelas do Cliente", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 9, "bold")).grid(row=3, column=0, columnspan=3, sticky="w", pady=(15, 2), padx=5)
        self.tree_parcelas = ttk.Treeview(main_frame, columns=("id", "parc", "venc", "pagto", "liquido", "pago", "status"), show="headings", height=4, style="Compacta.Treeview")
        
        headers = {"id": "ID", "parc": "PARCELA", "venc": "VENCIMENTO", "pagto": "RECEBIDO EM", "liquido": "VLR LÍQUIDO", "pago": "VLR AMORTIZADO", "status": "STATUS"}
        for col, text in headers.items():
            self.tree_parcelas.heading(col, text=text)
            self.tree_parcelas.column(col, width=85, anchor="center")
        self.tree_parcelas.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5)
        self.tree_parcelas.bind("<<TreeviewSelect>>", self.carregar_parcela_selecionada)

        # --- BOTÕES DE AÇÃO OPERACIONAL (Dual Mode e Hover) ---
        texto_btn = "ATUALIZAR RECEITA" if self.receita_id else "SALVAR RECEITA"
        self.btn_salvar = tk.Button(main_frame, text=texto_btn, bg=self.cor_btn_acao, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", command=self.validar_e_salvar)
        self.btn_salvar.grid(row=7, column=0, columnspan=3, pady=(10, 0), sticky="ew", ipady=4)
        
        self.btn_deletar = tk.Button(main_frame, text="ESTORNAR / DELETAR TITULO", bg=self.cor_destaque, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", command=self.excluir_crud)
        self.btn_deletar.grid(row=6, column=0, columnspan=3, pady=2, sticky="ew", ipady=4)
        self.btn_deletar.grid_remove()

        self.btn_cancelar = tk.Button(main_frame, text="FECHAR JANELA", bg=self.cor_btn_sair, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", command=self.destroy)
        self.btn_cancelar.grid(row=20, column=0, columnspan=3, pady=(5, 0), sticky="ew", ipady=4)

       # Bind Hovers
        self.btn_salvar.bind("<Enter>", lambda e: e.widget.config(bg=self.cor_hover_btn))
        self.btn_salvar.bind("<Leave>", lambda e: e.widget.config(bg=self.cor_btn_acao))
        self.btn_cancelar.bind("<Enter>", lambda e: e.widget.config(bg=self.cor_hover_btn))
        self.btn_cancelar.bind("<Leave>", lambda e: e.widget.config(bg=self.cor_btn_sair))
    
    # --- LÓGICA ---
    def toggle_recorrencia(self, event=None):
        if self.cb_recorrencia.get() == "Parcelado":
            self.lbl_parc.grid(row=8, column=2, sticky="w", padx=5)
            self.ent_parc.grid(row=9, column=2, sticky="ew", ipady=3, padx=5)
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
        self.salvar_crud()

    def pesquisar_clientes(self, event=None):
        termo = self.ent_busca_cli.get().lower()
        if termo == self.placeholder_busca.lower(): termo = ""
        self.tree_cli.delete(*self.tree_cli.get_children())
        
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome, telefone, status_cliente FROM clientes WHERE tipo='Cliente' AND (nome LIKE ? OR telefone LIKE ?)", (f"%{termo}%", f"%{termo}%"))
            for c in cursor.fetchall():
                self.tree_cli.insert("", "end", values=c)

    def selecionar_cliente(self, event=None):
        sel = self.tree_cli.selection()
        if not sel: return
        dados = self.tree_cli.item(sel[0], "values")
        self.cliente_selecionado_id = dados[0]
        
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cpf, tamanho_calcado, limite_credito, status_cliente FROM clientes WHERE id=?", (self.cliente_selecionado_id,))
            extra = cursor.fetchone()
        
        self.ent_cliente_nome.delete(0, tk.END)
        self.ent_cliente_nome.insert(0, dados[1])
        
        txt = f"Cliente: {dados[1]} | Tel: {dados[2]} | Perfil: {extra[3]}\nNº Calçado: {extra[1] or 'N/A'} | Limite de Crédito Crediário: R$ {extra[2]:.2f}"
        self.lbl_detalhes_contato.config(text=txt, font=("Segoe UI", 9, "bold"), fg=self.cor_texto)

    def atualizar_calculos(self):
        try:
            v_base = float(self.ent_valor_base.get().replace(",", ".")) if self.ent_valor_base.get().strip() else 0.0
            enc = float(self.ent_encargos.get().replace(",", ".")) if self.ent_encargos.get().strip() else 0.0
            desc = float(self.ent_descontos.get().replace(",", ".")) if self.ent_descontos.get().strip() else 0.0
            pado = float(self.ent_valor_pago.get().replace(",", ".")) if self.ent_valor_pago.get().strip() else 0.0
            parc = int(self.ent_parc.get()) if self.ent_parc.get().strip() else 1
        except ValueError:
            self.lbl_painel_calculo.config(text="Erro de digitação nos campos de faturamento.", fg="red")
            return

        v_liquido = round(v_base + enc - desc, 2)
        devedor = round(v_liquido - pado, 2)
        
        if self.cb_recorrencia.get() == "Parcelado" and parc > 1:
            txt = f"Valor Bruto Ajustado: R$ {v_liquido:.2f} | {parc}x Carnê de R$ {round(v_liquido/parc, 2):.2f} | Saldo em Aberto: R$ {devedor:.2f}"
        else:
            txt = f"Valor Receita Líquida: R$ {v_liquido:.2f} | Saldo Pendente: R$ {devedor:.2f}"
        
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
        self.cb_cat.set(d[18] if d[18] else "Venda")  # categoria
        self.cb_status.set(d[19])
        
        self.ent_parc.delete(0, tk.END); self.ent_parc.insert(0, str(d[14] or 1))
        self.toggle_recorrencia()
        
        self.btn_salvar.config(text="⚙️ ATUALIZAR PARCELA / RECEBIMENTO", bg=self.cor_destaque)
        self.btn_deletar.grid()
        if self.venda_id:
            self.carregar_parcelas_por_venda(self.venda_id)
        else:
            self.carregar_parcelas_historico(d[5], d[6])

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

        valor_liquido_calculado = round(val_base_f + enc_f - desc_f, 2)
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
                # Modificação via CRUD Direto
                cursor.execute("""
                    UPDATE financeiro SET cliente_id=?, entidade_nome=?, descricao=?, valor=?, valor_base=?, valor_pago=?,
                                          encargos=?, descontos=?, data_lancamento=?, data_vencimento=?, data_pagamento=?,
                                          forma_pagamento=?, categoria=?, status=?, recorrencia=?
                    WHERE id=? AND tipo='Receita'
                """, (self.cliente_selecionado_id, nome, desc, valor_liquido_calculado, val_base_f, val_pago_f, enc_f, desc_f,
                      dat_lan, dat_ven, dat_pag, self.cb_forma.get(), self.cb_cat.get(), st, self.cb_recorrencia.get(), self.receita_id))
                conn.commit()
                messagebox.showinfo("Sucesso", "Título de Receita modificado.", parent=self)
            else:
                # Inclusão Manual/Avulsa
                for i in range(parcelas_totais):
                    venc_calculado = database.adicionar_meses(datetime.strptime(dat_ven, "%Y-%m-%d"), i).strftime("%Y-%m-%d")
                    v_parc_liquido = round(valor_liquido_calculado / parcelas_totais, 2)
                    cursor.execute("""
                        INSERT INTO financeiro (tipo, entidade_nome, descricao, valor, valor_base, valor_pago, encargos, descontos, forma_pagamento, recorrencia, total_parcelas, parcelas_atual, data_vencimento, data_pagamento, categoria, status, data_lancamento)
                        VALUES ('Receita', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (nome, f"{desc} ({i+1}/{parcelas_totais})", v_parc_liquido, val_base_f, val_pago_f if i==0 else 0.0, enc_f, desc_f, self.cb_forma.get(), self.cb_recorrencia.get(), parcelas_totais, i+1, venc_calculado, dat_pag if i==0 else None, self.cb_cat.get(), self.cb_status.get() if i==0 else 'Pendente', dat_lan))
                conn.commit()
                messagebox.showinfo("Sucesso", "Fluxo de contas a receber criado.", parent=self)

        if hasattr(self.master, "exibir_financeiro"): self.master.exibir_financeiro()
        self.destroy()

    def excluir_crud(self):
        if self.receita_id and messagebox.askyesno("Estorno Definitivo", "Deseja estornar e apagar este lançamento?", parent=self):
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
