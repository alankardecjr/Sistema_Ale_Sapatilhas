"""
cadastro_vendas.py — PDV / checkout (cliente, estoque, carrinho).

O pagamento é realizado em Gerenciar Receitas após finalizar a venda.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

import config
import database
import ui_utils


class JanelaCadastroVendas(tk.Toplevel):
    """PDV: coluna de produtos + coluna cliente/carrinho; pagamento em receitas."""

    FORMAS_PAGAMENTO = list(config.FORMAS_PAGAMENTO)
    CORES_FILTRO = ["", "Amarelo", "Azul", "Branco", "Caramelo", "Massala", "Nude", "Off", "Preto", "Rosa", "Verde", "Vermelho"]
    TAMANHOS_FILTRO = [""] + [str(i) for i in range(33, 41)] + ["G", "GG", "M", "P", "U"]
    PLACEHOLDER_BUSCA_CLI = "🔍 Digite nome do cliente para buscar..."

    def __init__(self, master, cliente_selecionado=None, dados_venda=None, on_cliente_atualizado=None):
        super().__init__(master)
        self.master = master
        self.title("Alê Sapatilhas - Checkout de Vendas (PDV)")
        self.transient(master)
        self.grab_set()
        self.focus_set()

        ui_utils.calcular_dimensoes_janela(self, maximizar=True)

        paleta = ui_utils.get_paleta()
        self.bg_fundo = paleta["bg_fundo"]
        self.bg_card = paleta["bg_card"]
        self.cor_borda = paleta["cor_borda"]
        self.cor_texto = paleta["cor_texto"]
        self.cor_destaque = paleta["cor_destaque"]
        self.cor_btn_menu = paleta["cor_btn_menu"]
        self.cor_btn_sair = paleta["cor_btn_sair"]
        self.cor_hover_btn = paleta["cor_hover_btn"]
        self.configure(bg=self.bg_fundo)

        self.cliente_atual = None
        self.carrinho_itens = {}
        self.venda_id = dados_venda.get("id") if dados_venda else None
        self._imgs_tree = {}
        self._estoque_cache = []
        self._popup_resultados = None
        self.on_cliente_atualizado = on_cliente_atualizado
        self.configurar_estilos()
        self.setup_layout()
        self._rastreador = ui_utils.RastreadorAlteracoes(self._snapshot_pdv)

        if cliente_selecionado:
            cid = cliente_selecionado[0] if isinstance(cliente_selecionado, (tuple, list)) else cliente_selecionado
            self.carregar_dados_cliente_completo(cid)
            if isinstance(cliente_selecionado, (tuple, list)) and len(cliente_selecionado) > 1:
                self._definir_busca_cliente(cliente_selecionado[1])
            if self.venda_id:
                v = database.obter_venda_por_id(self.venda_id)
                if v:
                    self._carregar_itens_venda()
                    self.ent_desconto.delete(0, tk.END)
                    self.ent_desconto.insert(0, f"{float(v[6] or 0):.2f}")
                    self.atualizar_view_carrinho()
                    if v[11] == config.STATUS_VENDA_CANCELADA:
                        self.lbl_modo.config(text="VENDA CANCELADA (somente consulta)")
                        self.btn_finalizar.config(state="disabled")
        elif self.venda_id:
            v = database.obter_venda_por_id(self.venda_id)
            if v:
                self.carregar_dados_cliente_completo(v[1])
                self._definir_busca_cliente(v[2])
                self._carregar_itens_venda()
                self.ent_desconto.delete(0, tk.END)
                self.ent_desconto.insert(0, f"{float(v[6] or 0):.2f}")
                self.atualizar_view_carrinho()
                if v[11] == config.STATUS_VENDA_CANCELADA:
                    self.lbl_modo.config(text="VENDA CANCELADA (somente consulta)")
                    self.btn_finalizar.config(state="disabled")

        self.listar_estoque_completo()
        self._atualizar_estado_botao_finalizar()
        self.protocol("WM_DELETE_WINDOW", self._fechar_pdv)

    def _snapshot_pdv(self):
        return (
            self.cliente_atual[0] if self.cliente_atual else None,
            tuple(sorted(self.carrinho_itens.items())),
            self.ent_busca_cli.get(),
            self.ent_desconto.get() if hasattr(self, "ent_desconto") else "0",
        )

    def configurar_estilos(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("PDV.Treeview", background=self.bg_card, foreground=self.cor_texto,
                             rowheight=28, font=("Segoe UI", 9))
        self.style.configure("PDV.Treeview.Heading", font=("Segoe UI", 9, "bold"), background=self.bg_card)
        self.style.map("PDV.Treeview", background=[("selected", self.cor_destaque)])
        self.style.configure("PDV.Cliente.Treeview", rowheight=22, font=("Segoe UI", 9))

    def setup_layout(self):
        self.sidebar = tk.Frame(self, bg=self.cor_btn_sair, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="ALÊ\nSAPATILHAS", font=("Segoe UI", 20, "bold"),
                 bg=self.cor_btn_sair, fg="white", pady=20).pack()

        btn_estilo = {
            "font": ("Segoe UI", 9, "bold"), "bg": self.cor_btn_menu, "fg": "white",
            "relief": "flat", "cursor": "hand2", "anchor": "w", "padx": 15, "pady": 8,
        }
        titulo_acao = "💾 SALVAR ALTERAÇÕES" if self.venda_id else "💰 FINALIZAR VENDA"

        botoes = [
            (titulo_acao, self.finalizar_venda),
            ("❌ REMOVER ITEM", self.remover_do_carrinho),
            ("↩ ESTORNAR VENDA", self.estornar_venda) if self.venda_id else None,
            ("✏️ EDITAR CLIENTE", self.editar_cliente_pdv),
            ("👤 NOVO CLIENTE", self.abrir_novo_cliente),
            ("📦 NOVO PRODUTO", self.abrir_cadastro_produto),
            ("➕ FERRAMENTAS", self.abrir_menu_ferramentas),
            ("🔄 LIMPAR DADOS", self.limpar_formulario),
            ("🔄 ATUALIZAR", self.listar_estoque_completo),
            ("🚪 SAIR PDV", self._fechar_pdv),
        ]

        for item in botoes:
            if not item:
                continue
            text_aux, cmd_aux = item
            btn = tk.Button(self.sidebar, text=text_aux, command=cmd_aux, **btn_estilo)
            btn.pack(fill="x", pady=3, padx=5)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.cor_hover_btn))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.cor_btn_menu))
            if "FINALIZAR" in text_aux or "SALVAR" in text_aux:
                self.btn_finalizar = btn
                self.btn_finalizar.config(state="disabled")

        self.main_container = tk.Frame(self, bg=self.bg_fundo)
        self.main_container.pack(side="right", fill="both", expand=True, padx=16, pady=10)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.lbl_modo = tk.Label(
            self.main_container,
            text="EDIÇÃO DE VENDA" if self.venda_id else "NOVA VENDA (PDV)",
            font=("Segoe UI", 12, "bold"), bg=self.bg_fundo, fg=self.cor_destaque,
        )
        self.lbl_modo.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.colunas_frame = tk.Frame(self.main_container, bg=self.bg_fundo)
        self.colunas_frame.grid(row=1, column=0, sticky="nsew")
        self.colunas_frame.grid_rowconfigure(0, weight=1)
        self.colunas_frame.grid_columnconfigure(0, weight=0, minsize=420)
        self.colunas_frame.grid_columnconfigure(1, weight=1)

        self.setup_sessao_produtos(self.colunas_frame)
        self.setup_coluna_cliente_carrinho(self.colunas_frame)

    def setup_sessao_produtos(self, parent):
        f_prod = tk.LabelFrame(parent, text=" 👠 LISTA DE PRODUTOS ", bg=self.bg_fundo,
                               fg=self.cor_texto, font=("Segoe UI", 10, "bold"), relief="solid", borderwidth=1)
        f_prod.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        barra_busca = tk.Frame(f_prod, bg=self.bg_fundo)
        barra_busca.pack(fill="x", padx=5, pady=5)

        self.ent_busca_prod = tk.Entry(barra_busca, font=("Segoe UI", 11), highlightthickness=1)
        self.ent_busca_prod.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._placeholder_prod = "Pesquisar produto..."
        self.ent_busca_prod.insert(0, self._placeholder_prod)
        self.ent_busca_prod.bind("<FocusIn>", lambda e: self._clear_placeholder())
        self.ent_busca_prod.bind("<FocusOut>", lambda e: self._add_placeholder())
        self.ent_busca_prod.bind("<KeyRelease>", lambda e: self.filtrar_produtos())

        tk.Label(barra_busca, text="Cor", bg=self.bg_fundo, font=("Segoe UI", 8, "bold")).pack(side="left")
        self.cb_filtro_cor = ttk.Combobox(barra_busca, values=self.CORES_FILTRO, width=10, state="readonly", font=("Segoe UI", 9))
        self.cb_filtro_cor.set("")
        self.cb_filtro_cor.pack(side="left", padx=4)
        self.cb_filtro_cor.bind("<<ComboboxSelected>>", lambda e: self.filtrar_produtos())

        tk.Label(barra_busca, text="Tam.", bg=self.bg_fundo, font=("Segoe UI", 8, "bold")).pack(side="left")
        self.cb_filtro_tam = ttk.Combobox(barra_busca, values=self.TAMANHOS_FILTRO, width=6, state="readonly", font=("Segoe UI", 9))
        self.cb_filtro_tam.set("")
        self.cb_filtro_tam.pack(side="left", padx=4)
        self.cb_filtro_tam.bind("<<ComboboxSelected>>", lambda e: self.filtrar_produtos())

        cols = ("prod", "cor", "tam", "preco", "qtd")
        self.tree_estoque = ttk.Treeview(f_prod, columns=cols, show="tree headings", style="PDV.Treeview")
        self.tree_estoque.heading("#0", text="FOTO")
        self.tree_estoque.column("#0", width=52, anchor="center")
        for col in cols:
            self.tree_estoque.heading(col, text=col.upper())
            self.tree_estoque.column(col, width=72, anchor="center")
        self.tree_estoque.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree_estoque.bind("<Double-1>", self.adicionar_ao_carrinho)

    def setup_coluna_cliente_carrinho(self, parent):
        col_dir = tk.Frame(parent, bg=self.bg_fundo)
        col_dir.grid(row=0, column=1, sticky="nsew")
        col_dir.grid_rowconfigure(2, weight=1)
        col_dir.grid_columnconfigure(0, weight=1)

        f_busca_wrap = tk.Frame(col_dir, bg=self.bg_fundo)
        f_busca_wrap.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        f_busca_wrap.columnconfigure(0, weight=1)

        tk.Label(f_busca_wrap, text="CLIENTE", font=("Segoe UI", 8, "bold"), bg=self.bg_fundo).grid(row=0, column=0, sticky="w")
        self.ent_busca_cli = tk.Entry(
            f_busca_wrap, font=("Segoe UI", 11), highlightthickness=1,
            highlightbackground=self.cor_borda,
        )
        self.ent_busca_cli.grid(row=1, column=0, sticky="ew", ipady=5)
        self.ent_busca_cli.insert(0, self.PLACEHOLDER_BUSCA_CLI)
        self.ent_busca_cli.config(fg="gray")
        self.ent_busca_cli.bind("<FocusIn>", self._cli_focus_in)
        self.ent_busca_cli.bind("<FocusOut>", self._cli_focus_out)
        self.ent_busca_cli.bind("<KeyRelease>", self._on_busca_cliente_key)

        # Painel minimalista com borda para os dados do cliente
        self.frame_dados_cliente = tk.LabelFrame(
            col_dir, text=" Dados do cliente ", bg=self.bg_card, fg=self.cor_texto,
            font=("Segoe UI", 9, "bold"), relief="solid", borderwidth=1,
        )
        self.frame_dados_cliente.grid(row=1, column=0, sticky="ew", pady=4)
        
        # Componente de texto plano para exibição minimalista e linear das informações
        self.txt_cli_detalhes = tk.Text(
            self.frame_dados_cliente, bg=self.bg_card, fg=self.cor_texto,
            font=("Segoe UI", 9), relief="flat", height=4, width=40,
            wrap="word", state="disabled", cursor="arrow"
        )
        self.txt_cli_detalhes.pack(fill="both", expand=True, padx=8, pady=6)

        f_cart = tk.LabelFrame(
            col_dir, text=" 🛒 CARRINHO ", bg=self.bg_card, fg=self.cor_destaque,
            font=("Segoe UI", 10, "bold"), relief="solid", borderwidth=1,
        )
        
        f_cart.grid(row=2, column=0, sticky="nsew")
        f_cart.grid_rowconfigure(0, weight=1)
        f_cart.grid_columnconfigure(0, weight=1)

        cols = ("prod", "tam", "qtd", "sub")
        self.tree_cart = ttk.Treeview(f_cart, columns=cols, show="tree headings", style="PDV.Treeview")
        self.tree_cart.heading("#0", text="FOTO")
        self.tree_cart.column("#0", width=48, anchor="center")
        for col in cols:
            self.tree_cart.heading(col, text=col.upper())
            self.tree_cart.column(col, width=80, anchor="center")
        self.tree_cart.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        rodape_cart = tk.Frame(f_cart, bg=self.bg_card)
        rodape_cart.grid(row=1, column=0, sticky="ew", padx=8, pady=6)
        rodape_cart.columnconfigure(2, weight=1)

        tk.Label(rodape_cart, text="Desconto (R$)", font=("Segoe UI", 9, "bold"),
                 bg=self.bg_card, fg=self.cor_texto).grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.ent_desconto = tk.Entry(rodape_cart, font=("Segoe UI", 10), width=10,
                                     highlightthickness=1, highlightbackground=self.cor_borda)
        self.ent_desconto.insert(0, "0.00")
        self.ent_desconto.grid(row=0, column=1, sticky="w", padx=(0, 12), ipady=3)
        self.ent_desconto.bind("<KeyRelease>", lambda e: self.atualizar_view_carrinho())

        self.lbl_subtotal = tk.Label(
            rodape_cart, text="Subtotal: R$ 0,00", font=("Segoe UI", 9),
            bg=self.bg_card, fg=self.cor_texto, anchor="e",
        )
        self.lbl_subtotal.grid(row=0, column=2, sticky="e")

        self.lbl_total = tk.Label(
            rodape_cart, text="TOTAL: R$ 0,00", font=("Segoe UI", 16, "bold"),
            bg=self.bg_card, fg=self.cor_destaque, anchor="e",
        )
        self.lbl_total.grid(row=1, column=0, columnspan=3, sticky="e", pady=(4, 0))

    def _cli_focus_in(self, event):
        if self.ent_busca_cli.get() == self.PLACEHOLDER_BUSCA_CLI:
            self.ent_busca_cli.delete(0, tk.END)
            self.ent_busca_cli.config(fg=self.cor_texto)

    def _cli_focus_out(self, event):
        if not self.ent_busca_cli.get().strip():
            self.ent_busca_cli.insert(0, self.PLACEHOLDER_BUSCA_CLI)
            self.ent_busca_cli.config(fg="gray")
        if self._popup_resultados and self._popup_resultados.winfo_exists():
            self.after(120, self._fechar_popup_clientes)

    def _definir_busca_cliente(self, texto):
        self.ent_busca_cli.delete(0, tk.END)
        self.ent_busca_cli.insert(0, texto)
        self.ent_busca_cli.config(fg=self.cor_texto)

    def _on_busca_cliente_key(self, event=None):
        termo = self.ent_busca_cli.get().strip()
        if termo == self.PLACEHOLDER_BUSCA_CLI:
            termo = ""
        self._fechar_popup_clientes()
        if len(termo) < 2:
            return
        resultados = []
        with database.conectar() as conn:
            rows = conn.execute(
                """SELECT id, nome, cpf, telefone FROM clientes
                   WHERE tipo = ? AND (nome LIKE ? OR cpf LIKE ? OR telefone LIKE ?)
                   ORDER BY nome ASC LIMIT 5""",
                (config.TIPO_CLIENTE, f"%{termo}%", f"%{termo}%", f"%{termo}%"),
            ).fetchall()
            resultados = rows
        if resultados:
            self._mostrar_popup_clientes(resultados)

    def _mostrar_popup_clientes(self, resultados):
        self._fechar_popup_clientes()
        self.update_idletasks()
        x = self.ent_busca_cli.winfo_rootx()
        y = self.ent_busca_cli.winfo_rooty() + self.ent_busca_cli.winfo_height()

        pop = tk.Toplevel(self)
        pop.wm_overrideredirect(True)
        pop.configure(bg=self.bg_card, highlightthickness=1, highlightbackground=self.cor_borda)
        pop.geometry(f"+{x}+{y}")

        tree = ttk.Treeview(pop, columns=("nome", "cpf", "tel"), show="headings", height=min(5, len(resultados)))
        for col, txt, w in (("nome", "NOME", 160), ("cpf", "CPF", 110), ("tel", "TELEFONE", 100)):
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor="w")
        for row in resultados:
            tree.insert("", "end", iid=row[0], values=(row[1], row[2] or "—", row[3] or "—"))
        tree.pack(fill="both", expand=True)

        def selecionar(event=None):
            iid = None
            if hasattr(event, 'y'):
                iid = tree.identify_row(event.y)
            if not iid and tree.selection():
                iid = tree.selection()[0]
            if not iid:
                return
            tree.selection_set(iid)
            vals = tree.item(iid, "values")
            self._definir_busca_cliente(vals[0])
            self.carregar_dados_cliente_completo(iid)
            self._fechar_popup_clientes()

        tree.bind("<Double-1>", selecionar)
        tree.bind("<Return>", selecionar)
        tree.bind("<ButtonRelease-1>", lambda e: self.after(10, selecionar, e))
        self._popup_resultados = pop

    def _fechar_popup_clientes(self):
        if self._popup_resultados and self._popup_resultados.winfo_exists():
            self._popup_resultados.destroy()
        self._popup_resultados = None

    def _preencher_tree_cliente(self, c):
        texto = (
            f"Nome: {c[2]} | CPF: {c[3] or '—'} | Fone: {c[4] or '—'}\n"
            f"Logradouro: {c[8] or '—'} | Bairro: {c[9] or '—'} | CEP: {c[11] or '—'}\n"
            f"Cidade: {c[10] or '—'}\n"
            f"Observação: {c[12] or '—'}"
        )
        self.txt_cli_detalhes.config(state="normal")
        self.txt_cli_detalhes.delete("1.0", tk.END)
        self.txt_cli_detalhes.insert(tk.END, texto)
        self.txt_cli_detalhes.config(state="disabled")

    def abrir_menu_ferramentas(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Calculadora", command=lambda: ui_utils.abrir_calculadora(self))
        menu.add_command(label="Calendário", command=lambda: ui_utils.abrir_calendario_info(self))
        menu.add_command(label="Anotações", command=lambda: ui_utils.abrir_anotacoes(self))
        menu.add_command(label="Configurações", command=lambda: ui_utils.abrir_configuracoes(self))
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        except tk.TclError:
            pass

    def editar_cliente_pdv(self):
        if not self.cliente_atual:
            messagebox.showwarning("Cliente", "Selecione um cliente antes de editar.", parent=self)
            return
        from cadastro_clientes import JanelaCadastroClientes
        JanelaCadastroClientes(
            self,
            dados_cliente=self.cliente_atual,
            on_salvo=lambda cid: self._apos_editar_cliente(cid),
        )

    def _apos_editar_cliente(self, cliente_id):
        self.carregar_dados_cliente_completo(cliente_id)
        if self.on_cliente_atualizado:
            self.on_cliente_atualizado()

    def _fechar_pdv(self):
        if ui_utils.confirmar_fechar_formulario(self, self._rastreador, "Sair do PDV"):
            self.destroy()

    def _clear_placeholder(self):
        if self.ent_busca_prod.get() == self._placeholder_prod:
            self.ent_busca_prod.delete(0, tk.END)

    def _add_placeholder(self):
        if not self.ent_busca_prod.get():
            self.ent_busca_prod.insert(0, self._placeholder_prod)

    def _desconto_valor(self):
        try:
            return max(float(self.ent_desconto.get().replace(",", ".")), 0)
        except (ValueError, AttributeError):
            return 0.0

    def _total_bruto(self):
        return sum(d["sub"] for d in self.carrinho_itens.values())

    def _total_liquido(self):
        return max(self._total_bruto() - self._desconto_valor(), 0)

    def _atualizar_estado_botao_finalizar(self):
        ok = self.cliente_atual is not None and bool(self.carrinho_itens)
        if hasattr(self, "btn_finalizar"):
            self.btn_finalizar.config(state="normal" if ok else "disabled")

    def _miniatura_produto(self, pid, foto_path):
        if pid in self._imgs_tree:
            return self._imgs_tree[pid]
        img = ui_utils.carregar_miniatura_foto(foto_path, (36, 36))
        if img:
            self._imgs_tree[pid] = img
        return img

    def _inserir_linha_estoque(self, p):
        pid, prod, cor, tam, _custo, preco, qtd, foto = p
        img = self._miniatura_produto(pid, foto if len(p) > 7 else "")
        self.tree_estoque.insert(
            "", "end", iid=pid, image=img or "", text="" if img else "—",
            values=(prod, cor, tam, f"R$ {preco:.2f}", qtd),
        )

    def carregar_dados_cliente_completo(self, cliente_id):
        with database.conectar() as conn:
            c = conn.execute(
                "SELECT * FROM clientes WHERE id = ? AND tipo = ?",
                (cliente_id, config.TIPO_CLIENTE),
            ).fetchone()
        if c:
            self.cliente_atual = c
            self._preencher_tree_cliente(c)
            self._atualizar_estado_botao_finalizar()

    def _carregar_itens_venda(self):
        self.carrinho_itens = {}
        for row in database.obter_itens_venda(self.venda_id):
            pid, prod, _cor, tam, qtd, preco, sub = row
            self.carrinho_itens[str(pid)] = {
                "id": pid, "prod": prod, "tam": tam, "preco": preco, "qtd": qtd, "sub": sub, "foto": "",
            }
        self.atualizar_view_carrinho()

    def _passa_filtros_fixos(self, p):
        cor_f = self.cb_filtro_cor.get().strip()
        tam_f = self.cb_filtro_tam.get().strip()
        if cor_f and p[2] != cor_f:
            return False
        if tam_f and str(p[3]) != tam_f:
            return False
        return True

    def listar_estoque_completo(self):
        self.tree_estoque.delete(*self.tree_estoque.get_children())
        self._estoque_cache = list(database.listar_itens())
        for p in self._estoque_cache:
            if self._passa_filtros_fixos(p):
                self._inserir_linha_estoque(p)

    def filtrar_produtos(self):
        termo = self.ent_busca_prod.get().lower()
        if termo == self._placeholder_prod.lower():
            termo = ""
        self.tree_estoque.delete(*self.tree_estoque.get_children())
        for p in self._estoque_cache:
            if not self._passa_filtros_fixos(p):
                continue
            if termo and termo not in p[1].lower() and termo not in p[2].lower():
                continue
            self._inserir_linha_estoque(p)

    def adicionar_ao_carrinho(self, event):
        sel = self.tree_estoque.selection()
        if not sel:
            return
        id_prod = str(sel[0])
        item = self.tree_estoque.item(id_prod, "values")
        qtd_estoque = int(item[4])
        if qtd_estoque <= 0:
            messagebox.showwarning("Aviso", "Produto esgotado!", parent=self)
            return
        preco = float(item[3].replace("R$ ", "").replace(",", "."))
        foto = ""
        for p in self._estoque_cache:
            if str(p[0]) == id_prod:
                foto = p[7] if len(p) > 7 else ""
                break
        if id_prod in self.carrinho_itens:
            if self.carrinho_itens[id_prod]["qtd"] < qtd_estoque:
                self.carrinho_itens[id_prod]["qtd"] += 1
                self.carrinho_itens[id_prod]["sub"] = self.carrinho_itens[id_prod]["qtd"] * preco
            else:
                messagebox.showwarning("Limite", "Quantidade máxima em estoque atingida.", parent=self)
        else:
            self.carrinho_itens[id_prod] = {
                "id": int(id_prod), "prod": item[0], "tam": item[2],
                "preco": preco, "qtd": 1, "sub": preco, "foto": foto,
            }
        self.atualizar_view_carrinho()

    def remover_do_carrinho(self):
        sel = self.tree_cart.selection()
        if not sel:
            return
        id_prod = str(sel[0])
        if id_prod in self.carrinho_itens:
            if self.carrinho_itens[id_prod]["qtd"] > 1:
                self.carrinho_itens[id_prod]["qtd"] -= 1
                self.carrinho_itens[id_prod]["sub"] = (
                    self.carrinho_itens[id_prod]["qtd"] * self.carrinho_itens[id_prod]["preco"]
                )
            else:
                del self.carrinho_itens[id_prod]
        self.atualizar_view_carrinho()

    def atualizar_view_carrinho(self):
        self.tree_cart.delete(*self.tree_cart.get_children())
        for dados in self.carrinho_itens.values():
            img = self._miniatura_produto(dados["id"], dados.get("foto", ""))
            self.tree_cart.insert(
                "", "end", iid=str(dados["id"]),
                image=img or "", text="" if img else "—",
                values=(dados["prod"], dados["tam"], dados["qtd"], f"R$ {dados['sub']:.2f}"),
            )
        bruto = self._total_bruto()
        total = self._total_liquido()
        desc = self._desconto_valor()
        self.lbl_subtotal.config(text=f"Subtotal: R$ {bruto:.2f}" + (f"  (− R$ {desc:.2f})" if desc else ""))
        self.lbl_total.config(text=f"TOTAL: R$ {total:.2f}")
        self._atualizar_estado_botao_finalizar()

    def _dados_venda_para_api(self):
        lista_final = [{"id": d["id"], "qtd": d["qtd"], "preco": d["preco"]} for d in self.carrinho_itens.values()]
        return lista_final, self._desconto_valor()

    def estornar_venda(self):
        if not self.venda_id:
            return
        if ui_utils.confirmar(self, "Estornar venda", "Cancelar esta venda e devolver itens ao estoque?"):
            ok, msg = database.cancelar_venda(self.venda_id)
            if ok:
                messagebox.showinfo("Sucesso", msg, parent=self)
                if hasattr(self.master, "atualizar_lista"):
                    self.master.atualizar_lista()
                self.destroy()
            else:
                messagebox.showerror("Erro", msg, parent=self)

    def finalizar_venda(self):
        """Registra venda pendente e abre Gerenciar Receitas para pagamento."""
        if not self.cliente_atual or not self.carrinho_itens:
            messagebox.showerror("Erro", "Selecione um cliente e adicione itens ao carrinho.", parent=self)
            return

        lista_final, desconto = self._dados_venda_para_api()
        total = self._total_liquido()

        # Se for edição de uma venda já existente
        if self.venda_id:
            res, msg = database.atualizar_venda_comercial(self.venda_id, self.cliente_atual[0], lista_final, desconto)
            if not res:
                messagebox.showerror("Erro", msg, parent=self)
                return
            vid = self.venda_id
        # Se for uma nova venda
        else:
            res, msg, vid = database.realizar_venda_pdv(self.cliente_atual[0], lista_final, desconto)
            if not res:
                messagebox.showerror("Erro", msg, parent=self)
                return

        if hasattr(self.master, "atualizar_lista"):
            self.master.atualizar_lista()

        from gerenciar_receitas import JanelaGerenciarReceitas
        
        # 1. Liberamos o bloqueio (grab) do PDV temporariamente para a janela de receitas receber cliques
        self.grab_release()
        
        # 2. Abrimos a janela de faturamento passando 'self' (PDV) como pai legítimo
        janela_rec = JanelaGerenciarReceitas(
            self,
            venda_id=vid,
            on_sucesso=None # Removemos o callback antigo para controle síncrono total
        )
        
        # 3. Travamos a execução até que o operador salve e feche a tela de Receitas
        self.wait_window(janela_rec)
        
        # 4. Ao retornar do fechamento da janela de receitas, limpamos o PDV para uma nova venda
        self._limpar_exceto_produtos()
        self._rastreador.marcar_limpo()
        
        # 5. Exibe a mensagem de finalização com sucesso na tela
        messagebox.showinfo(
            "PDV",
            f"Operação finalizada com sucesso.\nVenda total: R$ {total:.2f}\nPDV pronto para nova venda.",
            parent=self
        )
        
        # 6. Se o PDV continuar aberto por algum motivo, restabelecemos o grab de segurança
        try:
            self.grab_set()
        except Exception:
            pass

    def _apos_pagamento_receitas(self, total):
        messagebox.showinfo(
            "PDV",
            f"Pagamento registrado.\nVenda total: R$ {total:.2f}\nPDV pronto para nova venda.",
            parent=self,
        )

    def _limpar_exceto_produtos(self):
        self.cliente_atual = None
        self.carrinho_itens = {}
        if hasattr(self, "ent_desconto"):
            self.ent_desconto.delete(0, tk.END)
            self.ent_desconto.insert(0, "0.00")
        self.txt_cli_detalhes.config(state="normal")
        self.txt_cli_detalhes.delete("1.0", tk.END)
        self.txt_cli_detalhes.insert(tk.END, "Nenhum cliente selecionado.")
        self.txt_cli_detalhes.config(state="disabled")
        self.ent_busca_cli.delete(0, tk.END)
        self.ent_busca_cli.insert(0, self.PLACEHOLDER_BUSCA_CLI)
        self.ent_busca_cli.config(fg="gray")
        self.atualizar_view_carrinho()

    def abrir_novo_cliente(self):
        from cadastro_clientes import JanelaCadastroClientes
        JanelaCadastroClientes(self, on_salvo=lambda cid: self.carregar_dados_cliente_completo(cid))

    def abrir_cadastro_produto(self):
        from cadastro_produtos import JanelaCadastroProdutos
        JanelaCadastroProdutos(self)

    def limpar_formulario(self):
        self._limpar_exceto_produtos()
        self._rastreador.marcar_limpo()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Main Window Mock")
    app = JanelaCadastroVendas(root)
    root.mainloop()
