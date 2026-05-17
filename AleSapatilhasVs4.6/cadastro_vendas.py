"""
cadastro_vendas.py — PDV (Ponto de Venda): operação comercial da loja.

Responsabilidades:
  - Montar carrinho, validar estoque e cliente
  - Finalizar venda (database.realizar_venda_segura)
  - Editar itens de venda existente / estornar (database.cancelar_venda)

Pagamentos e parcelas financeiras: use gerenciar_receitas.py após a venda.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import config
import database
import ui_utils


class JanelaCadastroVendas(tk.Toplevel):
    """Checkout fullscreen: cliente + estoque + carrinho."""

    FORMAS_PAGAMENTO = list(config.FORMAS_PAGAMENTO)

    def __init__(self, master, cliente_selecionado=None, dados_venda=None):
        super().__init__(master)
        self.master = master
        self.title("Alê Sapatilhas - Checkout de Vendas")
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

        self.configurar_estilos()
        self.setup_layout()

        if cliente_selecionado:
            cid = cliente_selecionado[0] if isinstance(cliente_selecionado, (tuple, list)) else cliente_selecionado
            self.carregar_dados_cliente_completo(cid)
        elif self.venda_id:
            v = database.obter_venda_por_id(self.venda_id)
            if v:
                self.carregar_dados_cliente_completo(v[1])
                self.cb_forma.set(v[8] or "Dinheiro")
                self.ent_parcelas.delete(0, tk.END)
                self.ent_parcelas.insert(0, str(v[9] or 1))
                self.ent_desconto.delete(0, tk.END)
                self.ent_desconto.insert(0, f"{v[6]:.2f}")
                self._carregar_itens_venda()
                if v[11] == config.STATUS_VENDA_CANCELADA:
                    self.lbl_modo.config(text="VENDA CANCELADA (somente consulta)")
                    self.btn_finalizar.config(state="disabled")

        self.listar_estoque_completo()

    def configurar_estilos(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("PDV.Treeview", background=self.bg_card, foreground=self.cor_texto,
                             rowheight=30, font=("Segoe UI", 10))
        self.style.configure("PDV.Treeview.Heading", font=("Segoe UI", 10, "bold"), background=self.bg_card)
        self.style.map("PDV.Treeview", background=[("selected", self.cor_destaque)])

    def setup_layout(self):
        self.sidebar = tk.Frame(self, bg=self.cor_btn_sair, width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="ALÊ\nSAPATILHAS", font=("Segoe UI", 23, "bold"),
                 bg=self.cor_btn_sair, fg="white", pady=20).pack()

        btn_estilo = {
            "font": ("Segoe UI", 10, "bold"), "bg": self.cor_btn_menu, "fg": "white",
            "relief": "flat", "cursor": "hand2", "anchor": "w", "padx": 20, "pady": 10,
        }
        titulo_acao = "💾 SALVAR ALTERAÇÕES" if self.venda_id else "💰 FINALIZAR VENDA"
        botoes = [
            ("", None, None),
            (titulo_acao, self.finalizar_venda),
            ("❌ REMOVER ITEM", self.remover_do_carrinho),
            ("↩ ESTORNAR VENDA", self.estornar_venda) if self.venda_id else None,
            ("👤 NOVO CLIENTE", self.abrir_novo_cliente),
            ("📦 NOVO PRODUTO", self.abrir_cadastro_produto),
            ("🔄 ATUALIZAR", self.listar_estoque_completo),
            ("", None, None), ("", None, None),
            ("🚪 SAIR", self.destroy),
        ]
        for item in botoes:
            if not item:
                tk.Label(self.sidebar, bg=self.cor_btn_sair, pady=5).pack()
                continue
            texto, comando = item
            btn = tk.Button(self.sidebar, text=texto, command=comando, **btn_estilo)
            btn.pack(fill="x", pady=2)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.cor_hover_btn))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.cor_btn_menu))
            if "FINALIZAR" in texto or "SALVAR" in texto:
                self.btn_finalizar = btn

        self.main_container = tk.Frame(self, bg=self.bg_fundo, padx=20, pady=10)
        self.main_container.pack(side="right", fill="both", expand=True)
        self.lbl_modo = tk.Label(
            self.main_container,
            text="EDIÇÃO DE VENDA" if self.venda_id else "NOVA VENDA (PDV)",
            font=("Segoe UI", 12, "bold"), bg=self.bg_fundo, fg=self.cor_destaque,
        )
        self.lbl_modo.pack(anchor="w", pady=(0, 8))
        self.setup_sessao_cliente()
        self.colunas_frame = tk.Frame(self.main_container, bg=self.bg_fundo)
        self.colunas_frame.pack(fill="both", expand=True, pady=10)
        self.setup_sessao_produtos(self.colunas_frame)
        self.setup_sessao_carrinho(self.colunas_frame)
        self._setup_pagamento()

    def _setup_pagamento(self):
        f = tk.LabelFrame(self.main_container, text=" Pagamento ", bg=self.bg_fundo,
                          fg=self.cor_texto, font=("Segoe UI", 9, "bold"))
        f.pack(fill="x", pady=(0, 8))
        tk.Label(f, text="Forma", bg=self.bg_fundo, font=("Segoe UI", 8, "bold")).grid(row=0, column=0, padx=5, sticky="w")
        self.cb_forma = ttk.Combobox(f, values=self.FORMAS_PAGAMENTO, state="readonly", width=18)
        self.cb_forma.set("Dinheiro")
        self.cb_forma.grid(row=1, column=0, padx=5, pady=4)
        tk.Label(f, text="Parcelas", bg=self.bg_fundo, font=("Segoe UI", 8, "bold")).grid(row=0, column=1, padx=5, sticky="w")
        self.ent_parcelas = tk.Entry(f, width=6, font=("Segoe UI", 10))
        self.ent_parcelas.insert(0, "1")
        self.ent_parcelas.grid(row=1, column=1, padx=5, pady=4)
        tk.Label(f, text="Desconto (R$)", bg=self.bg_fundo, font=("Segoe UI", 8, "bold")).grid(row=0, column=2, padx=5, sticky="w")
        self.ent_desconto = tk.Entry(f, width=10, font=("Segoe UI", 10))
        self.ent_desconto.insert(0, "0.00")
        self.ent_desconto.bind("<KeyRelease>", lambda e: self.atualizar_view_carrinho())
        self.ent_desconto.grid(row=1, column=2, padx=5, pady=4)
        tk.Label(f, text="Baixa de parcelas: menu Gerenciar Receitas", bg=self.bg_fundo, fg="#64748B",
                 font=("Segoe UI", 8, "italic")).grid(row=1, column=3, padx=10, sticky="w")

    def setup_sessao_cliente(self):
        frame_cli = tk.Frame(self.main_container, bg=self.bg_fundo)
        frame_cli.pack(fill="x")
        f_busca = tk.Frame(frame_cli, bg=self.bg_fundo)
        f_busca.pack(side="left", fill="y")
        tk.Label(f_busca, text="BUSCAR CLIENTE", font=("Segoe UI", 8, "bold"), bg=self.bg_fundo).pack(anchor="w")
        self.ent_busca_cli = tk.Entry(f_busca, font=("Segoe UI", 10), width=30, highlightthickness=1)
        self.ent_busca_cli.pack(pady=2)
        self.ent_busca_cli.bind("<KeyRelease>", lambda e: self.buscar_cliente_db())
        self.tree_cli = ttk.Treeview(f_busca, columns=("nome",), show="headings", height=3, style="PDV.Treeview")
        self.tree_cli.heading("nome", text="NOME")
        self.tree_cli.column("nome", width=250)
        self.tree_cli.pack()
        self.tree_cli.bind("<<TreeviewSelect>>", self.selecionar_cliente_busca)
        self.frame_dados_detalhados = tk.LabelFrame(
            frame_cli, text=" 👤 DADOS DO CLIENTE ", bg=self.bg_card, fg=self.cor_texto,
            font=("Segoe UI", 10, "bold"),
        )
        self.frame_dados_detalhados.pack(side="right", fill="both", expand=True, padx=(20, 0))
        self.txt_dados_cliente = tk.Text(
            self.frame_dados_detalhados, font=("Segoe UI", 10), height=6,
            bg=self.bg_card, relief="flat", state="disabled",
        )
        self.txt_dados_cliente.pack(fill="both", expand=True, padx=10, pady=5)

    def setup_sessao_produtos(self, parent):
        f_prod = tk.LabelFrame(parent, text=" 👠 LISTA DE PRODUTOS ", bg=self.bg_fundo,
                               fg=self.cor_texto, font=("Segoe UI", 10, "bold"))
        f_prod.pack(side="left", fill="both", expand=True, padx=(0, 10))
        barra_busca = tk.Frame(f_prod, bg=self.bg_fundo)
        barra_busca.pack(fill="x", padx=5, pady=5)
        self.ent_busca_prod = tk.Entry(barra_busca, font=("Segoe UI", 10), highlightthickness=1)
        self.ent_busca_prod.pack(side="left", fill="x", expand=True)
        self._placeholder_prod = "Pesquisar produto..."
        self.ent_busca_prod.insert(0, self._placeholder_prod)
        self.ent_busca_prod.bind("<FocusIn>", lambda e: self._clear_placeholder())
        self.ent_busca_prod.bind("<FocusOut>", lambda e: self._add_placeholder())
        self.ent_busca_prod.bind("<KeyRelease>", lambda e: self.filtrar_produtos())
        cols = ("id", "prod", "cor", "tam", "preco", "qtd")
        self.tree_estoque = ttk.Treeview(f_prod, columns=cols, show="headings", style="PDV.Treeview")
        for col in cols:
            self.tree_estoque.heading(col, text=col.upper())
            self.tree_estoque.column(col, width=70, anchor="center")
        self.tree_estoque.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree_estoque.bind("<Double-1>", self.adicionar_ao_carrinho)

    def setup_sessao_carrinho(self, parent):
        f_cart = tk.LabelFrame(parent, text=" 🛒 CARRINHO ", bg=self.bg_card, fg=self.cor_destaque,
                               font=("Segoe UI", 10, "bold"))
        f_cart.pack(side="right", fill="both", expand=True)
        self.tree_cart = ttk.Treeview(f_cart, columns=("id", "prod", "tam", "qtd", "sub"),
                                    show="headings", style="PDV.Treeview")
        for col in ("id", "prod", "tam", "qtd", "sub"):
            self.tree_cart.heading(col, text=col.upper())
            self.tree_cart.column(col, width=80, anchor="center")
        self.tree_cart.pack(fill="both", expand=True, padx=5, pady=5)
        self.lbl_total = tk.Label(f_cart, text="TOTAL: R$ 0,00", font=("Segoe UI", 22, "bold"),
                                  bg=self.bg_card, fg=self.cor_destaque)
        self.lbl_total.pack(pady=10)

    def _clear_placeholder(self):
        if self.ent_busca_prod.get() == self._placeholder_prod:
            self.ent_busca_prod.delete(0, tk.END)

    def _add_placeholder(self):
        if not self.ent_busca_prod.get():
            self.ent_busca_prod.insert(0, self._placeholder_prod)

    def carregar_dados_cliente_completo(self, cliente_id):
        with database.conectar() as conn:
            c = conn.execute(
                "SELECT * FROM clientes WHERE id = ? AND tipo = ?",
                (cliente_id, config.TIPO_CLIENTE),
            ).fetchone()
        if c:
            info = (
                f"NOME: {c[2]}\nCPF: {c[3] or 'N/A'} | TEL: {c[4]}\n"
                f"CALÇADO: {c[7] or 'N/A'} | LIMITE: R$ {float(c[13] or 0):.2f}\n"
                f"STATUS: {c[15]}"
            )
            self.txt_dados_cliente.config(state="normal")
            self.txt_dados_cliente.delete("1.0", tk.END)
            self.txt_dados_cliente.insert("1.0", info)
            self.txt_dados_cliente.config(state="disabled")
            self.cliente_atual = c

    def _carregar_itens_venda(self):
        self.carrinho_itens = {}
        for row in database.obter_itens_venda(self.venda_id):
            pid, prod, _cor, tam, qtd, preco, sub = row
            self.carrinho_itens[str(pid)] = {
                "id": pid, "prod": prod, "tam": tam, "preco": preco, "qtd": qtd, "sub": sub,
            }
        self.atualizar_view_carrinho()

    def buscar_cliente_db(self):
        termo = self.ent_busca_cli.get()
        self.tree_cli.delete(*self.tree_cli.get_children())
        if len(termo) >= 2:
            for row in database.listar_contatos(tipo=config.TIPO_CLIENTE, termo=termo):
                self.tree_cli.insert("", "end", iid=row[0], values=(row[2],))

    def selecionar_cliente_busca(self, event):
        sel = self.tree_cli.selection()
        if sel:
            self.carregar_dados_cliente_completo(sel[0])

    def listar_estoque_completo(self):
        self.tree_estoque.delete(*self.tree_estoque.get_children())
        for p in database.listar_itens():
            self.tree_estoque.insert("", "end", iid=p[0], values=(
                p[0], p[1], p[2], p[3], f"R$ {p[5]:.2f}", p[6],
            ))

    def filtrar_produtos(self):
        termo = self.ent_busca_prod.get().lower()
        if termo == self._placeholder_prod.lower():
            return
        self.tree_estoque.delete(*self.tree_estoque.get_children())
        for p in database.listar_itens():
            if termo in p[1].lower() or termo in p[2].lower():
                self.tree_estoque.insert("", "end", iid=p[0], values=(
                    p[0], p[1], p[2], p[3], f"R$ {p[5]:.2f}", p[6],
                ))

    def adicionar_ao_carrinho(self, event):
        sel = self.tree_estoque.selection()
        if not sel:
            return
        id_prod = str(sel[0])
        item = self.tree_estoque.item(id_prod, "values")
        qtd_estoque = int(item[5])
        if qtd_estoque <= 0:
            messagebox.showwarning("Aviso", "Produto esgotado!", parent=self)
            return
        preco = float(item[4].replace("R$ ", "").replace(",", "."))
        if id_prod in self.carrinho_itens:
            if self.carrinho_itens[id_prod]["qtd"] < qtd_estoque:
                self.carrinho_itens[id_prod]["qtd"] += 1
                self.carrinho_itens[id_prod]["sub"] = self.carrinho_itens[id_prod]["qtd"] * preco
            else:
                messagebox.showwarning("Limite", "Quantidade máxima em estoque atingida.", parent=self)
        else:
            self.carrinho_itens[id_prod] = {
                "id": int(id_prod), "prod": item[1], "tam": item[3],
                "preco": preco, "qtd": 1, "sub": preco,
            }
        self.atualizar_view_carrinho()

    def remover_do_carrinho(self):
        sel = self.tree_cart.selection()
        if not sel:
            return
        id_prod = str(self.tree_cart.item(sel[0], "values")[0])
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
        total_geral = 0
        for dados in self.carrinho_itens.values():
            self.tree_cart.insert("", "end", values=(
                dados["id"], dados["prod"], dados["tam"], dados["qtd"], f"R$ {dados['sub']:.2f}",
            ))
            total_geral += dados["sub"]
        try:
            desc = float(self.ent_desconto.get().replace(",", "."))
        except ValueError:
            desc = 0
        self.lbl_total.config(text=f"TOTAL: R$ {max(total_geral - desc, 0):.2f}")

    def estornar_venda(self):
        if not self.venda_id:
            return
        if messagebox.askyesno("Estornar venda", "Cancelar esta venda e devolver itens ao estoque?", parent=self):
            ok, msg = database.cancelar_venda(self.venda_id)
            if ok:
                messagebox.showinfo("Sucesso", msg, parent=self)
                if hasattr(self.master, "atualizar_lista"):
                    self.master.atualizar_lista()
                self.destroy()
            else:
                messagebox.showerror("Erro", msg, parent=self)

    def finalizar_venda(self):
        if not self.cliente_atual or not self.carrinho_itens:
            messagebox.showerror("Erro", "Selecione um cliente e adicione itens ao carrinho.", parent=self)
            return
        try:
            desconto = float(self.ent_desconto.get().replace(",", "."))
            parcelas = max(1, int(self.ent_parcelas.get() or 1))
        except ValueError:
            messagebox.showerror("Erro", "Desconto ou parcelas inválidos.", parent=self)
            return
        total = sum(d["sub"] for d in self.carrinho_itens.values()) - desconto
        limite = float(self.cliente_atual[13] or 0)
        if total > limite and self.cliente_atual[15] != "Vip" and self.cb_forma.get() == "Crediário":
            if not messagebox.askyesno("Limite", f"Venda excede limite (R$ {limite:.2f}). Continuar?", parent=self):
                return
        lista_final = [{"id": d["id"], "qtd": d["qtd"], "preco": d["preco"]} for d in self.carrinho_itens.values()]
        forma = self.cb_forma.get()
        if not messagebox.askyesno(
            "Confirmar", f"Total líquido: R$ {total:.2f}\nForma: {forma} | {parcelas}x\nConfirmar?", parent=self,
        ):
            return
        if self.venda_id:
            res, msg = database.atualizar_venda_comercial(
                self.venda_id, self.cliente_atual[0], lista_final, desconto,
            )
        else:
            res, msg = database.realizar_venda_segura(
                self.cliente_atual[0], lista_final, forma, parcelas, desconto,
            )
        if res:
            messagebox.showinfo("Sucesso", msg, parent=self)
            if hasattr(self.master, "atualizar_lista"):
                self.master.atualizar_lista()
            self.destroy()
        else:
            messagebox.showerror("Erro", msg, parent=self)

    def abrir_novo_cliente(self):
        from cadastro_clientes import JanelaCadastroClientes
        JanelaCadastroClientes(self)

    def abrir_cadastro_produto(self):
        from cadastro_produtos import JanelaCadastroProdutos        
        JanelaCadastroProdutos(self)

if __name__ == "__main__":
    root = tk.Tk()
    app = JanelaCadastroVendas(root)
    root.mainloop()
