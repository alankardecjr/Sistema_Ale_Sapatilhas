import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

import config
import database
import ui_utils


class SistemaAleSapatilhas:
    """
    Janela principal estilo ERP: barra lateral + área de listagem + busca.

    Atributos de estado importantes:
        modo_atual: define colunas, filtros e menu de contexto da Treeview
        botao_menu_ativo: referência do botão destacado na sidebar
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Alê Sapatilhas - Gestão Integrada")
        
        ui_utils.calcular_dimensoes_janela(self.root, maximizar=True)
           
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

        self.root.configure(bg=self.bg_fundo)
        self.modo_atual = "vendas"
        self.botoes_menu = {}
        self.botoes_por_texto = {}
        self.botao_menu_ativo = None
        
        self.setup_ui()
        self.botao_menu_ativo = self.botoes_por_texto.get("📑 GERENCIAR VENDAS")
        self.exibir_vendas()

    def formatar_data_exibicao(self, data_str):
        if data_str:
            try: 
                return datetime.strptime(data_str, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError: return data_str
        return ""
    
    def _aplicar_estilo_foco(self, ent):
        def on_enter(e):
            if ent.focus_get() != ent: ent.config(highlightbackground=self.cor_hover_field)
        def on_leave(e):
            if ent.focus_get() != ent: ent.config(highlightbackground=self.cor_borda)
        def on_focus_in(e): ent.config(highlightbackground=self.cor_destaque, highlightthickness=2)
        def on_focus_out(e): ent.config(highlightbackground=self.cor_borda, highlightthickness=1)
        ent.bind("<Enter>", on_enter); ent.bind("<Leave>", on_leave)
        ent.bind("<FocusIn>", on_focus_in); ent.bind("<FocusOut>", on_focus_out)

    def aplicar_hover(self, btn):
        btn.bind("<Enter>", lambda e: btn.config(bg=self.cor_hover_btn) if btn != self.botao_menu_ativo else None)
        btn.bind("<Leave>", lambda e: btn.config(bg=self.cor_btn_menu) if btn != self.botao_menu_ativo else None)

    def setup_ui(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=self.cor_btn_sair, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="ALÊ\nSAPATILHAS", font=("Segoe UI", 23, "bold"), 
                 bg=self.cor_btn_sair, fg="white", pady=20).pack()

        btn_estilo = {
            "font": ("Segoe UI", 10, "bold"), "bg": self.cor_btn_menu, "fg": "white",
            "relief": "flat", "activebackground": self.cor_hover_btn, 
            "activeforeground": "white", "cursor": "hand2", "anchor": "w", "padx": 20
        }

        botoes = [
            ("➕ GERAR VENDAS", self.abrir_cadastro_vendas, "vendas"),
            ("📑 GERENCIAR VENDAS", self.exibir_vendas, "vendas"),
            ("👤 ADICIONAR CONTATOS", self.abrir_cadastro_cliente, "clientes"),
            ("👥 GERENCIAR CONTATOS", self.exibir_clientes, "clientes"),
            ("💸 ADICIONAR DESPESAS", self.abrir_gerenciar_despesas, "financeiro"),
            ("📦 ADICIONAR PRODUTOS", self.abrir_cadastro_produto, "produtos"),
            ("👠 GERENCIAR PRODUTOS", self.exibir_produtos, "produtos"),
            ("📥 CONTAS A RECEBER", self.exibir_contas_a_receber, "contas_receber"),
            ("📤 CONTAS A PAGAR", self.exibir_contas_a_pagar, "contas_pagar"),
            ("📉 FLUXO DE CAIXA", self.exibir_financeiro, "financeiro"),
            ("📊 DASHBOARD", self.exibir_dashboard, "dashboard"),
            ("🔄 ATUALIZAR", self.atualizar_lista, None),
            ("", None, None),
            ("🚪 SAIR", self.confirmar_saida, None)
        ]

        for texto, comando, modo in botoes:
            if texto == "":
                tk.Label(self.sidebar, bg=self.cor_btn_sair, pady=10).pack()
                continue

            btn = tk.Button(self.sidebar, text=texto, **btn_estilo)
            btn.config(command=lambda c=comando, m=modo, b=btn: self.executar_comando_menu(c, m, b))
            btn.pack(fill="x", pady=2)
            self.botoes_por_texto[texto] = btn
            self.aplicar_hover(btn)

            if modo:
                self.botoes_menu.setdefault(modo, []).append(btn)

        self.container = tk.Frame(self.root, bg=self.bg_fundo, padx=20, pady=20)
        self.container.pack(side="right", fill="both", expand=True)
      
        self.criar_barra_busca(self.container)

        self.lbl_titulo = tk.Label(self.container, text="Lista", font=("Segoe UI", 18, "bold"), bg=self.bg_fundo, fg=self.cor_texto)
        self.lbl_titulo.pack(anchor="w", pady=(0, 10))
        
        # --- Tabela (Treeview) ---
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Treeview", background=self.bg_card, foreground=self.cor_texto, rowheight=35, borderwidth=0, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=self.bg_card)
        self.style.map("Treeview", background=[('selected', self.cor_destaque)])
        
        self.tree_frame = tk.Frame(self.container, bg=self.bg_card)
        self.tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(self.tree_frame, show="headings", selectmode="browse")
        self.tree.pack(side="left", fill="both", expand=True)
       
        self.tree.bind("<Double-1>", lambda e: self.editar_selecionado())
        self.tree.bind("<Button-3>", self.mostrar_menu_contexto)
        self.tree.bind("<Motion>", self.focus_linha_mouse)
        
        self.atualizar_destaque_menu()

    def criar_barra_busca(self, container_pai):
        search_frame = tk.Frame(container_pai, bg=self.bg_fundo)
        search_frame.pack(fill="x", pady=(0, 15))
        tk.Label(search_frame, text="BUSCA RÁPIDA ", font=("Segoe UI", 10, "bold"), bg=self.bg_fundo).pack(side="left")

        self.placeholder_busca = " 🔍 Digite para buscar..."
        self.ent_busca = tk.Entry(search_frame, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto, relief="flat", highlightthickness=1, highlightbackground=self.cor_borda)
        self.ent_busca.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 10))
      
        self.ent_busca.insert(0, self.placeholder_busca)
        self.ent_busca.config(fg="gray")

        self.ent_busca.bind("<FocusIn>", self._remover_placeholder)
        self.ent_busca.bind("<FocusOut>", self._inserir_placeholder)
        self.ent_busca.bind("<KeyRelease>", lambda e: self.filtrar_busca())

        btn_estilo = {
            "font": ("Segoe UI", 9, "bold"), "bg": self.cor_btn_menu, "fg": "white",
            "relief": "flat", "activebackground": self.cor_destaque, "activeforeground": "white",
            "cursor": "hand2", "padx": 15, "pady": 5
        }

        btn_filtrar = tk.Menubutton(search_frame, text="⏳ FILTRAR", **btn_estilo)
        menu_filtrar = tk.Menu(btn_filtrar, tearoff=0, bg=self.bg_card, fg=self.cor_texto, font=("Segoe UI", 9))
        menu_filtrar.add_command(label="Tipo", command=lambda: self.aplicar_filtro_avancado("Tipo"))
        menu_filtrar.add_command(label="Data", command=lambda: self.aplicar_filtro_avancado("Data"))
        menu_filtrar.add_command(label="Status", command=lambda: self.aplicar_filtro_avancado("Status"))
        menu_filtrar.add_separator()
        menu_filtrar.add_command(label="Ordenar", command=lambda: self.aplicar_filtro_avancado("Ordenar"))
        
        btn_filtrar.config(menu=menu_filtrar)
        btn_filtrar.pack(side="left", padx=2)

        btn_limpar = tk.Button(search_frame, text="❌ LIMPAR", command=self.limpar_busca_e_filtros, **btn_estilo)
        btn_limpar.pack(side="left", padx=(2, 0))

    def _remover_placeholder(self, event):
        if self.ent_busca.get() == self.placeholder_busca:
            self.ent_busca.delete(0, tk.END)
            self.ent_busca.config(fg=self.cor_texto)

    def _inserir_placeholder(self, event):
        if not self.ent_busca.get().strip():
            self.ent_busca.insert(0, self.placeholder_busca)
            self.ent_busca.config(fg="gray")

    def aplicar_filtro_avancado(self, tipo_filtro):
        messagebox.showinfo("Filtros", f"Filtro por '{tipo_filtro}' acionado.")

    def limpar_busca_e_filtros(self):
        """Limpa o campo de texto e força o recarregamento total sem perder os dados."""
        self.ent_busca.delete(0, tk.END)
        self.ent_busca.config(fg=self.cor_texto)
        self._inserir_placeholder(None)
        self.root.focus()
        self.atualizar_lista()

    def executar_comando_menu(self, comando, modo, btn=None):
        if comando:
            comando()
        if modo:
            self.modo_atual = modo
        if btn is not None:
            self.botao_menu_ativo = btn
        self.atualizar_destaque_menu()

    def atualizar_destaque_menu(self):
        for texto, btn in self.botoes_por_texto.items():
            if btn == self.botao_menu_ativo:
                btn.config(bg=self.cor_destaque, fg="white")
            else:
                btn.config(bg=self.cor_btn_menu, fg="white")

    def focus_linha_mouse(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.focus(item)
            self.tree.selection_set(item)

    def preparar_colunas(self, colunas):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = colunas
        for col in colunas:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, anchor="center", width=120)

    # --- Métodos de Listagem ---
    def exibir_clientes(self):
        self.modo_atual = "clientes"
        self.lbl_titulo.config(text="👥 CONTATOS")
        self.preparar_colunas(("tipo", "nome", "cpf/cnpj", "telefone", "aniversario", "calcado", "limite", "status"))    
        for c in database.exibir_clientes():
            self.tree.insert("", "end", iid=c[0], values=(c[1], c[2], c[3], c[4], self.formatar_data_exibicao(c[6]), c[7], f"R$ {c[13]:.2f}", c[15]))

    def exibir_produtos(self):
        self.modo_atual = "produtos"
        self.lbl_titulo.config(text="👠 ESTOQUE")
        self.preparar_colunas(("sku", "produto", "material", "cor", "tamanho", "estoque", "preço", "fornecedor", "status"))
        for i in database.exibir_produtos_com_fornecedor():
            self.tree.insert("", "end", iid=i[0], values=(i[1], i[3], i[10], i[4], i[5], i[8], f"R$ {i[7]:.2f}", i[11], i[12]))

    def exibir_vendas(self):
        self.modo_atual = "vendas"
        self.lbl_titulo.config(text="📑 VENDAS")
        self.preparar_colunas(("cliente", "total", "forma", "data", "status"))
        for v in database.relatorio_vendas_geral():
            self.tree.insert("", "end", iid=v[0], values=(v[1], f"R$ {v[2]:.2f}", v[3], self.formatar_data_exibicao(v[5]), v[7]))
   
    def exibir_financeiro(self):
        self.modo_atual = "financeiro"
        self.lbl_titulo.config(text="💸 FLUXO DE CAIXA")
        self.preparar_colunas(("tipo", "nome", "descrição", "valor", "vencimento", "pagamento", "forma", "categoria", "recorrencia", "status"))
        for f in database.obter_todos_registros_financeiros():
            tag = ("cancelado",) if f[10] == "Cancelado" else ()
            self.tree.insert("", "end", iid=f[0], values=(f[1], f[2], f[3], f"R$ {f[4]:.2f}", self.formatar_data_exibicao(f[5]), self.formatar_data_exibicao(f[6]), f[7], f[8], f[9], f[10]), tags=tag)

    def exibir_dashboard(self):
        self.modo_atual = "dashboard"
        res = database.dashboard_resumo()
        msg = (
            f"📊 PAINEL DA LOJA\n{'-'*34}\n"
            f"Contas a receber: R$ {res['total_a_receber']:.2f}\n"
            f"Contas a pagar:    R$ {res['total_a_pagar']:.2f}\n"
            f"Vendas finalizadas: {res['vendas_finalizadas']}\n"
        )
        if res["alertas_estoque"]:
            msg += f"\n🚨 ESTOQUE BAIXO (<{config.LIMITE_ESTOQUE_ALERTA} un.):\n"
            for item in res["alertas_estoque"]:
                msg += f"  • {item[0]}: {item[1]} un.\n"
        else:
            msg += "\n✅ Estoque dentro do limite de alerta."
        messagebox.showinfo("Dashboard", msg, parent=self.root)

    def exibir_contas_a_receber(self):
        self.modo_atual = "contas_receber"
        self.lbl_titulo.config(text="📥 CONTAS A RECEBER")
        self.preparar_colunas(("cliente", "descrição", "valor", "pago", "saldo", "vencimento", "status"))
        for row in database.listar_titulos_abertos(config.TIPO_RECEITA):
            _id, nome, desc, valor, pago, venc, status, saldo = row
            self.tree.insert("", "end", iid=_id, values=(
                nome, desc, f"R$ {valor:.2f}", f"R$ {(pago or 0):.2f}", f"R$ {saldo:.2f}",
                self.formatar_data_exibicao(venc), status,
            ))

    def exibir_contas_a_pagar(self):
        self.modo_atual = "contas_pagar"
        self.lbl_titulo.config(text="📤 CONTAS A PAGAR")
        self.preparar_colunas(("fornecedor", "descrição", "valor", "pago", "saldo", "vencimento", "status"))
        for row in database.listar_titulos_abertos(config.TIPO_DESPESA):
            _id, nome, desc, valor, pago, venc, status, saldo = row
            self.tree.insert("", "end", iid=_id, values=(
                nome, desc, f"R$ {valor:.2f}", f"R$ {(pago or 0):.2f}", f"R$ {saldo:.2f}",
                self.formatar_data_exibicao(venc), status,
            ))

    def abrir_gerenciar_receitas(self):
        from gerenciar_receitas import JanelaGerenciarReceitas
        JanelaGerenciarReceitas(self.root)
        self.atualizar_lista()

    def abrir_gerenciar_despesas(self):
        from gerenciar_despesas import JanelaGerenciarDespesas
        JanelaGerenciarDespesas(self.root)
        self.atualizar_lista()

    def abrir_cadastro_vendas(self):
        selection = self.tree.selection()
        cliente_selecionado = None
        if self.modo_atual == "clientes" and selection:
            valores = self.tree.item(selection[0], "values")
            cliente_selecionado = (selection[0], valores[1], valores[3])
        from cadastro_vendas import JanelaCadastroVendas
        JanelaCadastroVendas(self.root, cliente_selecionado)
        self.exibir_vendas()

    def abrir_cadastro_cliente(self):
        from cadastro_clientes import JanelaCadastroClientes
        JanelaCadastroClientes(self.root)
        self.exibir_clientes()

    def abrir_cadastro_produto(self):
        from cadastro_produtos import JanelaCadastroProdutos
        JanelaCadastroProdutos(self.root)
        self.exibir_produtos()

    def editar_selecionado(self):
        item_id = self.tree.selection()
        if not item_id: return
        id_banco = item_id[0]

        if self.modo_atual == "clientes":
            from cadastro_clientes import JanelaCadastroClientes
            with database.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM clientes WHERE id = ?", (id_banco,))
                dados = cursor.fetchone()
                if dados: 
                    JanelaCadastroClientes(self.root, dados_cliente=dados)
                    self.exibir_clientes()

        elif self.modo_atual == "produtos":
            from cadastro_produtos import JanelaCadastroProdutos
            with database.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM produtos WHERE id = ?", (id_banco,))
                dados = cursor.fetchone()
                if dados: 
                    JanelaCadastroProdutos(self.root, dados_produto=dados)
                    self.exibir_produtos()

        elif self.modo_atual in ("financeiro", "contas_receber", "contas_pagar"):
            self.editar_financeiro_registro()

        elif self.modo_atual == "vendas":
            self.editar_venda()

    def editar_financeiro_registro(self):
        item = self.tree.selection()
        if not item: return
        dados = database.obter_financeiro_por_id(item[0])
        if not dados: return
        if dados[1] == config.TIPO_DESPESA:
            from gerenciar_despesas import JanelaGerenciarDespesas
            JanelaGerenciarDespesas(self.root, dados_despesa=dados)
        elif dados[1] == config.TIPO_RECEITA:
            from gerenciar_receitas import JanelaGerenciarReceitas
            JanelaGerenciarReceitas(self.root, dados_receita=dados, venda_id=dados[2])
        self.atualizar_lista()

    def mostrar_menu_contexto(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            menu = tk.Menu(self.root, tearoff=0)
            
            if self.modo_atual == "clientes":
                menu.add_command(label="Editar Contato", command=self.editar_selecionado)
                menu.add_command(label="Visualizar Contato", command=self.visualizar_cliente)
                menu.add_separator()
                for status in ["✓ Ativo", "★ VIP", "⛔ Bloqueado"]:
                    menu.add_command(label=status, command=lambda s=status: self._mudar_status_cliente(s))
                
            elif self.modo_atual == "produtos":
                menu.add_command(label="Editar Produto", command=self.editar_selecionado)
                menu.add_command(label="Visualizar Produto", command=self.visualizar_item)
                menu.add_separator()
                for status in ["✓ Disponível", "✗ Indisponível", "★ Promocional"]:
                    menu.add_command(label=status, command=lambda s=status: self._mudar_status_produto(s))
                
            elif self.modo_atual == "financeiro":
                valores = self.tree.item(item, "values")
                tipo_reg = valores[0] if valores else "Registro"
                if tipo_reg == "Receita":
                    menu.add_command(label="Receber / Baixar parcela", command=self.editar_financeiro_registro)
                else:
                    menu.add_command(label="Pagar / Editar despesa", command=self.editar_financeiro_registro)
                menu.add_command(label=f"Visualizar {tipo_reg}", command=self.visualizar_despesa)
                menu.add_separator()
                for status in ["✓ Pago", "◎ Pendente", "⚠ Atrasado", "✗ Cancelado"]:
                    menu.add_command(label=status, command=lambda s=status: self._mudar_status_despesa(s))
                
            elif self.modo_atual == "vendas":
                menu.add_command(label="Editar itens da venda (PDV)", command=self.editar_venda)
                menu.add_command(label="Financeiro / Receber", command=self.abrir_financeiro_venda)
                menu.add_command(label="Visualizar Venda", command=self.visualizar_venda)
                menu.add_separator()
                for status in ["✓ Finalizada", "⏳ Pendente", "✗ Cancelada"]:
                    menu.add_command(label=status, command=lambda s=status: self._mudar_status_venda(s))

            elif self.modo_atual in ("contas_receber", "contas_pagar"):
                menu.add_command(label="Baixar / Editar lançamento", command=self.editar_financeiro_registro)
                menu.add_command(label="Visualizar título", command=self.visualizar_despesa)

            menu.post(event.x_root, event.y_root)

    def filtrar_busca(self):
        """Nova lógica de busca estável: oculta os elementos baseando-se no valor de texto real."""
        termo = self.ent_busca.get().lower().strip()
        
        # Se estiver vazio ou for o placeholder, restaura e exibe tudo nativamente
        if not termo or termo == self.placeholder_busca.lower().strip():
            self.atualizar_lista()
            return

        # Avalia item por item dentro da Treeview ativa
        for item in self.tree.get_children():
            valores = self.tree.item(item)['values']
            if any(termo in str(v).lower() for v in valores):
                self.tree.reattach(item, '', 'end')
            else:
                self.tree.detach(item)

    def abrir_financeiro_venda(self):
        item = self.tree.selection()
        if not item: return
        from gerenciar_receitas import JanelaGerenciarReceitas
        JanelaGerenciarReceitas(self.root, venda_id=item[0])

    def _mudar_status_cliente(self, novo_status):
        item = self.tree.selection()
        st = ui_utils.normalizar_status_menu(novo_status, ui_utils.STATUS_MENU_CLIENTE)
        if item and messagebox.askyesno("Confirmar", f"Alterar status para '{st}'?"):
            database.atualizar_cliente(item[0], status_cliente=st)
            self.exibir_clientes()

    def _mudar_status_produto(self, novo_status):
        item = self.tree.selection()
        st = ui_utils.normalizar_status_menu(novo_status, ui_utils.STATUS_MENU_PRODUTO)
        if item and messagebox.askyesno("Confirmar", f"Alterar status para '{st}'?"):
            database.atualizar_produto(item[0], status_item=st)
            self.exibir_produtos()

    def _mudar_status_despesa(self, novo_status):
        item = self.tree.selection()
        if not item: return
        id_banco = item[0]
        data_pagamento = None
        novo_status = ui_utils.normalizar_status_menu(novo_status, ui_utils.STATUS_MENU_FINANCEIRO)

        if novo_status == "Pago":
            with database.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT data_pagamento FROM financeiro WHERE id = ?", (id_banco,))
                resultado = cursor.fetchone()
                data_existente = resultado[0] if resultado else None

            hoje = datetime.now().strftime("%Y-%m-%d")
            if data_existente:
                data_formatada = self.formatar_data_exibicao(data_existente)
                pergunta = f"Este registro já foi pago em {data_formatada}.\nDeseja alterar para hoje?"
                data_pagamento = hoje if messagebox.askyesno("Alterar Data", pergunta, parent=self.root) else data_existente
            else:
                data_pagamento = hoje

        if messagebox.askyesno("Confirmar", f"Alterar para '{novo_status}'?", parent=self.root):
            with database.conectar() as conn:
                conn.cursor().execute("UPDATE financeiro SET status = ?, data_pagamento = ? WHERE id = ?", (novo_status, data_pagamento, id_banco))
                conn.commit()
            self.exibir_financeiro()

    def _mudar_status_venda(self, novo_status):
        item = self.tree.selection()
        st = ui_utils.normalizar_status_menu(novo_status, ui_utils.STATUS_MENU_VENDA)
        if not item: return
        if st == "Cancelada":
            if messagebox.askyesno("Confirmar", "Estornar esta venda e devolver estoque?"):
                ok, msg = database.cancelar_venda(item[0])
                messagebox.showinfo("Sucesso", msg) if ok else messagebox.showerror("Erro", msg)
                self.exibir_vendas()
            return
        if messagebox.askyesno("Confirmar", f"Mudar status da venda para {st}?"):
            with database.conectar() as conn:
                conn.execute("UPDATE vendas SET status_venda = ? WHERE id = ?", (st, item[0]))
                conn.commit()
            self.exibir_vendas()
  
    def editar_venda(self):
        item = self.tree.selection()
        if not item: return
        from cadastro_vendas import JanelaCadastroVendas
        v = database.obter_venda_por_id(item[0])
        if v:
            dados_venda = {'id': v[0], 'desconto': v[6], 'forma': v[8], 'parcelas': v[9]}
            JanelaCadastroVendas(self.root, dados_venda=dados_venda)
            self.exibir_vendas()
  
    def visualizar_venda(self):
        """Correção crítica: Instancia um tk.Toplevel em vez de chamar self.title."""
        item = self.tree.selection()
        if not item: return
        id_venda = item[0]

        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.id, c.nome, c.cpf, c.telefone, c.email, c.aniversario, c.tamanho_calcado, 
                       c.endereco_completo, c.bairro, c.cidade, c.cep, c.observacao, c.limite_credito, c.status_cliente,
                       v.valor_bruto, v.desconto, v.valor_total, v.forma_pagamento, v.qtd_parcelas, v.data_venda, v.status_venda, v.vendedor,
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
            messagebox.showerror("Erro", "Venda não encontrada!", parent=self.root)
            return
        
        # Criação da subjanela correta
        janela = tk.Toplevel(self.root)
        janela.title("Recibo Eletrônico de Venda")
        janela.configure(bg=self.bg_fundo)
        janela.transient(self.root)
        janela.grab_set()
        ui_utils.calcular_dimensoes_janela(janela, largura_desejada=580, altura_desejada=620)
        
        main_frame = tk.Frame(janela, bg=self.bg_fundo, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        tk.Label(main_frame, text="🧾 DETALHES DA VENDA", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 14, "bold")).pack(pady=(0, 15))
        
        info_text = f"""
=== DADOS DA VENDA ===
ID da Venda: {dados[0]}
Data: {self.formatar_data_exibicao(dados[19])}
Status: {dados[20]}
Vendedor: {dados[21] or 'N/A'}

=== DADOS DO CLIENTE ===
Nome: {dados[1]}
CPF: {dados[2]} | Tel: {dados[3]}
Endereço: {dados[7] or 'N/A'}, Bairro: {dados[8] or 'N/A'} - {dados[9] or 'N/A'}
Limite de Crédito: R$ {dados[12]:.2f} | Status Cliente: {dados[13]}

=== FINANCEIRO ===
Valor Bruto: R$ {dados[14]:.2f}
Desconto: R$ {dados[15]:.2f}
Valor Líquido Total: R$ {dados[16]:.2f}
Forma de Pagamento: {dados[17]} ({dados[18]}x)

=== PRODUTOS VENDIDOS ===
{dados[22]}
        """
        
        lbl_info = tk.Label(main_frame, text=info_text.strip(), bg=self.bg_card, fg=self.cor_texto, font=("Courier New", 9), justify="left", relief="solid", borderwidth=1, padx=10, pady=10)
        lbl_info.pack(fill="both", expand=True, pady=(0, 15))
        
        tk.Button(main_frame, text="FECHAR RECEITO", bg=self.cor_destaque, fg="white", font=("Segoe UI", 10, "bold"), command=janela.destroy).pack()
        
    def visualizar_cliente(self):
        item = self.tree.selection()
        if not item: return
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tipo, nome, cpf, telefone, email, aniversario, tamanho_calcado, endereco_completo, bairro, city=cidade, cep, observacao, limite_credito, status_cliente FROM clientes WHERE id = ?", (item[0],))
            dados = cursor.fetchone()
        if not dados: return
        
        janela = tk.Toplevel(self.root)
        janela.title("Visualizar Contato")
        janela.configure(bg=self.bg_fundo)
        ui_utils.calcular_dimensoes_janela(janela, largura_desejada=560, altura_desejada=620)
        
        info_text = f"Tipo: {dados[0]}\nNome: {dados[1]}\nCPF: {dados[2] or 'N/A'}\nTelefone: {dados[3] or 'N/A'}\nEmail: {dados[4] or 'N/A'}\nLimite de Crédito: R$ {float(dados[12] or 0):.2f}\nStatus: {dados[13]}"
        frame = tk.Frame(janela, bg=self.bg_fundo, padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="👤 VISUALIZAR CONTATO", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        tk.Label(frame, text=info_text.strip(), bg=self.bg_card, fg=self.cor_texto, font=("Courier New", 10), justify="left", relief="solid", borderwidth=1, padx=10, pady=10).pack(fill="both", expand=True)
        tk.Button(frame, text="FECHAR", bg=self.cor_destaque, fg="white", font=("Segoe UI", 10, "bold"), command=janela.destroy).pack(pady=10)

    def visualizar_despesa(self):
        item = self.tree.selection()
        if not item: return
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tipo, entidade_nome, descricao, valor, parcelas_atual, total_parcelas, data_vencimento, data_pagamento, forma_pagamento, categoria, status, recorrencia FROM financeiro WHERE id = ?", (item[0],))
            dados = cursor.fetchone()
        if not dados: return

        tipo, entidade_nome, descricao, valor, parcela_atual, total_parcelas, data_vencimento, data_pagamento, forma_pagamento, categoria, status, recorrencia = dados
        janela = tk.Toplevel(self.root)
        janela.title(f"Visualizar {tipo}")
        janela.configure(bg=self.bg_fundo)
        ui_utils.calcular_dimensoes_janela(janela, largura_desejada=560, altura_desejada=620)

        info_text = f"Tipo: {tipo}\nEntidade: {entidade_nome}\nDescrição: {descricao}\nValor: R$ {valor:.2f}\nParcela: {parcelas_atual if 'parcelas_atual' in locals() else parcela_atual} de {total_parcelas}\nStatus: {status}"
        frame = tk.Frame(janela, bg=self.bg_fundo, padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=f"💰 VISUALIZAR RECURSO", bg=self.bg_fundo, fg=self.cor_destaque, font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        tk.Label(frame, text=info_text.strip(), bg=self.bg_card, fg=self.cor_texto, font=("Courier New", 10), justify="left", relief="solid", borderwidth=1, padx=10, pady=10).pack(fill="both", expand=True)
        tk.Button(frame, text="FECHAR", bg=self.cor_destaque, fg="white", font=("Segoe UI", 10, "bold"), command=janela.destroy).pack(pady=10)

    def visualizar_item(self):
        item = self.tree.selection()
        if item:
            from cadastro_produtos import VisualizarProduto
            with database.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM produtos WHERE id = ?", (item[0],))
                dados = cursor.fetchone()
                if dados: VisualizarProduto(self.root, dados)

    def atualizar_lista(self):
        if self.modo_atual == "clientes": self.exibir_clientes()
        elif self.modo_atual == "produtos": self.exibir_produtos()
        elif self.modo_atual == "financeiro": self.exibir_financeiro()
        elif self.modo_atual == "vendas": self.exibir_vendas()
        elif self.modo_atual == "dashboard": self.exibir_dashboard()
        elif self.modo_atual == "contas_receber": self.exibir_contas_a_receber()
        elif self.modo_atual == "contas_pagar": self.exibir_contas_a_pagar()

    def confirmar_saida(self):
        if messagebox.askyesno("Sair", "Deseja encerrar o sistema Ale Sapatilhas?"):
            self.root.destroy()


if __name__ == "__main__":
    database.criar_tabelas()
    root = tk.Tk()
    app = SistemaAleSapatilhas(root)
    root.mainloop()