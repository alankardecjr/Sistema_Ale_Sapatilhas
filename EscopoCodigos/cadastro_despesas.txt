import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import database 
import ui_utils

class JanelaGestaoFinanceira(tk.Toplevel):
    def __init__(self, master, dados_despesa=None):
        super().__init__(master)
        
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

        # --- Configurações da janela ---
        self.title("Alê Sapatilhas - Gestão Financeira")
        self.configure(bg=self.bg_fundo)
        self.resizable(False, False)
        
        self._manter_em_primeiro_plano()
        
        # --- Aplicar dimensões padrão (600px largura, altura aumentada) ---
        ui_utils.calcular_dimensoes_janela(self, largura_desejada=600, altura_desejada=950)
        
        self.despesa_id = dados_despesa[0] if dados_despesa else None
        
        self.list_formas = ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Boleto", "Outros"]
        self.list_categorias = ["Infraestrutura", "Compra Mercadoria", "Marketing", "Salários", "Impostos", "Outros"]
        self.list_recorrencia = ["Não Recorrente", "Fixo Mensal", "Parcelado"]
        self.list_status = ["Pendente", "Pago", "Atrasado", "Cancelado"]

        self.setup_styles()
        self.criar_widgets()
        
        if dados_despesa:
            self.preencher_dados(dados_despesa)
            
        self.grab_set()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground=self.bg_card, background=self.bg_card, 
                        arrowcolor=self.cor_btn_acao, bordercolor=self.cor_borda)
        style.configure("Busca.Treeview", background="#F8FAFC", rowheight=22, font=("Segoe UI", 9))
        style.configure("Hist.Treeview", background="#F8FAFC", rowheight=22, font=("Segoe UI", 9))

    def formatar_data_para_bd(self, data_str):
        try:
            return datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except: return None

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

        main_frame = tk.Frame(canvas, bg=self.bg_fundo, padx=20, pady=10)
        self.canvas_frame = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        def _update_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        main_frame.bind("<Configure>", _update_scroll_region)
        def _resize_frame(event):
            canvas.itemconfigure(self.canvas_frame, width=event.width)
        canvas.bind("<Configure>", _resize_frame)

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

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

        def criar_campo(parent, texto, row, col=0, colspan=1, width=15):
            tk.Label(parent, text=texto, bg=self.bg_fundo, fg=self.cor_lbl, 
                     font=("Segoe UI", 8, "bold")).grid(row=row, column=col, sticky="w", pady=(2, 0), padx=5)
            ent = tk.Entry(parent, width=width, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto,
                            relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
            ent.grid(row=row+1, column=col, columnspan=colspan, sticky="ew", ipady=2, padx=5)
            aplicar_estilo_foco(ent)
            return ent

        # --- Título ---
        tk.Label(main_frame, text=" Lançamento de Financeiro", bg=self.bg_fundo, 
                 fg=self.cor_texto, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 15))

        # --- BUSCA RÁPIDA (Conforme Cadastro Produtos) ---
        tk.Label(main_frame, text="🔍 BUSCA RÁPIDA", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=(5, 0))
        self.ent_busca_interna = tk.Entry(main_frame, font=("Segoe UI", 9), bg=self.bg_card, relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
        self.ent_busca_interna.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, ipady=3, pady=5)
        self.ent_busca_interna.bind("<KeyRelease>", self.filtrar_busca_interna)
        self.ent_busca_interna.bind("<Enter>", lambda e: self.ent_busca_interna.focus_set())
        
        self.tree_busca = ttk.Treeview(main_frame, columns=("id", "ent", "desc", "valor"), show="headings", height=3, style="Busca.Treeview")
        self.tree_busca.heading("id", text="ID"); self.tree_busca.heading("ent", text="FORNECEDOR")
        self.tree_busca.heading("desc", text="DESCRIÇÃO"); self.tree_busca.heading("valor", text="VALOR")
        for col in ("id", "ent", "desc", "valor"): self.tree_busca.column(col, width=80, anchor="w")
        self.tree_busca.grid(row=3, column=0, columnspan=3, sticky="ew", pady=2, padx=5)
        self.tree_busca.bind("<<TreeviewSelect>>", self.selecionar_da_busca)
        self.tree_busca.bind("<Double-1>", self.editar_despesa_duplo_clique)
        self.tree_busca.bind("<Button-3>", self.menu_contexto)

        # --- FORMULÁRIO ---
        self.ent_entidade = criar_campo(main_frame, "FORNECEDOR*", 4, 0, colspan=3)
        self.ent_desc = criar_campo(main_frame, "DESCRIÇÃO", 6, 0, colspan=3)

        # Linha de Valores, Encargos e Descontos
        tk.Label(main_frame, text="VALOR (R$)*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=8, column=0, sticky="w", padx=5)
        tk.Label(main_frame, text="ENCARGOS", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=8, column=1, sticky="w", padx=5)
        tk.Label(main_frame, text="DESCONTOS", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=8, column=2, sticky="w", padx=5)

        self.ent_valor = tk.Entry(main_frame, width=15, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto,
                            relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
        self.ent_valor.grid(row=9, column=0, sticky="ew", padx=5, ipady=2)
        aplicar_estilo_foco(self.ent_valor)
        self.ent_valor.bind("<KeyRelease>", lambda e: self.atualizar_calculo_parcela())

        frame_encargos = tk.Frame(main_frame, bg=self.bg_fundo)
        frame_encargos.grid(row=9, column=1, sticky="ew", padx=5)
        self.cb_encargos = ttk.Combobox(frame_encargos, values=("Valor Fixo", "Porcentagem"), state="readonly", font=("Segoe UI", 9))
        self.cb_encargos.set("Valor Fixo")
        self.cb_encargos.pack(side="left", fill="x", expand=True, ipady=2)
        self.cb_encargos.bind("<<ComboboxSelected>>", lambda e: self.atualizar_calculo_parcela())
        self.ent_encargos = tk.Entry(frame_encargos, width=10, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto,
                                     relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
        self.ent_encargos.pack(side="right", padx=(8, 0), ipady=2)
        aplicar_estilo_foco(self.ent_encargos)
        self.ent_encargos.bind("<KeyRelease>", lambda e: self.atualizar_calculo_parcela())

        frame_descontos = tk.Frame(main_frame, bg=self.bg_fundo)
        frame_descontos.grid(row=9, column=2, sticky="ew", padx=5)
        self.cb_descontos = ttk.Combobox(frame_descontos, values=("Valor Fixo", "Porcentagem"), state="readonly", font=("Segoe UI", 9))
        self.cb_descontos.set("Valor Fixo")
        self.cb_descontos.pack(side="left", fill="x", expand=True, ipady=2)
        self.cb_descontos.bind("<<ComboboxSelected>>", lambda e: self.atualizar_calculo_parcela())
        self.ent_descontos = tk.Entry(frame_descontos, width=10, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto,
                                      relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
        self.ent_descontos.pack(side="right", padx=(8, 0), ipady=2)
        aplicar_estilo_foco(self.ent_descontos)
        self.ent_descontos.bind("<KeyRelease>", lambda e: self.atualizar_calculo_parcela())

        # Linha de datas
        self.ent_lancamento = criar_campo(main_frame, "LANÇAMENTO", 10, 0, width=12)
        self.ent_vencimento = criar_campo(main_frame, "VENCIMENTO", 10, 1, width=12)
        self.ent_pagamento = criar_campo(main_frame, "PAGAMENTO", 10, 2, width=12)
        self.ent_lancamento.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.ent_vencimento.insert(0, datetime.now().strftime("%d/%m/%Y"))

        # Linha de status e configurações
        tk.Label(main_frame, text="STATUS*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=12, column=0, sticky="w", padx=5)
        self.cb_status = ttk.Combobox(main_frame, values=self.list_status, state="readonly", font=("Segoe UI", 9))
        self.cb_status.set("Pendente")
        self.cb_status.grid(row=13, column=0, sticky="ew", padx=5, ipady=2)

        tk.Label(main_frame, text="CATEGORIA*", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=12, column=1, sticky="w", padx=5)
        self.cb_cat = ttk.Combobox(main_frame, values=self.list_categorias, state="readonly", font=("Segoe UI", 9))
        self.cb_cat.grid(row=13, column=1, sticky="ew", padx=5, ipady=2)

        tk.Label(main_frame, text="FORMA DE PAGAMENTO", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=12, column=2, sticky="w", padx=5)
        self.cb_forma = ttk.Combobox(main_frame, values=self.list_formas, state="readonly", font=("Segoe UI", 9))
        self.cb_forma.set("Dinheiro")
        self.cb_forma.grid(row=13, column=2, sticky="ew", padx=5, ipady=2)

        tk.Label(main_frame, text="RECORRÊNCIA", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=14, column=0, sticky="w", padx=5)
        self.cb_recorrencia = ttk.Combobox(main_frame, values=self.list_recorrencia, state="readonly", font=("Segoe UI", 9))
        self.cb_recorrencia.set("Não Recorrente")
        self.cb_recorrencia.grid(row=15, column=0, sticky="ew", padx=5, ipady=2)
        self.cb_recorrencia.bind("<<ComboboxSelected>>", self.toggle_parcelas)

        # Frame para opções de recorrência
        self.frame_recorrencia = tk.Frame(main_frame, bg=self.bg_fundo)
        self.frame_recorrencia.grid(row=16, column=0, columnspan=3, sticky="ew", padx=5, pady=(5, 0))

        self.lbl_qtd_parc = tk.Label(self.frame_recorrencia, text="QUANT PARCELAS", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold"))
        self.lbl_qtd_parc.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.ent_qtd_parc = tk.Entry(self.frame_recorrencia, width=8, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto,
                                     relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
        self.ent_qtd_parc.grid(row=0, column=1, sticky="w", padx=(0, 20), ipady=2)
        self.ent_qtd_parc.insert(0, "1")
        aplicar_estilo_foco(self.ent_qtd_parc)
        self.ent_qtd_parc.bind("<KeyRelease>", lambda e: self.atualizar_calculo_parcela())

        self.lbl_periodo = tk.Label(self.frame_recorrencia, text="PERÍODO", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold"))
        self.lbl_periodo.grid(row=0, column=2, sticky="w", padx=(0, 10))
        self.cb_periodo = ttk.Combobox(self.frame_recorrencia, values=["Mensal", "Trimestral", "Anual"], state="readonly", font=("Segoe UI", 9))
        self.cb_periodo.set("Mensal")
        self.cb_periodo.grid(row=0, column=3, sticky="w", padx=(0, 20), ipady=2)

        self.lbl_calculo = tk.Label(main_frame, text="= 1x R$ 0.00", bg=self.bg_fundo, font=("Segoe UI", 9, "italic"), fg=self.cor_destaque)
        self.lbl_calculo.grid(row=17, column=0, sticky="w", padx=5)

        self.lbl_total_final = tk.Label(main_frame, text="Total c/ encargos/descontos: R$ 0.00", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 9, "italic"))
        self.lbl_total_final.grid(row=17, column=1, columnspan=2, sticky="e", padx=5)

        self.toggle_parcelas()

        # --- TREEVIEW HISTÓRICO ---
        tk.Label(main_frame, text="HISTÓRICO DAS PARCELAS", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 8, "bold")).grid(row=18, column=0, columnspan=3, sticky="w", pady=(15, 2), padx=5)
        self.tree_pagos = ttk.Treeview(main_frame, columns=("parc", "venc", "pagto", "valor", "forma", "status"), show="headings", height=3, style="Hist.Treeview")
        
        headers = {"parc": "Nº", "venc": "VENC.", "pagto": "PAGTO", "valor": "VALOR", "forma": "FORMA", "status": "STATUS"}
        for col, text in headers.items():
            self.tree_pagos.heading(col, text=text)
            self.tree_pagos.column(col, width=80, anchor="center")
        self.tree_pagos.grid(row=19, column=0, columnspan=3, sticky="ew", padx=5)

        # --- BOTÕES (Dual Mode e Hover) ---
        texto_btn = "ATUALIZAR DESPESA" if self.despesa_id else "SALVAR DESPESA"
        self.btn_salvar = tk.Button(main_frame, text=texto_btn, bg=self.cor_btn_acao, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", command=self.validar_e_salvar)
        self.btn_salvar.grid(row=20, column=0, columnspan=3, pady=(10, 0), sticky="ew", ipady=6)
        
        self.btn_cancelar = tk.Button(main_frame, text="CANCELAR", bg=self.cor_btn_sair, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", command=self.destroy)
        self.btn_cancelar.grid(row=21, column=0, columnspan=3, pady=(10, 0), sticky="ew", ipady=6)

        # Bind Hovers
        self.btn_salvar.bind("<Enter>", lambda e: e.widget.config(bg=self.cor_hover_btn))
        self.btn_salvar.bind("<Leave>", lambda e: e.widget.config(bg=self.cor_btn_acao))
        self.btn_cancelar.bind("<Enter>", lambda e: e.widget.config(bg=self.cor_hover_btn))
        self.btn_cancelar.bind("<Leave>", lambda e: e.widget.config(bg=self.cor_btn_sair))

        # --- Menu de contexto (botão direito) ---
        self.menu_contexto = tk.Menu(self, tearoff=0)
        self.menu_contexto.add_command(label="Editar", command=self.editar_despesa_menu)
        self.menu_contexto.add_command(label="Quitar", command=self.quitar_despesa_menu)
        self.menu_contexto.add_command(label="Restaurar", command=self.restaurar_despesa_menu)
        self.menu_contexto.add_separator()
        self.menu_contexto.add_command(label="Sair", command=self.destroy)

        try:
            self.atualizar_tree_busca()
        except Exception:
            pass  # Banco pode não estar inicializado durante testes

    # --- LÓGICA ---
    def toggle_parcelas(self, event=None):
        if self.cb_recorrencia.get() == "Parcelado":
            self.lbl_qtd_parc.grid()
            self.ent_qtd_parc.grid()
            self.lbl_periodo.grid_remove()
            self.cb_periodo.grid_remove()
        elif self.cb_recorrencia.get() == "Fixo Mensal":
            self.lbl_qtd_parc.grid_remove()
            self.ent_qtd_parc.grid_remove()
            self.lbl_periodo.grid()
            self.cb_periodo.grid()
        else:  # Não Recorrente
            self.lbl_qtd_parc.grid_remove()
            self.ent_qtd_parc.grid_remove()
            self.lbl_periodo.grid_remove()
            self.cb_periodo.grid_remove()
        self.atualizar_calculo_parcela()

    def calcular_total_despesa(self):
        try:
            valor_base = float(self.ent_valor.get().replace(",", "."))
        except Exception:
            return None

        try:
            encargos_raw = float(self.ent_encargos.get().replace(",", ".")) if self.ent_encargos.get().strip() else 0.0
        except Exception:
            return None

        try:
            descontos_raw = float(self.ent_descontos.get().replace(",", ".")) if self.ent_descontos.get().strip() else 0.0
        except Exception:
            return None

        if self.cb_encargos.get() == "Porcentagem":
            encargos_total = round(valor_base * (encargos_raw / 100), 2)
        else:
            encargos_total = round(encargos_raw, 2)

        if self.cb_descontos.get() == "Porcentagem":
            descontos_total = round(valor_base * (descontos_raw / 100), 2)
        else:
            descontos_total = round(descontos_raw, 2)

        valor_final = round(valor_base + encargos_total - descontos_total, 2)
        return {
            "valor_base": valor_base,
            "encargos": encargos_total,
            "descontos": descontos_total,
            "valor_final": valor_final
        }

    def atualizar_calculo_parcela(self):
        resultado = self.calcular_total_despesa()
        if not resultado:
            self.lbl_calculo.config(text="= Erro no cálculo")
            self.lbl_total_final.config(text="Total c/ encargos/descontos: -")
            return

        qtd = 1
        periodo = ""
        if self.cb_recorrencia.get() == "Parcelado":
            try:
                qtd = max(1, int(self.ent_qtd_parc.get()))
            except Exception:
                qtd = 1
        elif self.cb_recorrencia.get() == "Fixo Mensal":
            periodo = f" ({self.cb_periodo.get().lower()})"

        if self.cb_recorrencia.get() == "Parcelado":
            parcela_valor = round(resultado["valor_final"] / qtd, 2)
        else:
            parcela_valor = resultado["valor_final"]

        texto = f"= {qtd}x R$ {parcela_valor:.2f}{periodo}"
        if self.cb_recorrencia.get() == "Fixo Mensal":
            texto += " (valor fixo)"

        self.lbl_calculo.config(text=texto)
        self.lbl_total_final.config(text=f"Total c/ encargos/descontos: R$ {resultado['valor_final']:.2f}")

    def atualizar_tree_busca(self):
        self.tree_busca.delete(*self.tree_busca.get_children())
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, entidade_nome, descricao, valor FROM financeiro WHERE tipo='Despesa' LIMIT 20")
            for d in cursor.fetchall(): self.tree_busca.insert("", "end", values=d)

    def validar_e_salvar(self):
        # --- Lógica de persistência DUAL ---
        d = {
            "ent": self.ent_entidade.get(), "desc": self.ent_desc.get(),
            "val": self.ent_valor.get().replace(",", "."),
            "lanc": self.formatar_data_para_bd(self.ent_lancamento.get()),
            "venc": self.formatar_data_para_bd(self.ent_vencimento.get()),
            "pagto": self.formatar_data_para_bd(self.ent_pagamento.get()) if self.ent_pagamento.get().strip() else None,
            "forma": self.cb_forma.get(), "cat": self.cb_cat.get(), "status": self.cb_status.get(),
            "enc_tipo": self.cb_encargos.get(), "desc_tipo": self.cb_descontos.get(),
            "enc_val": self.ent_encargos.get().replace(",", ".") if self.ent_encargos.get().strip() else "0",
            "desc_val": self.ent_descontos.get().replace(",", ".") if self.ent_descontos.get().strip() else "0"
        }
        
        if not all([d["ent"], d["desc"], d["val"], d["lanc"], d["venc"]]):
            messagebox.showwarning("Erro", "Preencha os campos obrigatórios (*) e verifique as datas.", parent=self)
            return

        try:
            resultado = self.calcular_total_despesa()
            if not resultado:
                raise ValueError("Dados inválidos para encargos/descontos ou valor")

            valor_base = resultado["valor_base"]
            valor_final = resultado["valor_final"]
            enc_val = float(d["enc_val"])
            desc_val = float(d["desc_val"])
            parc = int(self.ent_qtd_parc.get()) if self.cb_recorrencia.get() != "Não Recorrente" else 1

            if self.despesa_id:
                database.atualizar_despesa(
                    self.despesa_id,
                    entidade_nome=d["ent"], descricao=d["desc"], valor=valor_final,
                    valor_base=valor_base,
                    data_lancamento=d["lanc"], data_vencimento=d["venc"], data_pagamento=d["pagto"],
                    forma_pagamento=d["forma"], categoria=d["cat"], status=d["status"], recorrencia=self.cb_recorrencia.get(),
                    tipo_encargos=d["enc_tipo"], valor_encargos=enc_val,
                    tipo_descontos=d["desc_tipo"], valor_descontos=desc_val
                )
                messagebox.showinfo("Sucesso", "Despesa atualizada!", parent=self)
            else:
                sucesso, mensagem = database.cadastrar_despesa(
                    d["ent"], d["desc"], d["cat"], valor_base,
                    self.cb_recorrencia.get(), d["venc"], d["forma"], d["status"], parc,
                    data_lancamento=d["lanc"], data_pagamento=d["pagto"],
                    tipo_encargos=d["enc_tipo"], valor_encargos=enc_val,
                    tipo_descontos=d["desc_tipo"], valor_descontos=desc_val,
                    valor_base=valor_base
                )
                if not sucesso:
                    messagebox.showerror("Erro", mensagem, parent=self)
                    return
                messagebox.showinfo("Sucesso", "Nova despesa cadastrada!", parent=self)
            
            if hasattr(self.master, "exibir_financeiro"): self.master.exibir_financeiro()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def preencher_dados(self, d):
        # d vem da tabela financeiro: (id, tipo, venda_id, entidade, desc, valor, parc_at, parc_tot, venc, pagto, forma, cat, status, recorrencia, data_lancamento, tipo_encargos, valor_encargos, tipo_descontos, valor_descontos, valor_base)
        self.despesa_id = d[0]
        self.ent_entidade.delete(0, tk.END); self.ent_entidade.insert(0, d[3] if d[3] else "")
        self.ent_desc.delete(0, tk.END); self.ent_desc.insert(0, d[4])
        valor_base = d[19] if len(d) > 19 and d[19] else d[5]
        self.ent_valor.delete(0, tk.END); self.ent_valor.insert(0, f"{valor_base:.2f}")

        data_lanc = None
        if len(d) > 14 and d[14]:
            try:
                data_lanc = datetime.strptime(d[14], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                data_lanc = datetime.now().strftime("%d/%m/%Y")
        else:
            data_lanc = datetime.now().strftime("%d/%m/%Y")
        self.ent_lancamento.delete(0, tk.END); self.ent_lancamento.insert(0, data_lanc)

        if d[8]:
            try:
                venc_br = datetime.strptime(d[8], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                venc_br = d[8]
        else:
            venc_br = ""
        self.ent_vencimento.delete(0, tk.END); self.ent_vencimento.insert(0, venc_br)

        if d[9]:
            try:
                pagto_br = datetime.strptime(d[9], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                pagto_br = d[9]
        else:
            pagto_br = ""
        self.ent_pagamento.delete(0, tk.END); self.ent_pagamento.insert(0, pagto_br)

        self.cb_forma.set(d[10] if d[10] else "Dinheiro")
        self.cb_cat.set(d[11] if d[11] else "Outros")
        self.cb_status.set(d[12])
        recorrencia = d[13] if len(d) > 13 else ("Parcelar" if d[7] > 1 else "Não Recorrente")
        if recorrencia == "Fixa Mensal":
            recorrencia = "Fixo Mensal"
        self.cb_recorrencia.set(recorrencia)

        self.cb_encargos.set(d[15] if len(d) > 15 and d[15] else "Valor Fixo")
        self.ent_encargos.delete(0, tk.END); self.ent_encargos.insert(0, f"{d[16]:.2f}" if len(d) > 16 and d[16] else "0")
        self.cb_descontos.set(d[17] if len(d) > 17 and d[17] else "Valor Fixo")
        self.ent_descontos.delete(0, tk.END); self.ent_descontos.insert(0, f"{d[18]:.2f}" if len(d) > 18 and d[18] else "0")

        self.ent_qtd_parc.delete(0, tk.END)
        self.ent_qtd_parc.insert(0, str(d[7] if d[7] > 1 else 1))
        self.toggle_parcelas()
        self.btn_salvar.config(text="ATUALIZAR DESPESA", bg=self.cor_hover_field)

        # Preencher histórico de parcelas
        self.tree_pagos.delete(*self.tree_pagos.get_children())
        with database.conectar() as conn:
            cursor = conn.cursor()
            # Buscar todas as parcelas relacionadas (mesma entidade e descrição, mas diferentes parcela_atual)
            cursor.execute("""
                SELECT parcela_atual, data_vencimento, data_pagamento, valor, forma_pagamento, status
                FROM financeiro 
                WHERE entidade_nome = ? AND descricao = ? AND tipo = 'Despesa'
                ORDER BY parcela_atual
            """, (d[3], d[4]))
            parcelas = cursor.fetchall()
            for parc in parcelas:
                venc = datetime.strptime(parc[1], "%Y-%m-%d").strftime("%d/%m/%Y") if parc[1] else ""
                pagto = datetime.strptime(parc[2], "%Y-%m-%d").strftime("%d/%m/%Y") if parc[2] else ""
                self.tree_pagos.insert("", "end", values=(parc[0], venc, pagto, f"R$ {parc[3]:.2f}", parc[4] or "", parc[5]))
        self.tree_busca.delete(*self.tree_busca.get_children())
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, entidade_nome, descricao, valor FROM financeiro WHERE tipo='Despesa' LIMIT 20")
            for d in cursor.fetchall(): self.tree_busca.insert("", "end", values=d)

    def filtrar_busca_interna(self, e):
        t = self.ent_busca_interna.get().lower()
        self.tree_busca.delete(*self.tree_busca.get_children())
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, entidade_nome, descricao, valor FROM financeiro WHERE tipo='Despesa' AND (entidade_nome LIKE ? OR descricao LIKE ?)", (f'%{t}%', f'%{t}%'))
            for d in cursor.fetchall(): self.tree_busca.insert("", "end", values=d)

    def selecionar_da_busca(self, e):
        sel = self.tree_busca.selection()
        if not sel: return
        id_d = self.tree_busca.item(sel[0])["values"][0]
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM financeiro WHERE id=?", (id_d,))
            self.preencher_dados(cursor.fetchone())


    def editar_despesa_duplo_clique(self, event):
        """Editar despesa/receita com duplo clique - distingue tipo"""
        sel = self.tree_busca.selection()
        if not sel: return
        id_item = self.tree_busca.item(sel[0])["values"][0]
        
        # Verificar se é receita ou despesa
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tipo, venda_id FROM financeiro WHERE id=?", (id_item,))
            result = cursor.fetchone()
            if not result:
                messagebox.showerror("Erro", "Registro financeiro não encontrado.", parent=self)
                return
            tipo, venda_id = result
        
        if tipo == "Receita":
            if not venda_id:
                messagebox.showerror("Erro", "Registro de receita sem venda vinculada.", parent=self)
                return
            from cadastro_vendas import JanelaCadastroVendas
            with database.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT v.id, c.nome, c.telefone, GROUP_CONCAT(p.produto), v.valor_total, v.forma_pagamento, v.qtd_parcelas, v.desconto, v.data_venda
                    FROM vendas v
                    JOIN clientes c ON v.cliente_id = c.id
                    JOIN itens_venda vi ON v.id = vi.venda_id
                    JOIN produtos p ON vi.produto_id = p.id
                    WHERE v.id = ?
                    GROUP BY v.id
                """, (venda_id,))
                dados_venda = cursor.fetchone()

            if dados_venda:
                dados_venda_dict = {
                    'id': dados_venda[0],
                    'cliente': f"{dados_venda[1]} - {dados_venda[2]}",
                    'produtos': dados_venda[3],
                    'total': dados_venda[4],
                    'forma': dados_venda[5],
                    'parcelas': dados_venda[6],
                    'desconto': dados_venda[7],
                    'data': dados_venda[8]
                }
                JanelaCadastroVendas(self.master, dados_venda=dados_venda_dict)
            else:
                messagebox.showinfo("Info", "Venda não encontrada para o registro selecionado.", parent=self)
        else:
            with database.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM financeiro WHERE id=?", (id_item,))
                dados = cursor.fetchone()
                if dados:
                    self.preencher_dados(dados)
                else:
                    messagebox.showerror("Erro", "Despesa não encontrada.", parent=self)

    def menu_contexto(self, event):
        """Mostrar menu de contexto no botão direito"""
        try:
            self.tree_busca.selection_set(self.tree_busca.identify_row(event.y))
            self.menu_contexto.post(event.x_root, event.y_root)
        except:
            pass

    def editar_despesa_menu(self):
        """Editar despesa/receita via menu de contexto"""
        if messagebox.askyesno("Confirmar", "Deseja editar este lançamento financeiro?", parent=self):
            self.editar_despesa_duplo_clique(None)

    def quitar_despesa_menu(self):
        """Quitar despesa via menu de contexto"""
        sel = self.tree_busca.selection()
        if not sel: return
        id_d = self.tree_busca.item(sel[0])["values"][0]
        
        if messagebox.askyesno("Confirmar", "Deseja quitar esta despesa?"):
            try:
                database.quitar_titulo_financeiro(id_d, "Diversos")
                messagebox.showinfo("Sucesso", "Despesa quitada!", parent=self)
                self.atualizar_tree_busca()
                if hasattr(self.master, "exibir_financeiro"): 
                    self.master.exibir_financeiro()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao quitar despesa: {str(e)}", parent=self)

class VisualizarRecibo(tk.Toplevel):
    """Classe para visualizar recibo de venda"""
    def __init__(self, master, id_venda):
        super().__init__(master)
        
        # --- Paleta de cores ---
        paleta = ui_utils.get_paleta()
        self.bg_fundo = paleta["bg_fundo"]
        self.bg_card = paleta["bg_card"]
        self.cor_texto = paleta["cor_texto"]
        self.cor_destaque = paleta["cor_destaque"]
        
        self.title("Recibo de Venda")
        self.configure(bg=self.bg_fundo)
        ui_utils.calcular_dimensoes_janela(self, largura_desejada=560, altura_desejada=620)
        
        # Buscar dados da venda
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.id, c.nome, c.cpf, c.telefone, c.email, c.endereco_completo, c.bairro, c.cidade, c.cep, v.valor_bruto, v.desconto, v.valor_total, v.forma_pagamento, v.qtd_parcelas, v.data_venda, v.status_venda, v.vendedor,
                       GROUP_CONCAT(p.produto || ' (' || vi.quantidade || 'x R$ ' || vi.preco_unitario || ' = R$ ' || vi.subtotal || ')', '\n') as produtos
                FROM vendas v
                JOIN clientes c ON v.cliente_id = c.id
                JOIN itens_venda vi ON v.id = vi.venda_id
                JOIN produtos p ON vi.produto_id = p.id
                WHERE v.id = ?
                GROUP BY v.id
            """, (id_venda,))
            dados = cursor.fetchone()
        
        if not dados:
            messagebox.showerror("Erro", "Venda não encontrada!", parent=self)
            self.destroy()
            return
        
        # Criar interface
        main_frame = tk.Frame(self, bg=self.bg_fundo, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        tk.Label(main_frame, text="🧾 DETALHES DA VENDA", bg=self.bg_fundo, 
                 fg=self.cor_destaque, font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        
        # Informações da venda e cliente
        info_text = f"""
=== DADOS DA VENDA ===
ID da Venda: {dados[0]}
Data: {dados[18]}
Status: {dados[20]}
Vendedor: {dados[21] or 'N/A'}

=== DADOS DO CLIENTE ===
Nome: {dados[1]}
CPF: {dados[2]}
Telefone: {dados[3]}
Email: {dados[4] or 'N/A'}
Endereço: {dados[7] or 'N/A'}
Bairro: {dados[8] or 'N/A'}
Cidade: {dados[9] or 'N/A'}
CEP: {dados[10] or 'N/A'}

=== DADOS FINANCEIROS ===
Valor Bruto: R$ {dados[14]:.2f}
Desconto: R$ {dados[15]:.2f}
Valor Total: R$ {dados[16]:.2f}
Forma de Pagamento: {dados[17]}
Parcelas: {dados[19]}x

=== PRODUTOS VENDIDOS ===
{dados[22]}
        """
        
        lbl_info = tk.Label(main_frame, text=info_text.strip(), bg=self.bg_card, fg=self.cor_texto,
                           font=("Courier New", 9), justify="left", relief="solid", borderwidth=1)
        lbl_info.pack(fill="both", expand=True, pady=(0, 20))
        
        # Botão fechar
        tk.Button(main_frame, text="FECHAR", bg=self.cor_destaque, fg="white",
                 font=("Segoe UI", 10, "bold"), command=self.destroy).pack()
        
        self.grab_set()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    JanelaGestaoFinanceira(root)
    root.mainloop()

