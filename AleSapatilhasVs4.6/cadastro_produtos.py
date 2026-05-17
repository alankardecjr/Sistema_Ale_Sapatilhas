"""
cadastro_produtos.py — Gestão de estoque e ficha técnica do produto.

Integração com contatos: fornecedor_id referencia clientes (tipo Fornecedor).
SKU único com variação automática quando cor/tamanho divergem.
"""

import os
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from datetime import datetime
import database
import ui_utils


class JanelaCadastroProdutos(tk.Toplevel):
    """Cadastro de SKU, grade (cor/tamanho) e vínculo com fornecedor."""
    def __init__(self, master, dados_produto=None):
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
        self.title("Alê Sapatilhas - Gestão do Estoque")
        self.configure(bg=self.bg_fundo)
        self.resizable(False, False)
        
        self._manter_em_primeiro_plano()
        
        # --- Aplicar dimensões padrão (600px largura, altura ajustada) ---
        ui_utils.calcular_dimensoes_janela(self, largura_desejada=700, altura_desejada=850)

        self.produto_id = dados_produto[0] if dados_produto else None
        self.fornecedor_id = None
        
        self.list_categorias = ["Sapatilhas", "Rasteiras", "Salto Fino", "Salto Block", "Mules", "Tênis", "Botas", "Biquinis", "Roupas"]     
        self.list_materiais = ["Couro", "Camurça", "Nobuck", "PU", "Verniz", "Algodão", "Poliamida", "Suplex"]      
        self.list_tamanhos = [str(i) for i in range(33, 41)] + ["G", "GG", "M", "P", "U"]        
        self.list_cores = ["Amarelo", "Azul", "Branco", "Caramelo", "Massala", "Nude", "Off", "Preto", "Rosa", "Verde", "Vermelho"]
        self.list_status = ["Disponível", "Indisponível", "Esgotado", "Promocional"]

        self.setup_styles()
        self.criar_widgets()
    
        if dados_produto:
            self.preencher_dados(dados_produto)
     
        self.grab_set()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground=self.bg_card, background=self.bg_card, 
                        arrowcolor=self.cor_btn_acao, bordercolor=self.cor_borda)
        style.configure("Busca.Treeview", background="#F8FAFC", rowheight=22, font=("Segoe UI", 9))

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

        def criar_campo(parent, texto, row, col=0, colspan=2):
            tk.Label(parent, text=texto, bg=self.bg_fundo, fg=self.cor_lbl, 
                     font=("Segoe UI", 8, "bold")).grid(row=row, column=col, sticky="w", pady=(3, 0))
            ent = tk.Entry(parent, font=("Segoe UI", 10), bg=self.bg_card, fg=self.cor_texto,
                            relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
            ent.grid(row=row+1, column=col, columnspan=colspan, sticky="ew", ipady=3, padx=(0, 5) if colspan==1 else 0)
            aplicar_estilo_foco(ent)
            return ent

        def criar_combo(parent, texto, lista, row, col, span=1):
            tk.Label(parent, text=texto, bg=self.bg_fundo, fg=self.cor_lbl, 
                     font=("Segoe UI", 8, "bold")).grid(row=row, column=col, sticky="w", pady=(3, 0))
            combo = ttk.Combobox(parent, values=lista, font=("Segoe UI", 10), state="readonly")
            combo.set(lista[0])
            combo.grid(row=row+1, column=col, columnspan=span, sticky="ew", padx=(0, 5) if col==0 else 0)
            return combo

        tk.Label(main_frame, text="Ficha Cadastral do Produto", bg=self.bg_fundo, 
                 fg=self.cor_texto, font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        tk.Label(main_frame, text="🔍 BUSCA RÁPIDA", bg=self.bg_fundo, 
                 fg=self.cor_destaque, font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        self.ent_busca_interna = tk.Entry(main_frame, font=("Segoe UI", 10), bg=self.bg_card, relief="flat",
                                          highlightbackground=self.cor_borda, highlightthickness=1)
        self.ent_busca_interna.grid(row=2, column=0, columnspan=2, sticky="ew", ipady=3)
        self.ent_busca_interna.bind("<KeyRelease>", self.filtrar_busca_interna)
        aplicar_estilo_foco(self.ent_busca_interna)

        self.tree_busca = ttk.Treeview(main_frame, columns=("id", "prod", "forn"), show="headings", height=2, style="Busca.Treeview")
        self.tree_busca.heading("id", text="ID")
        self.tree_busca.heading("prod", text="MODELO")
        self.tree_busca.heading("forn", text="FORNECEDOR")
        self.tree_busca.column("id", width=40, anchor="center")
        self.tree_busca.grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)
        self.tree_busca.bind("<<TreeviewSelect>>", self.selecionar_da_busca)

        tk.Frame(main_frame, height=1, bg=self.cor_borda).grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

        self.ent_produto = criar_campo(main_frame, "DESCRIÇÃO DO MODELO*", 5)
        self.cb_cat      = criar_combo(main_frame, "CATEGORIA*", self.list_categorias, 7, 0)
        self.cb_mat      = criar_combo(main_frame, "MATERIAL", self.list_materiais, 7, 1)

        self.ent_custo = criar_campo(main_frame, "PREÇO DE CUSTO (R$)*", 9, col=0, colspan=1)
        self.ent_custo.bind("<KeyRelease>", self.calcular_markup)
        
        tk.Label(main_frame, text="PREÇO DE VENDA (R$)*", bg=self.bg_fundo, fg=self.cor_lbl, 
                 font=("Segoe UI", 8, "bold")).grid(row=9, column=1, sticky="w", pady=(3, 0))
        self.ent_venda = tk.Entry(main_frame, font=("Segoe UI", 10, "bold"), bg="#E2E8F0", fg=self.cor_destaque, 
                                  relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
        self.ent_venda.grid(row=10, column=1, sticky="ew", ipady=3)

        tk.Label(main_frame, text="FORNECEDOR (CADASTRO UNIFICADO)*", bg=self.bg_fundo, fg=self.cor_lbl,
                 font=("Segoe UI", 8, "bold")).grid(row=11, column=0, columnspan=2, sticky="w", pady=(3, 0))
        self.ent_busca_forn = tk.Entry(main_frame, font=("Segoe UI", 9), bg=self.bg_card, relief="flat", highlightthickness=1, highlightbackground=self.cor_borda)
        self.ent_busca_forn.grid(row=12, column=0, columnspan=2, sticky="ew", ipady=3)
        self.ent_busca_forn.bind("<KeyRelease>", self.pesquisar_fornecedores_produto)
        aplicar_estilo_foco(self.ent_busca_forn)
        self.tree_forn = ttk.Treeview(main_frame, columns=("id", "nome"), show="headings", height=2, style="Busca.Treeview")
        self.tree_forn.heading("id", text="ID"); self.tree_forn.heading("nome", text="FORNECEDOR")
        self.tree_forn.column("id", width=40, anchor="center")
        self.tree_forn.grid(row=13, column=0, columnspan=2, sticky="ew", pady=2)
        self.tree_forn.bind("<<TreeviewSelect>>", self.selecionar_fornecedor_produto)
        self.ent_forn = criar_campo(main_frame, "FORNECEDOR SELECIONADO", 14)
        self.ent_forn.config(state="readonly")

        # --- Campo Data do Lançamento ---
        tk.Label(main_frame, text="DATA DO LANÇAMENTO", bg=self.bg_fundo, fg=self.cor_lbl, 
                 font=("Segoe UI", 8, "bold")).grid(row=16, column=0, sticky="w", pady=(3, 0))
        self.ent_data_lancamento = tk.Entry(main_frame, font=("Segoe UI", 10), bg=self.bg_card, fg=self.cor_texto,
                                           relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
        self.ent_data_lancamento.grid(row=17, column=0, sticky="ew", ipady=3, padx=(0, 5))
        self.ent_data_lancamento.insert(0, datetime.now().strftime("%d/%m/%Y"))
        aplicar_estilo_foco(self.ent_data_lancamento)

        # --- Campo Status do Item ---
        tk.Label(main_frame, text="STATUS DO ITEM*", bg=self.bg_fundo, fg=self.cor_lbl, 
                 font=("Segoe UI", 8, "bold")).grid(row=16, column=1, sticky="w", pady=(3, 0))
        self.var_status = tk.StringVar(value="Disponível")
        self.opt_status = tk.OptionMenu(main_frame, self.var_status, *self.list_status)
        self.opt_status.config(bg=self.bg_card, fg=self.cor_texto, relief="flat", highlightthickness=1, 
                                highlightbackground=self.cor_borda, font=("Segoe UI", 10), cursor="hand2")
        self.opt_status.grid(row=17, column=1, sticky="ew", pady=(1, 0))

        # --- GRADE DE ESTOQUE E FOTO ---
        tk.Label(main_frame, text="GRADE DE ESTOQUE", bg=self.bg_fundo, fg=self.cor_texto, 
                 font=("Segoe UI", 9, "bold")).grid(row=18, column=0, sticky="w", pady=(10, 2))
        
        tk.Label(main_frame, text="FOTO DO PRODUTO", bg=self.bg_fundo, fg=self.cor_texto, 
                 font=("Segoe UI", 9, "bold")).grid(row=18, column=1, sticky="w", pady=(10, 2))
        
        # Frame para grade e foto lado a lado
        frame_conteudo = tk.Frame(main_frame, bg=self.bg_fundo)
        frame_conteudo.grid(row=19, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        frame_conteudo.columnconfigure(0, weight=1)
        frame_conteudo.columnconfigure(1, weight=1)

        # --- GRADE DE ESTOQUE (lado esquerdo) ---
        frame_grade = tk.LabelFrame(frame_conteudo, bg=self.bg_card, relief="groove", borderwidth=1, padx=10, pady=10, text="Estoque")
        frame_grade.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        frame_grade.columnconfigure(0, weight=1)

        self.cb_cor = criar_combo(frame_grade, "COR*", self.list_cores, 0, 0, 2)
        self.cb_tam = criar_combo(frame_grade, "TAMANHO*", self.list_tamanhos, 2, 0, 2)
        self.ent_qtd = criar_campo(frame_grade, "QUANTIDADE*", 4, col=0, colspan=1)
        self.lbl_qtd_atual = tk.Label(frame_grade, text="", bg=self.bg_card, fg=self.cor_lbl, font=("Segoe UI", 8), anchor="w")
        self.lbl_qtd_atual.grid(row=6, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # --- ESPAÇO PARA FOTO (lado direito) ---
        frame_foto = tk.LabelFrame(frame_conteudo, bg=self.bg_card, relief="groove", borderwidth=1, padx=10, pady=10, text="Foto")
        frame_foto.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Placeholder para foto
        self.lbl_foto = tk.Label(frame_foto, text="📷\n\nClique para\nadicionar foto", 
                                bg="#F8FAFC", fg=self.cor_texto, font=("Segoe UI", 10), 
                                relief="flat", cursor="hand2", width=15, height=6)
        self.lbl_foto.pack(expand=True, fill="both", padx=5, pady=5)
        self.lbl_foto.bind("<Button-1>", self.selecionar_foto)
        self.lbl_foto.bind("<Button-3>", self.menu_contexto_foto)

        # --- Campo SKU (no final, apenas visualização) ---
        tk.Label(main_frame, text="CÓDIGO DO PRODUTO (SKU)", bg=self.bg_fundo, fg=self.cor_lbl, 
                 font=("Segoe UI", 8, "bold")).grid(row=20, column=0, sticky="w", pady=(10, 0))
        self.ent_sku = tk.Entry(main_frame, font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg=self.cor_destaque, 
                               relief="flat", highlightbackground=self.cor_borda, highlightthickness=1, state="readonly")
        self.ent_sku.grid(row=21, column=0, columnspan=2, sticky="ew", ipady=3, pady=(0, 10))
        
        # --- BOTÕES (Dual Mode e Hover) ---
        texto_botao = "ATUALIZAR PRODUTO" if self.produto_id else "SALVAR PRODUTO"
        cor_base_acao = self.cor_hover_field if self.produto_id else self.cor_btn_acao

        self.btn_salvar = tk.Button(main_frame, text=texto_botao, bg=cor_base_acao, fg="white", 
                                    font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", 
                                    command=self.validar_e_salvar)
        self.btn_salvar.grid(row=22, column=0, columnspan=2, pady=(10, 0), sticky="ew", ipady=6)
        
        self.btn_cancelar = tk.Button(main_frame, text="FECHAR JANELA", bg=self.cor_btn_sair, fg="white", 
                                      font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", 
                                      command=self.destroy)
        self.btn_cancelar.grid(row=23, column=0, columnspan=2, pady=(10, 0), sticky="ew", ipady=6)

        self.btn_salvar.bind("<Enter>", lambda e: e.widget.config(bg=self.cor_hover_btn))
        self.btn_salvar.bind("<Leave>", lambda e: e.widget.config(bg=cor_base_acao))
        self.btn_cancelar.bind("<Enter>", lambda e: e.widget.config(bg=self.cor_hover_btn))
        self.btn_cancelar.bind("<Leave>", lambda e: e.widget.config(bg=self.cor_btn_sair))

        # --- Menu de contexto (botão direito) ---
        self.menu_contexto = tk.Menu(self, tearoff=0)
        self.menu_contexto.add_command(label="Editar Item", command=self.editar_produto_menu)
        self.menu_contexto.add_command(label="Visualizar Item", command=self.visualizar_produto_menu)
        self.menu_contexto.add_separator()
        self.menu_contexto.add_command(label="✓ Disponível", command=self.disponibilizar_produto_menu)
        self.menu_contexto.add_command(label="✗ Indisponível", command=self.indisponibilizar_produto_menu)
        self.menu_contexto.add_command(label="⭐ Promocional", command=self.promocional_produto_menu)

        # Bindings para treeview
        self.tree_busca.bind("<Double-1>", self.editar_produto_duplo_clique)
        self.tree_busca.bind("<Button-3>", self.menu_contexto_produto)

        self.atualizar_tree_busca()
        self.pesquisar_fornecedores_produto()
        if not self.produto_id:  # Só gera SKU automático para novos produtos
            self.gerar_sku_automatico()

    def pesquisar_fornecedores_produto(self, event=None):
        termo = self.ent_busca_forn.get().strip()
        self.tree_forn.delete(*self.tree_forn.get_children())
        for f in database.listar_contatos(tipo='Fornecedor', termo=termo):
            self.tree_forn.insert("", "end", values=(f[0], f[2]))

    def selecionar_fornecedor_produto(self, event=None):
        sel = self.tree_forn.selection()
        if not sel:
            return
        vals = self.tree_forn.item(sel[0], "values")
        self.fornecedor_id = vals[0]
        self.ent_forn.config(state="normal")
        self.ent_forn.delete(0, tk.END)
        self.ent_forn.insert(0, vals[1])
        self.ent_forn.config(state="readonly")

    def calcular_markup(self, event=None):
        try:
            custo = self.ent_custo.get().replace(",", ".")
            if custo:
                venda = float(custo) * 2.5
                self.ent_venda.delete(0, tk.END)
                self.ent_venda.insert(0, f"{venda:.2f}")
        except ValueError:
            self.ent_venda.delete(0, tk.END)

    def atualizar_tree_busca(self):
        self.tree_busca.delete(*self.tree_busca.get_children())
        for p in database.exibir_produtos():
            self.tree_busca.insert("", "end", values=(p[0], p[2], p[10]))

    def filtrar_busca_interna(self, event=None):
        termo = self.ent_busca_interna.get().lower()
        self.tree_busca.delete(*self.tree_busca.get_children())
        for p in database.exibir_produtos():
            if termo in str(p[2]).lower() or termo in str(p[10]).lower():
                self.tree_busca.insert("", "end", values=(p[0], p[2], p[10]))

    def selecionar_da_busca(self, event):
        selecao = self.tree_busca.selection()
        if not selecao: return
        id_prod = self.tree_busca.item(selecao[0])["values"][0]
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM produtos WHERE id = ?", (id_prod,))
            dados = cursor.fetchone()
            if dados:
                self.preencher_dados(dados)

    def validar_e_salvar(self):
        try:
            d = {
                "sku": self.ent_sku.get().strip(),
                "produto": self.ent_produto.get().strip(),
                "cor": self.cb_cor.get(), 
                "tam": self.cb_tam.get(),
                "custo": self.ent_custo.get().replace(",", "."),
                "venda": self.ent_venda.get().replace(",", "."),
                "qtd": int(self.ent_qtd.get().strip()),
                "cat": self.cb_cat.get(), 
                "mat": self.cb_mat.get(),
                "forn": self.ent_forn.get().strip(),
                "forn_id": self.fornecedor_id,
                "status": self.var_status.get()
            }

            if not d["produto"] or not d["cor"] or not d["custo"] or not d["forn_id"]:
                messagebox.showwarning("Atenção", "Preencha os campos obrigatórios e selecione um fornecedor cadastrado.", parent=self)
                return
            if self.produto_id:
                if d["qtd"] < 0:
                    messagebox.showwarning("Atenção", "Quantidade deve ser zero ou positiva.", parent=self)
                    return
            else:
                if d["qtd"] <= 0:
                    messagebox.showwarning("Atenção", "Quantidade deve ser maior que zero para cadastrar um novo produto.", parent=self)
                    return

            # Gerar SKU se necessário
            if not d["sku"]:
                d["sku"] = self._gerar_sku_novo(d["produto"], d["cor"])

            if self.produto_id:
                # Lógica de atualização
                with database.conectar() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT sku, produto, cor, tamanho, precocusto, precovenda, categoria, material, fornecedor, status_item, quantidade FROM produtos WHERE id = ?", (self.produto_id,))
                    atual = cursor.fetchone()

                if not atual:
                    messagebox.showerror("Erro", "Produto não encontrado para atualização.", parent=self)
                    return

                # Verificar se descrição do modelo é igual
                descricao_igual = atual[1].lower() == d["produto"].lower()
                
                if descricao_igual:
                    # Mesmo modelo - verificar se atributos são iguais
                    atributos_iguais = (
                        atual[2] == d["cor"] and str(atual[3]) == str(d["tam"]) and
                        atual[6] == d["cat"] and atual[7] == d["mat"] and atual[8] == d["forn"]
                    )
                    
                    if atributos_iguais:
                        # Atributos iguais - verificar se preço, status ou quantidade mudaram
                        preco_mudou = float(atual[4]) != float(d["custo"]) or float(atual[5]) != float(d["venda"])
                        status_mudou = atual[9] != d["status"]
                        qtd_add = d["qtd"]
                        
                        if not preco_mudou and not status_mudou and qtd_add == 0:
                            messagebox.showinfo("Info", "Nenhuma alteração detectada.", parent=self)
                        else:
                            nova_qtde = atual[10] + qtd_add
                            database.atualizar_produto(
                                self.produto_id, 
                                precocusto=d["custo"], 
                                precovenda=d["venda"],
                                quantidade=nova_qtde, 
                                status_item=d["status"],
                                fornecedor=d["forn"],
                                fornecedor_id=d["forn_id"]
                            )
                            
                            if (preco_mudou or qtd_add > 0) and d["qtd"] > 0:
                                valor_despesa = float(d["custo"]) * qtd_add
                                database.lancar_despesa(
                                    f"Compra de {d['produto']} - Reposição de Estoque", 
                                    valor_despesa, 
                                    "Compra Mercadoria", 
                                    self.ent_data_lancamento.get(),
                                    1
                                )
                            
                            messagebox.showinfo("Sucesso", "Atualização realizada com sucesso.", parent=self)
                    else:
                        # Atributos diferentes - gerar novo SKU
                        novo_sku = self._gerar_sku_variacao(d["sku"])
                        criado = database.cadastrar_produto(
                            novo_sku, 'Calçados', d["produto"], d["cor"], d["tam"],
                            d["custo"], d["venda"], d["qtd"], d["cat"], d["mat"], d["forn"],
                            getattr(self, 'caminho_foto', ''), fornecedor_id=d["forn_id"]
                        )
                        if not criado:
                            messagebox.showerror("Erro", "Falha ao cadastrar nova variação do produto.", parent=self)
                            return
                        
                        # Lançar despesa para nova variação
                        valor_despesa = float(d["custo"]) * d["qtd"]
                        database.lancar_despesa(
                            f"Compra de {d['produto']} - Nova Variação", 
                            valor_despesa, 
                            "Compra Mercadoria", 
                            self.ent_data_lancamento.get(),
                            1
                        )
                        
                        messagebox.showinfo("Sucesso", "Nova variação cadastrada com sucesso.", parent=self)
                else:
                    # Descrição diferente - sempre novo SKU
                    novo_sku = self._gerar_sku_novo(d["produto"], d["cor"])
                    criado = database.cadastrar_produto(
                        novo_sku, 'Calçados', d["produto"], d["cor"], d["tam"],
                        d["custo"], d["venda"], d["qtd"], d["cat"], d["mat"], d["forn"],
                        getattr(self, 'caminho_foto', ''), fornecedor_id=d["forn_id"]
                    )
                    if not criado:
                        messagebox.showerror("Erro", "Falha ao cadastrar novo produto.", parent=self)
                        return
                    
                    # Lançar despesa
                    valor_despesa = float(d["custo"]) * d["qtd"]
                    database.lancar_despesa(
                        f"Compra de {d['produto']} - Novo Produto", 
                        valor_despesa, 
                        "Compra Mercadoria", 
                        self.ent_data_lancamento.get(),
                        1
                    )
                    
                    messagebox.showinfo("Sucesso", "Novo produto cadastrado com sucesso.", parent=self)
            else:
                # Novo produto
                criado = database.cadastrar_produto(
                    d["sku"], 'Calçados', d["produto"], d["cor"], d["tam"], 
                    d["custo"], d["venda"], d["qtd"], d["cat"], d["mat"], d["forn"],
                    getattr(self, 'caminho_foto', ''), fornecedor_id=d["forn_id"]
                )
                if not criado:
                    messagebox.showerror("Erro", "Falha ao cadastrar produto.", parent=self)
                    return
                
                # Lançar despesa
                valor_despesa = float(d["custo"]) * d["qtd"]
                database.lancar_despesa(
                    f"Compra de {d['produto']} - Novo Produto", 
                    valor_despesa, 
                    "Compra Mercadoria", 
                    self.ent_data_lancamento.get(),
                    1
                )
                
                messagebox.showinfo("Sucesso", "Produto cadastrado com sucesso.", parent=self)

            if hasattr(self.master, "exibir_produtos"):
                self.master.exibir_produtos()
            if hasattr(self.master, "exibir_financeiro"):
                self.master.exibir_financeiro()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar: {e}", parent=self)

    def preencher_dados(self, d):
        self.produto_id = d[0]
        self.ent_sku.config(state="normal")
        self.ent_sku.delete(0, tk.END); self.ent_sku.insert(0, d[1] if d[1] else "")
        self.ent_sku.config(state="readonly")
        self.ent_produto.delete(0, tk.END); self.ent_produto.insert(0, d[3])
        self.cb_cor.set(d[4]); self.cb_tam.set(str(d[5]))
        self.ent_custo.delete(0, tk.END); self.ent_custo.insert(0, f"{d[6]:.2f}")
        self.ent_venda.delete(0, tk.END); self.ent_venda.insert(0, f"{d[7]:.2f}")
        quantidade_atual = d[8]
        self.ent_qtd.delete(0, tk.END)
        self.ent_qtd.insert(0, "0")
        self.lbl_qtd_atual.config(text=f"Quantidade atual em estoque: {quantidade_atual}")
        self.cb_cat.set(d[9]); self.cb_mat.set(d[10])
        self.fornecedor_id = d[15] if len(d) > 15 else None
        self.ent_forn.config(state="normal")
        self.ent_forn.delete(0, tk.END)
        self.ent_forn.insert(0, d[11] if d[11] else "")
        self.ent_forn.config(state="readonly")
        self.var_status.set(d[12])
        self.caminho_foto = d[13] if len(d) > 13 else ""
        if self.caminho_foto:
            self.exibir_foto_preview()
        self.btn_salvar.config(text="ATUALIZAR PRODUTO", bg=self.cor_hover_field)

    def exibir_foto_preview(self):
        """Carrega e exibe a foto do produto no Label"""
        if not self.caminho_foto or not os.path.exists(self.caminho_foto):
            self.lbl_foto.config(text="📷\n\nClique para\nadicionar foto", image="", compound="top")
            return
        try:
            img = Image.open(self.caminho_foto)
            img = img.resize((150, 150), Image.Resampling.LANCZOS)
            self.foto_tk = tk.PhotoImage(img)
            self.lbl_foto.config(image=self.foto_tk, text="", compound="center")
        except Exception as e:
            self.lbl_foto.config(text=f"Erro ao carregar\nfoto: {str(e)[:20]}", image="")

    def menu_contexto_foto(self, event):
        """Menu de contexto para a foto"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Nova foto", command=self.selecionar_foto)
        menu.add_command(label="Excluir foto", command=self.excluir_foto)
        menu.add_separator()
        menu.add_command(label="Sair", command=lambda: None)
        menu.post(event.x_root, event.y_root)

    def excluir_foto(self):
        """Remove a foto do produto"""
        if messagebox.askyesno("Confirmar", "Deseja realmente excluir a foto?", parent=self):
            self.caminho_foto = ""
            self.lbl_foto.config(text="📷\n\nClique para\nadicionar foto", image="")

    def gerar_sku_automatico(self):
        """Gera SKU automaticamente baseado nos dados do produto"""
        produto = self.ent_produto.get().strip()
        cor = self.cb_cor.get()
        
        if produto and cor:
            sku = self._gerar_sku_novo(produto, cor)
            self.ent_sku.config(state="normal")
            self.ent_sku.delete(0, tk.END)
            self.ent_sku.insert(0, sku)
            self.ent_sku.config(state="readonly")

    def _gerar_sku_novo(self, produto, cor):
        """Gera novo SKU baseado na descrição e cor"""
        # Três primeiras letras de cada palavra da descrição
        palavras = produto.split()
        parte_produto = ''.join(palavra[:3].upper() for palavra in palavras)
        
        # Três primeiras letras da cor
        parte_cor = cor[:3].upper()
        
        # Gerar sequência numérica única
        sequencia = self._gerar_sequencia_numerica()
        
        return f"{parte_produto}{sequencia}{parte_cor}"

    def _gerar_sequencia_numerica(self):
        """Gera uma sequência de 4 números únicos"""
        with database.conectar() as conn:
            cursor = conn.cursor()
            # Encontrar o maior número usado em SKUs existentes
            cursor.execute("SELECT sku FROM produtos")
            skus_existentes = cursor.fetchall()
            
            max_num = 0
            for sku_row in skus_existentes:
                sku = sku_row[0]
                # Verificar se o SKU segue o padrão novo (letras + 4 números + letras)
                if len(sku) >= 7 and sku[:-7].isalpha() and sku[-3:].isalpha() and sku[-7:-3].isdigit():
                    parte_numerica = sku[-7:-3]
                    if parte_numerica.isdigit():
                        max_num = max(max_num, int(parte_numerica))
            
            return f"{max_num + 1:04d}"

    def _gerar_sku_variacao(self, sku_base):
        """Gera um novo SKU único quando atributos mudam mas o produto é o mesmo."""
        # Para variações, manter a base do produto e cor, mas incrementar a sequência
        if len(sku_base) >= 7:
            parte_produto = sku_base[:-7]  # tudo menos os últimos 7 caracteres
            parte_cor = sku_base[-3:]      # últimos 3 caracteres (cor)
            parte_numerica = sku_base[-7:-3]  # 4 dígitos do meio
            
            if parte_numerica.isdigit():
                novo_num = int(parte_numerica) + 1
                novo_sku = f"{parte_produto}{novo_num:04d}{parte_cor}"
                
                # Verificar se já existe
                with database.conectar() as conn:
                    cursor = conn.cursor()
                    while cursor.execute("SELECT 1 FROM produtos WHERE sku = ?", (novo_sku,)).fetchone():
                        novo_num += 1
                        novo_sku = f"{parte_produto}{novo_num:04d}{parte_cor}"
                
                return novo_sku
        
        # Fallback: gerar completamente novo
        produto = self.ent_produto.get().strip()
        cor = self.cb_cor.get()
        return self._gerar_sku_novo(produto, cor)

    def selecionar_foto(self, event):
        """Selecionar foto da galeria e copiar para pasta images"""
        # Abrir diálogo para selecionar arquivo
        caminho_origem = filedialog.askopenfilename(
            parent=self,
            title="Selecionar Foto do Produto",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.gif *.bmp"), ("Todos os arquivos", "*.*")]
        )
        
        if caminho_origem:
            try:
                # Criar pasta images se não existir
                os.makedirs("images", exist_ok=True)
                
                # Gerar nome único para a foto
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nome_arquivo = f"produto_{timestamp}.jpg"
                caminho_destino = os.path.join("images", nome_arquivo)
                
                # Copiar arquivo para pasta images
                import shutil
                shutil.copy2(caminho_origem, caminho_destino)
                
                # Atualizar campo foto (se existir)
                if hasattr(self, 'caminho_foto'):
                    self.caminho_foto = caminho_destino
                
                # Atualizar label para mostrar preview
                self.lbl_foto.config(text=f"📷\n\nFoto selecionada:\n{nome_arquivo}", fg=self.cor_destaque)
                
                messagebox.showinfo("Sucesso", f"Foto '{nome_arquivo}' adicionada com sucesso!", parent=self)
                
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao copiar foto: {str(e)}", parent=self)

    def editar_produto_duplo_clique(self, event):
        """Editar produto com duplo clique"""
        selecao = self.tree_busca.selection()
        if not selecao: return
        id_prod = self.tree_busca.item(selecao[0])["values"][0]
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM produtos WHERE id = ?", (id_prod,))
            dados = cursor.fetchone()
            if dados:
                self.preencher_dados(dados)

    def menu_contexto_produto(self, event):
        """Mostrar menu de contexto no botão direito"""
        try:
            item = self.tree_busca.identify_row(event.y)
            if item:
                self.tree_busca.selection_set(item)
                self.menu_contexto.post(event.x_root, event.y_root)
        except:
            pass

    def editar_produto_menu(self):
        """Editar produto via menu de contexto"""
        if messagebox.askyesno("Confirmar", "Deseja editar este produto?", parent=self):
            self.editar_produto_duplo_clique(None)

    def visualizar_produto_menu(self):
        """Visualizar produto via menu de contexto"""
        selecao = self.tree_busca.selection()
        if not selecao: return
        id_prod = self.tree_busca.item(selecao[0])["values"][0]
        
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM produtos WHERE id = ?", (id_prod,))
            dados = cursor.fetchone()
        
        if dados:
            VisualizarProduto(self, dados)

    def _manter_em_primeiro_plano(self):
        try:
            self.attributes("-topmost", True)
        except Exception as e:
            messagebox.showwarning("Aviso", f"Não foi possível manter esta janela em primeiro plano: {e}", parent=self)

    def indisponibilizar_produto_menu(self):
        """Indisponibilizar produto via menu de contexto"""
        selecao = self.tree_busca.selection()
        if not selecao: return
        id_prod = self.tree_busca.item(selecao)["values"][0]
        
        if messagebox.askyesno("Confirmar", "Deseja indisponibilizar este item?", parent=self):
            try:
                database.atualizar_produto(id_prod, status_item="Indisponível")
                messagebox.showinfo("Sucesso", "Item indisponibilizado!", parent=self)
                self.atualizar_tree_busca()
                if hasattr(self.master, "exibir_produtos"):
                    self.master.exibir_produtos()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao indisponibilizar item: {str(e)}", parent=self)

    def disponibilizar_produto_menu(self):
        """Disponibilizar produto via menu de contexto"""
        selecao = self.tree_busca.selection()
        if not selecao: return
        id_prod = self.tree_busca.item(selecao)["values"][0]
        
        if messagebox.askyesno("Confirmar", "Deseja disponbilizar este item?", parent=self):
            try:
                database.atualizar_produto(id_prod, status_item="Disponível")
                messagebox.showinfo("Sucesso", "Item disponbilizado!", parent=self)
                self.atualizar_tree_busca()
                if hasattr(self.master, "exibir_produtos"):
                    self.master.exibir_produtos()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao disponbilizar item: {str(e)}", parent=self)

    def promocional_produto_menu(self):
        """Marcar produto como promocional via menu de contexto"""
        selecao = self.tree_busca.selection()
        if not selecao: return
        id_prod = self.tree_busca.item(selecao)["values"][0]
        
        if messagebox.askyesno("Confirmar", "Deseja marcar este item como promocional?", parent=self):
            try:
                database.atualizar_produto(id_prod, status_item="Promocional")
                messagebox.showinfo("Sucesso", "Item marcado como promocional!", parent=self)
                self.atualizar_tree_busca()
                if hasattr(self.master, "exibir_produtos"):
                    self.master.exibir_produtos()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao marcar item como promocional: {str(e)}", parent=self)


class VisualizarProduto(tk.Toplevel):
    """Classe para visualizar detalhes do produto"""
    def __init__(self, master, dados_produto):
        super().__init__(master)
        
        # --- Paleta de cores ---
        paleta = ui_utils.get_paleta()
        self.bg_fundo = paleta["bg_fundo"]
        self.bg_card = paleta["bg_card"]
        self.cor_texto = paleta["cor_texto"]
        self.cor_destaque = paleta["cor_destaque"]
        
        self.title("Detalhes do Produto")
        self.configure(bg=self.bg_fundo)
        ui_utils.calcular_dimensoes_janela(self, largura_desejada=560, altura_desejada=620)
        
        # Criar interface
        main_frame = tk.Frame(self, bg=self.bg_fundo, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        tk.Label(main_frame, text="📦 DETALHES DO PRODUTO", bg=self.bg_fundo, 
                 fg=self.cor_destaque, font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        
        # Informações do produto
        info_text = f"""
SKU: {dados_produto[1] or 'N/A'}
Produto: {dados_produto[2]}
Cor: {dados_produto[3]}
Tamanho: {dados_produto[4]}
Preço de Custo: R$ {dados_produto[5]:.2f}
Preço de Venda: R$ {dados_produto[6]:.2f}
Quantidade em Estoque: {dados_produto[7]}
Categoria: {dados_produto[8] or 'N/A'}
Material: {dados_produto[9] or 'N/A'}
Fornecedor: {dados_produto[10] or 'N/A'}
Status: {dados_produto[11]}
Última Atualização: {dados_produto[12] if len(dados_produto) > 12 else 'N/A'}
        """
        
        lbl_info = tk.Label(main_frame, text=info_text.strip(), bg=self.bg_card, fg=self.cor_texto,
                           font=("Courier New", 10), justify="left", relief="solid", borderwidth=1)
        lbl_info.pack(fill="both", expand=True, pady=(0, 20))
        
        # Botão fechar
        tk.Button(main_frame, text="FECHAR", bg=self.cor_destaque, fg="white",
                 font=("Segoe UI", 10, "bold"), command=self.destroy).pack()
        
        self.grab_set()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw() # Esconde a janela principal para abrir apenas o Toplevel
    JanelaCadastroProdutos(root)
    root.mainloop()