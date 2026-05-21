"""
main.py — Ponto de entrada e navegação principal (shell do ERP).

Este módulo concentra apenas orquestração de telas:
  - Menu lateral com destaque do botão ativo
  - Treeview dinâmica conforme o "modo" (vendas, estoque, financeiro…)
  - Imports tardios (lazy) nos métodos abrir_* para evitar import circular

Para estudar o fluxo, comece por __main__ → SistemaAleSapatilhas → setup_ui.
"""

import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
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
        """Inicializa a janela principal, paleta, estado das listas e exibe vendas."""
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
        self._cache_lista = []  # snapshot completo da lista
        self._lista_exibida = []  # vista atual (filtros + busca)
        self._pilha_vistas = []  # restaura ao apagar busca
        self._termo_busca_anterior = ""
        self._filtros_ativos = {}
        
        self.setup_ui()
        self.botao_menu_ativo = self.botoes_por_texto.get("📑 GERENCIAR VENDAS")
        self.exibir_vendas()

    def formatar_data_exibicao(self, data_str):
        """Delega para o utilitário central de formatação (DD/MM/YYYY)."""
        return ui_utils.formatar_data_exibicao(data_str)
    
    def _aplicar_estilo_foco(self, ent):
        """Aplica hover e destaque de foco em campos Entry da tela principal."""
        def on_enter(e):
            if ent.focus_get() != ent: ent.config(highlightbackground=self.cor_hover_field)
        def on_leave(e):
            if ent.focus_get() != ent: ent.config(highlightbackground=self.cor_borda)
        def on_focus_in(e): ent.config(highlightbackground=self.cor_destaque, highlightthickness=2)
        def on_focus_out(e): ent.config(highlightbackground=self.cor_borda, highlightthickness=1)
        ent.bind("<Enter>", on_enter); ent.bind("<Leave>", on_leave)
        ent.bind("<FocusIn>", on_focus_in); ent.bind("<FocusOut>", on_focus_out)

    def aplicar_hover(self, btn):
        """Destaca botão do menu lateral ao passar o mouse."""
        btn.bind("<Enter>", lambda e: btn.config(bg=self.cor_hover_btn))
        btn.bind("<Leave>", lambda e: btn.config(bg=self.cor_btn_menu))

    def setup_ui(self):
        """Monta sidebar, área de listagem, busca e bindings da Treeview."""
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

        # (texto, callback, modo) — modo agrupa telas relacionadas na Treeview
        botoes = [
            ("➕ NOVA VENDAS", self.abrir_cadastro_vendas, "vendas"),
            #("💰 GERAR RECEITAS", self.abrir_gerenciar_receitas, "financeiro"),
            ("", None, None),
            ("📑 LISTAR VENDAS", self.exibir_vendas, "vendas"),
            ("👥 LISTAR CONTATOS", self.exibir_clientes, "clientes"),
            ("👠 LISTAR PRODUTOS", self.exibir_produtos, "produtos"),
            ("👤 NOVO CONTATOS", self.abrir_cadastro_cliente, "clientes"),
            ("📦 NOVO PRODUTOS", self.abrir_cadastro_produto, "produtos"),
            ("💸 NOVA DESPESAS", self.abrir_gerenciar_despesas, "financeiro"),
            ("", None, None),
            ("📉 FLUXO DE CAIXA", self.exibir_financeiro, "financeiro"),
            ("📥 CONTAS A RECEBER", self.exibir_contas_a_receber, "contas_receber"),
            ("📤 CONTAS A PAGAR", self.exibir_contas_a_pagar, "contas_pagar"),
            ("📊 DASHBOARD", self.exibir_dashboard, "dashboard"),
            ("🔄 ATUALIZAR", self.atualizar_lista, None),
            ("", None, None),
            ("", None, None),
            ("", None, None),
            ("🚪 SAIR", self.confirmar_saida, None)
        ]

        for texto, comando, modo in botoes:
            if texto == "":
                tk.Label(self.sidebar, bg=self.cor_btn_sair, pady=10).pack()
                continue

            # --- Criando botões com estilo e hover ---
            btn = tk.Button(self.sidebar, text=texto, **btn_estilo)
            btn.config(command=lambda c=comando, m=modo, b=btn: self.executar_comando_menu(c, m, b))
            btn.pack(fill="x", pady=2)
            self.botoes_por_texto[texto] = btn
            self.aplicar_hover(btn)

            if modo:
                self.botoes_menu.setdefault(modo, []).append(btn)

        # --- Container Principal para exibir conteúdo dinâmico ---
        self.container = tk.Frame(self.root, bg=self.bg_fundo, padx=20, pady=20)
        self.container.pack(side="right", fill="both", expand=True)
      
        # --- Barra de busca rápida ---
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

        # --- Bindings de interação ---
        # Duplo-clique abre a visualização detalhada apropriada ao modo atual
        self.tree.bind("<Double-1>", lambda e: self.visualizar_selecionado())
        self.tree.bind("<Button-3>", self.mostrar_menu_contexto)
        self.tree.bind("<Motion>", self.focus_linha_mouse)
        
        # Focus no campo de busca
        self.ent_busca.bind("<Enter>", lambda e: self.ent_busca.focus())
      
        # Atualizar destaque do menu
        self.atualizar_destaque_menu()

    # -- Componente de Barra de Busca Avançada ---
    def criar_barra_busca(self, container_pai):
        """Cria campo de busca, botões Filtrar, Limpar e Utilidades."""
        search_frame = tk.Frame(container_pai, bg=self.bg_fundo)
        search_frame.pack(fill="x", pady=(0, 15))
        tk.Label(search_frame, text="BUSCA RÁPIDA", font=("Segoe UI", 10, "bold"), bg=self.bg_fundo).pack(side="left")

        # --- Campo de Entrada com Ícone/Placeholder Integrado ---
        self.placeholder_busca = "🔍 Digite para buscar..."
        self.ent_busca = tk.Entry(search_frame, font=("Segoe UI", 9), bg=self.bg_card, fg=self.cor_texto, relief="flat", highlightthickness=1, highlightbackground=self.cor_borda)
        self.ent_busca.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 10))
      
        # Inserir o subtítulo interno (Placeholder) inicial        
        self.ent_busca.insert(0, self.placeholder_busca)
        self.ent_busca.config(fg="gray")

        # Bindings para comportamento do Placeholder dinâmico
        self.ent_busca.bind("<FocusIn>", self._remover_placeholder)
        self.ent_busca.bind("<FocusOut>", self._inserir_placeholder)
        self.ent_busca.bind("<KeyRelease>", lambda e: self.filtrar_busca())

        btn_estilo = {
            "font": ("Segoe UI", 9, "bold"),
            "bg": self.cor_btn_menu,
            "fg": "white",
            "relief": "flat",
            "activebackground": self.cor_destaque,
            "activeforeground": "white",
            "cursor": "hand2",
            "width": 14,
            "height": 1,
        }

        self.btn_filtrar = tk.Button(search_frame, text="⏳ FILTROS", command=self.abrir_menu_filtrar, **btn_estilo)
        self.btn_filtrar.pack(side="left", padx=2, ipady=6)
        self.btn_filtrar.bind("<Enter>", lambda e: self.btn_filtrar.config(bg=self.cor_hover_btn))
        self.btn_filtrar.bind("<Leave>", lambda e: self.btn_filtrar.config(bg=self.cor_btn_menu))

        self.btn_limpar = tk.Button(search_frame, text="❌ LIMPAR", command=self.limpar_busca_e_filtros, **btn_estilo)
        self.btn_limpar.pack(side="left", padx=2, ipady=6)
        self.btn_limpar.bind("<Enter>", lambda e: self.btn_limpar.config(bg=self.cor_hover_btn))
        self.btn_limpar.bind("<Leave>", lambda e: self.btn_limpar.config(bg=self.cor_btn_menu))

        self.btn_utilidades = tk.Button(search_frame, text="➕ FERRAMENTAS", command=self.abrir_menu_utilidades, **btn_estilo)
        self.btn_utilidades.pack(side="right", padx=2, ipady=6)
        self.btn_utilidades.bind("<Enter>", lambda e: self.btn_utilidades.config(bg=self.cor_hover_btn))
        self.btn_utilidades.bind("<Leave>", lambda e: self.btn_utilidades.config(bg=self.cor_btn_menu))

    def _remover_placeholder(self, event):
        """Remove texto cinza placeholder ao focar o campo de busca."""
        if self.ent_busca.get() == self.placeholder_busca:
            self.ent_busca.delete(0, tk.END)
            self.ent_busca.config(fg=self.cor_texto)

    def _inserir_placeholder(self, event):
        """Restaura placeholder quando o campo de busca fica vazio."""
        if not self.ent_busca.get().strip():
            self.ent_busca.insert(0, self.placeholder_busca)
            self.ent_busca.config(fg="gray")

    def _atualizar_cache_lista(self):
        """Guarda snapshot da Treeview para filtrar sem consultar o banco de novo."""
        self._cache_lista = [(iid, self.tree.item(iid, "values")) for iid in self.tree.get_children()]
        self._lista_exibida = list(self._cache_lista)
        self._pilha_vistas = []
        self._termo_busca_anterior = ""

    def _renderizar_cache(self, linhas):
        """Atualiza a Treeview com lista (iid, valores) e guarda vista atual."""
        self.tree.delete(*self.tree.get_children())
        for iid, valores in linhas:
            self.tree.insert("", "end", iid=iid, values=valores)
        self._lista_exibida = list(linhas)

    def _indice_coluna_filtro(self):
        """Retorna índices de colunas (valores) conforme o modo da lista."""
        mapa = {
            "clientes": {"tipo": 0, "status": 7, "data": 4},
            "produtos": {"tipo": 1, "status": 9},
            "vendas": {"tipo": 1, "status": 5, "data": 4},
            "financeiro": {"tipo": 0, "status": 9, "data": 4},
            "contas_receber": {"status": 6, "data": 5},
            "contas_pagar": {"status": 6, "data": 5},
        }
        return mapa.get(self.modo_atual, {})

    def aplicar_filtro_avancado(self, tipo_filtro):
        """Filtra ou ordena a lista atual conforme o modo exibido."""
        if self.modo_atual == "dashboard":
            messagebox.showinfo("Filtros", "Abra uma lista (vendas, contatos, fluxo…) para usar filtros.", parent=self.root)
            return
        if not self._cache_lista:
            self._atualizar_cache_lista()
        if not self._cache_lista:
            return

        cols = self._indice_coluna_filtro()

        if tipo_filtro == "Tipo":
            if "tipo" not in cols:
                messagebox.showinfo("Filtro Tipo", "Esta lista não possui coluna de tipo.", parent=self.root)
                return
            opcoes = sorted({str(v[cols["tipo"]]) for _, v in self._cache_lista if v[cols["tipo"]]})
            escolha = simpledialog.askstring(
                "Filtrar por tipo",
                f"Tipos disponíveis:\n{', '.join(opcoes)}\n\nDigite o tipo:",
                parent=self.root,
            )
            if not escolha:
                return
            termo = escolha.strip().lower()
            filtrado = [(iid, v) for iid, v in self._cache_lista if termo in str(v[cols["tipo"]]).lower()]
            self._filtros_ativos["tipo"] = escolha
            self._renderizar_cache(filtrado)

        elif tipo_filtro == "Status":
            if "status" not in cols:
                messagebox.showinfo("Filtro Status", "Esta lista não possui coluna de status.", parent=self.root)
                return
            opcoes = sorted({str(v[cols["status"]]) for _, v in self._cache_lista if v[cols["status"]]})
            escolha = simpledialog.askstring(
                "Filtrar por status",
                f"Status: {', '.join(opcoes)}\n\nDigite o status:",
                parent=self.root,
            )
            if not escolha:
                return
            termo = escolha.strip().lower()
            filtrado = [(iid, v) for iid, v in self._cache_lista if termo in str(v[cols["status"]]).lower()]
            self._filtros_ativos["status"] = escolha
            self._renderizar_cache(filtrado)

        elif tipo_filtro == "Data":
            if "data" not in cols:
                messagebox.showinfo("Filtro Data", "Esta lista não possui coluna de data.", parent=self.root)
                return
            escolha = simpledialog.askstring(
                "Filtrar por data",
                "Digite parte da data (ex.: 2026, 05/2026 ou 15/05):",
                parent=self.root,
            )
            if not escolha:
                return
            termo = escolha.strip()
            filtrado = [(iid, v) for iid, v in self._cache_lista if termo in str(v[cols["data"]])]
            self._filtros_ativos["data"] = termo
            self._renderizar_cache(filtrado)

        elif tipo_filtro == "Ordenar":
            menu_ord = tk.Menu(self.root, tearoff=0)
            menu_ord.add_command(label="Data (vencimento / venda) ↑", command=lambda: self._ordenar_lista("data", False))
            menu_ord.add_command(label="Data (vencimento / venda) ↓", command=lambda: self._ordenar_lista("data", True))
            menu_ord.add_command(label="Nome / Cliente (A→Z)", command=lambda: self._ordenar_lista("nome", False))
            menu_ord.add_command(label="Nome / Cliente (Z→A)", command=lambda: self._ordenar_lista("nome", True))
            try:
                menu_ord.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
            except tk.TclError:
                pass

    def _ordenar_lista(self, criterio, reverso):
        if not self._cache_lista:
            self._atualizar_cache_lista()
        cols = self._indice_coluna_filtro()
        if criterio == "data" and "data" in cols:
            idx = cols["data"]
        else:
            idx = 0

        def chave(item):
            val = item[1][idx] if idx < len(item[1]) else ""
            if criterio == "data":
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(str(val), fmt)
                    except ValueError:
                        continue
            return str(val).lower()

        ordenada = sorted(self._cache_lista, key=chave, reverse=reverso)
        self._renderizar_cache(ordenada)

    def abrir_menu_utilidades(self):
        """Abre menu popup com calculadora, calendário, anotações e configurações."""
        menu = tk.Menu(self.root, tearoff=0, bg=self.bg_card, fg=self.cor_texto, font=("Segoe UI", 9))
        menu.add_command(label="Calculadora", command=lambda: self.aplicar_utilidades("Calculadora"))
        menu.add_command(label="Calendário", command=lambda: self.aplicar_utilidades("Calendário"))
        menu.add_command(label="Anotações", command=lambda: self.aplicar_utilidades("Anotações"))
        menu.add_separator()
        menu.add_command(label="Configurações", command=lambda: self.aplicar_utilidades("Configurações"))
        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        except tk.TclError:
            pass

    def aplicar_utilidades(self, tipo_utilidade):
        """Executa a ferramenta auxiliar escolhida no menu Utilidades."""
        if tipo_utilidade == "Calculadora":
            ui_utils.abrir_calculadora(self.root)
        elif tipo_utilidade == "Calendário":
            ref = tk.Entry(self.root)
            ui_utils.MiniCalendario(self.root, ref, titulo="Calendário")
        elif tipo_utilidade == "Anotações":
            ui_utils.abrir_anotacoes(self.root)
        elif tipo_utilidade == "Configurações":
            ui_utils.abrir_configuracoes(self.root)

    def abrir_menu_filtrar(self):
        """Monta menu de filtros dinâmico conforme o modo da lista (tipo, status, data)."""
        if self.modo_atual == "dashboard":
            messagebox.showinfo("Filtros", "Abra uma lista para usar filtros.", parent=self.root)
            return
        if not self._cache_lista:
            self._atualizar_cache_lista()
        if not self._cache_lista:
            return

        menu = tk.Menu(self.root, tearoff=0, bg=self.bg_card, fg=self.cor_texto, font=("Segoe UI", 9))
        cols = self._indice_coluna_filtro()

        if "tipo" in cols:
            sub_tipo = tk.Menu(menu, tearoff=0)
            opcoes = sorted({str(v[cols["tipo"]]) for _, v in self._cache_lista if v[cols["tipo"]]})
            for op in opcoes:
                sub_tipo.add_command(label=op, command=lambda o=op: self._filtrar_por_campo("tipo", o, cols["tipo"]))
            menu.add_cascade(label="Tipo", menu=sub_tipo)

        if "status" in cols:
            sub_st = tk.Menu(menu, tearoff=0)
            opcoes = sorted({str(v[cols["status"]]) for _, v in self._cache_lista if v[cols["status"]]})
            for op in opcoes:
                sub_st.add_command(label=op, command=lambda o=op: self._filtrar_por_campo("status", o, cols["status"]))
            menu.add_cascade(label="Status", menu=sub_st)

        if "data" in cols:
            sub_dt = tk.Menu(menu, tearoff=0)
            for rotulo, modo in [("Hoje (dia)", "Dia"), ("Esta semana", "Semana"), ("Este mês", "Mês"), ("Período personalizado", "Periodo")]:
                sub_dt.add_command(label=rotulo, command=lambda m=modo: self._filtrar_por_data(m, cols["data"]))
            menu.add_cascade(label="Data", menu=sub_dt)

        sub_ord = tk.Menu(menu, tearoff=0)
        sub_ord.add_command(label="Data ↑", command=lambda: self._ordenar_lista("data", False))
        sub_ord.add_command(label="Data ↓", command=lambda: self._ordenar_lista("data", True))
        sub_ord.add_command(label="Nome A→Z", command=lambda: self._ordenar_lista("nome", False))
        sub_ord.add_command(label="Nome Z→A", command=lambda: self._ordenar_lista("nome", True))
        menu.add_cascade(label="Ordenar", menu=sub_ord)

        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        except tk.TclError:
            pass

    def _filtrar_por_campo(self, chave_filtro, valor, idx_col):
        """Filtra a lista exibida por valor em uma coluna (tipo ou status)."""
        termo = str(valor).lower()
        filtrado = [(iid, v) for iid, v in self._cache_lista if termo in str(v[idx_col]).lower()]
        self._filtros_ativos[chave_filtro] = valor
        self._pilha_vistas = []
        self._renderizar_cache(filtrado)

    def _filtrar_por_data(self, modo, idx_col):
        """Filtra registros por dia, semana, mês ou intervalo personalizado."""
        if modo == "Periodo":
            ini = simpledialog.askstring("Período", "Data inicial (DD/MM/AAAA):", parent=self.root)
            fim = simpledialog.askstring("Período", "Data final (DD/MM/AAAA):", parent=self.root)
            if not ini or not fim:
                return
            try:
                d_ini = datetime.strptime(ini.strip(), "%d/%m/%Y").date()
                d_fim = datetime.strptime(fim.strip(), "%d/%m/%Y").date()
            except ValueError:
                messagebox.showerror("Data", "Formato inválido. Use DD/MM/AAAA.", parent=self.root)
                return

            def no_periodo(val):
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(str(val), fmt).date()
                        return d_ini <= dt <= d_fim
                    except ValueError:
                        continue
                return False

            filtrado = [(iid, v) for iid, v in self._cache_lista if no_periodo(v[idx_col])]
        else:
            filtrado = [(iid, v) for iid, v in self._cache_lista if ui_utils.filtro_data_periodo(modo, v[idx_col])]

        self._filtros_ativos["data"] = modo
        self._pilha_vistas = []
        self._renderizar_cache(filtrado)

    def limpar_busca_e_filtros(self):
        """Zera busca, filtros e pilha; recarrega a lista do modo atual."""
        self.ent_busca.delete(0, tk.END)
        self._inserir_placeholder(None)
        self._filtros_ativos = {}
        self._pilha_vistas = []
        self._termo_busca_anterior = ""
        self.root.focus()
        self.atualizar_lista()

    def executar_comando_menu(self, comando, modo, btn=None):
        """Executa ação do menu lateral e atualiza modo/destaque do botão."""
        if comando:
            comando()
        if modo:
            self.modo_atual = modo
        if btn is not None:
            self.botao_menu_ativo = btn
        self.atualizar_destaque_menu()

    def atualizar_destaque_menu(self):
        """Destaca visualmente o botão ativo na barra lateral."""
        for texto, btn in self.botoes_por_texto.items():
            if btn == self.botao_menu_ativo:
                btn.config(bg=self.cor_destaque, fg="white")
            else:
                btn.config(bg=self.cor_btn_menu, fg="white")

    def confirmar_acao_menu(self, titulo, func, mensagem=None):
        """Mostra confirmação antes de executar uma ação de menu de contexto."""
        if not func:
            return
        mensagem = mensagem or f"Deseja realmente {titulo.lower()}?"
        if messagebox.askyesno(titulo, mensagem, parent=self.root):
            func()

    def focus_linha_mouse(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.focus(item)
            self.tree.selection_set(item)

    # --- Função para preparar colunas da Treeview de acordo com o modo atual ---
    def preparar_colunas(self, colunas):
        """Redefine colunas da Treeview e limpa cache de filtros."""
        self.tree.delete(*self.tree.get_children())
        self._cache_lista = []
        self.tree["columns"] = colunas
        for col in colunas:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, anchor="center", width=120)

    # --- Funções de carregamento ---
    def exibir_clientes(self):
        """Carrega e exibe a lista de contatos (clientes/fornecedores)."""
        self.modo_atual = "clientes"
        self.botao_menu_ativo = self.botoes_por_texto.get("👥 LISTAR CONTATOS")
        self.atualizar_destaque_menu()
        self.lbl_titulo.config(text="👥 AGENDA DOS CONTATOS")
        self.preparar_colunas(("tipo", "nome", "cpf/cnpj", "telefone", "aniversario", "calcado", "limite", "status"))    
        for c in database.exibir_clientes():
            # c[1]=tipo, c[2]=nome, c[3]=cpf, c[4]=telefone, c[6]=aniversario, c[7]=calcado, c[13]=limite, c[15]=status
            self.tree.insert("", "end", iid=c[0], values=(c[1], c[2], c[3], c[4], self.formatar_data_exibicao(c[6]), c[7], f"R$ {c[13]:.2f}", c[15]))
        self._atualizar_cache_lista()

    def exibir_produtos(self):
        """Carrega e exibe o estoque de produtos com fornecedor."""
        self.modo_atual = "produtos"
        self.botao_menu_ativo = self.botoes_por_texto.get("👠 LISTAR PRODUTOS")
        self.atualizar_destaque_menu()
        self.lbl_titulo.config(text="👠 CONTROLE DO ESTOQUE")
        self.preparar_colunas(("sku", "tipo", "produto", "material", "cor", "tamanho", "estoque", "preço", "fornecedor", "status"))
        for i in database.exibir_produtos_com_fornecedor():
            tipo_ui = ui_utils.tipo_produto_para_ui(i[2])
            self.tree.insert("", "end", iid=i[0], values=(
                i[1], tipo_ui, i[3], i[10], i[4], i[5], i[8], f"R$ {i[7]:.2f}", i[11], i[12],
            ))
        self._atualizar_cache_lista()

    def exibir_vendas(self):
        """Carrega e exibe o relatório de vendas."""
        self.modo_atual = "vendas"
        self.botao_menu_ativo = self.botoes_por_texto.get("📑 LISTAR VENDAS")
        self.atualizar_destaque_menu()
        self.lbl_titulo.config(text="📑 HISTORICO DE VENDAS")
        self.preparar_colunas(("tipo", "cliente", "total", "forma", "data", "status"))
        for v in database.relatorio_vendas_geral():
            tipo_ui = ui_utils.tipo_produto_para_ui(v[8]) if len(v) > 8 else "—"
            self.tree.insert("", "end", iid=v[0], values=(
                tipo_ui, v[1], f"R$ {v[2]:.2f}", v[3], self.formatar_data_exibicao(v[5]), v[7],
            ))
        self._atualizar_cache_lista()

    def exibir_financeiro(self):
        """Carrega e exibe o fluxo de caixa consolidado."""
        self.modo_atual = "financeiro"
        self.botao_menu_ativo = self.botoes_por_texto.get("📉 FLUXO DE CAIXA")
        self.atualizar_destaque_menu()
        self.lbl_titulo.config(text="💸 FLUXO DE CAIXA (ENTRADAS / SAIDAS)")
        self.preparar_colunas(("tipo", "nome", "descrição", "valor", "vencimento", "pagamento", "forma", "categoria", "recorrencia", "status"))
        for f in database.obter_todos_registros_financeiros():
            tag = ("cancelado",) if f[10] == "Cancelado" else ()
            self.tree.insert("", "end", iid=f[0], values=(f[1], f[2], f[3], f"R$ {f[4]:.2f}", self.formatar_data_exibicao(f[5]), self.formatar_data_exibicao(f[6]), f[7], f[8], f[9], f[10]), tags=tag)
        self._atualizar_cache_lista()

    def exibir_dashboard(self):
        """KPIs operacionais — visão executiva sem sair da tela principal."""
        self.modo_atual = "dashboard"
        self.botao_menu_ativo = self.botoes_por_texto.get("📊 DASHBOARD")
        self.atualizar_destaque_menu()
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
        """Relatório de títulos de Receita em aberto (ordenados por vencimento)."""
        self.modo_atual = "contas_receber"
        self.botao_menu_ativo = self.botoes_por_texto.get("📥 CONTAS A RECEBER")
        self.atualizar_destaque_menu()
        self.lbl_titulo.config(text="📥 HISTORICO DE CONTAS A RECEBER")
        self.preparar_colunas(("cliente", "descrição", "valor", "pago", "saldo", "vencimento", "status"))
        for row in database.listar_titulos_abertos(config.TIPO_RECEITA):
            _id, nome, desc, valor, pago, venc, status, saldo = row
            self.tree.insert("", "end", iid=_id, values=(
                nome, desc, f"R$ {valor:.2f}", f"R$ {(pago or 0):.2f}", f"R$ {saldo:.2f}",
                self.formatar_data_exibicao(venc), status,
            ))
        self._atualizar_cache_lista()

    def exibir_contas_a_pagar(self):
        """Relatório de títulos de Despesa em aberto."""
        self.modo_atual = "contas_pagar"
        self.botao_menu_ativo = self.botoes_por_texto.get("📤 CONTAS A PAGAR")
        self.atualizar_destaque_menu()
        self.lbl_titulo.config(text="📤 HISTORICO DE CONTAS A PAGAR")
        self.preparar_colunas(("fornecedor", "descrição", "valor", "pago", "saldo", "vencimento", "status"))
        for row in database.listar_titulos_abertos(config.TIPO_DESPESA):
            _id, nome, desc, valor, pago, venc, status, saldo = row
            self.tree.insert("", "end", iid=_id, values=(
                nome, desc, f"R$ {valor:.2f}", f"R$ {(pago or 0):.2f}", f"R$ {saldo:.2f}",
                self.formatar_data_exibicao(venc), status,
            ))
        self._atualizar_cache_lista()

    # --- Janelas modais (import tardio = lazy import, boa prática em Tkinter) ---
    def abrir_gerenciar_receitas(self):
        from gerenciar_receitas import JanelaGerenciarReceitas
        JanelaGerenciarReceitas(self.root)
        if self.modo_atual in ("financeiro", "contas_receber"):
            self.atualizar_lista()

    def abrir_gerenciar_despesas(self):
        from gerenciar_despesas import JanelaGerenciarDespesas
        JanelaGerenciarDespesas(self.root)
        if self.modo_atual in ("financeiro", "contas_pagar"):
            self.atualizar_lista()

    def abrir_cadastro_vendas(self):
        """Abre o PDV; se houver cliente selecionado na lista, envia ao checkout."""
        cliente_selecionado = None
        if self.modo_atual == "clientes" and self.tree.selection():
            sel = self.tree.selection()[0]
            valores = self.tree.item(sel, "values")
            cliente_selecionado = (sel, valores[1], valores[3])
        from cadastro_vendas import JanelaCadastroVendas
        JanelaCadastroVendas(self.root, cliente_selecionado)

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

        elif self.modo_atual == "financeiro":
            self._abrir_financeiro_com_senha()

        elif self.modo_atual == "contas_receber":
            self._abrir_financeiro_com_senha()

        elif self.modo_atual == "contas_pagar":
            self._abrir_financeiro_com_senha()

        elif self.modo_atual == "vendas":
            self.editar_venda()

    def visualizar_selecionado(self):
        """Abre a janela de visualização apropriada ao `modo_atual` para o item selecionado.

        Melhor usabilidade: duplo-clique mostra detalhes em vez de entrar em modo de edição.
        """
        item = self.tree.selection()
        if not item:
            return

        # Despacha para o visualizador correto conforme o modo
        if self.modo_atual == "clientes":
            # Visualiza dados do cliente
            try:
                self.visualizar_cliente()
            except Exception:
                self.editar_selecionado()
        elif self.modo_atual == "produtos":
            # Visualiza produto se disponível
            if hasattr(self, "visualizar_item"):
                try:
                    self.visualizar_item()
                except Exception:
                    self.editar_selecionado()
            else:
                self.editar_selecionado()
        elif self.modo_atual in ("financeiro", "contas_receber", "contas_pagar"):
            # Visualiza título financeiro (receita/despesa)
            try:
                self.visualizar_despesa()
            except Exception:
                self.editar_selecionado()
        elif self.modo_atual == "vendas":
            try:
                self.visualizar_venda()
            except Exception:
                self.editar_venda()
        else:
            # Fallback: comportamento anterior
            self.editar_selecionado()

    def _abrir_financeiro_com_senha(self):
        """Baixa de título somente após senha do fluxo de caixa."""
        if not ui_utils.solicitar_senha_fluxo(self.root):
            return
        self.editar_financeiro_registro()

    def editar_financeiro_registro(self):
        """Roteamento: tipo do título define qual módulo financeiro abrir."""
        item = self.tree.selection()
        if not item:
            return
        registro_id = item[0]
        dados = database.obter_financeiro_por_id(registro_id)
        if not dados:
            return
        tipo = dados[1]
        if tipo == config.TIPO_DESPESA:
            from gerenciar_despesas import JanelaGerenciarDespesas
            JanelaGerenciarDespesas(self.root, dados_despesa=dados)
        elif tipo == config.TIPO_RECEITA:
            from gerenciar_receitas import JanelaGerenciarReceitas
            JanelaGerenciarReceitas(self.root, dados_receita=dados, venda_id=dados[2])
        self.atualizar_lista()

    # --- Função para mostrar menu de contexto ---
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
                    menu.add_command(label="Receber / Baixar parcela", command=self._abrir_financeiro_com_senha)
                else:
                    menu.add_command(label="Pagar / Editar despesa", command=self._abrir_financeiro_com_senha)
                menu.add_command(label=f"Visualizar {tipo_reg}", command=self.visualizar_despesa)
                menu.add_separator()
                for status in ["✓ Pago", "◎ Pendente", "⚠ Atrasado", "✗ Cancelado"]:
                    menu.add_command(label=status, command=lambda s=status: self._mudar_status_despesa(s))
                
            elif self.modo_atual == "vendas":
                menu.add_command(label="Editar itens da venda", command=self.editar_venda)
                menu.add_command(label="Financeiro / Receber", command=self.abrir_financeiro_venda)
                menu.add_command(label="Visualizar Venda", command=self.visualizar_venda)

                # --- Desativado por enquanto, pois o status de venda é mais complexo e pode exigir lógica adicional (ex.: só permitir "Finalizada" se tiver itens e pagamento registrado) ---
                #menu.add_separator()
                #for status in [ "⏳ Pendente","✓ Finalizada", "✗ Cancelada"]:
                #menu.add_command(label=status, command=lambda s=status: self._mudar_status_venda(s))

            elif self.modo_atual == "contas_receber":
                menu.add_command(label="Baixar / Receber parcela", command=self._abrir_financeiro_com_senha)
                menu.add_command(label="Visualizar título", command=self.visualizar_despesa)
                menu.add_separator()
                for status in ["✓ Pago", "◎ Pendente", "⚠ Atrasado", "✗ Cancelado"]:
                    menu.add_command(label=status, command=lambda s=status: self._mudar_status_despesa(s))

            elif self.modo_atual == "contas_pagar":
                menu.add_command(label="Pagar / Editar despesa", command=self._abrir_financeiro_com_senha)
                menu.add_command(label="Visualizar título", command=self.visualizar_despesa)
                menu.add_separator()
                for status in ["✓ Pago", "◎ Pendente", "⚠ Atrasado", "✗ Cancelado"]:
                    menu.add_command(label=status, command=lambda s=status: self._mudar_status_despesa(s))

            menu.post(event.x_root, event.y_root)

    def excluir_logico(self):
        item = self.tree.selection()
        if not item: return
        id_banco = item[0]
        
        if messagebox.askyesno("Confirmar", "Deseja realmente desativar este registro?", parent=self.root):
            if self.modo_atual == "clientes":
                database.atualizar_cliente(id_banco, status_cliente='Inativo')
                self.exibir_clientes()

            elif self.modo_atual == "produtos":
                database.atualizar_produto(id_banco, status_item='Indisponível')
                self.exibir_produtos()

    def quitar_selecionado(self):
        item = self.tree.selection()
        if not item: return
        if not messagebox.askyesno("Confirmar", "Deseja quitar este lançamento financeiro?", parent=self.root):
            return
        id_banco = item[0]
        database.quitar_titulo_financeiro(id_banco, "Dinheiro")
        self.exibir_financeiro()
    
    def filtrar_busca(self):
        """Filtra a vista atual por texto; usa pilha para restaurar ao apagar."""
        termo = self.ent_busca.get().lower()
        if termo == self.placeholder_busca.lower():
            termo = ""
        if not self._cache_lista:
            self._atualizar_cache_lista()
        base = self._lista_exibida if self._lista_exibida else self._cache_lista

        if not termo:
            if self._pilha_vistas:
                restaurar = self._pilha_vistas.pop()
                self._renderizar_cache(restaurar)
            else:
                self._renderizar_cache(self._cache_lista)
            self._termo_busca_anterior = ""
            return

        if not self._termo_busca_anterior and termo:
            self._pilha_vistas.append(list(base))

        filtrado = [
            (iid, v) for iid, v in base
            if any(termo in str(c).lower() for c in v)
        ]
        self._renderizar_cache(filtrado)
        self._termo_busca_anterior = termo

    # --- Funções do menu de contexto ---
    # Cada função de mudança de status agora inclui uma confirmação e, no caso das despesas, uma lógica específica para lidar com a data de pagamento.
    def abrir_financeiro_venda(self):
        item = self.tree.selection()
        if not item:
            return
        if not ui_utils.solicitar_senha_fluxo(self.root):
            return
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
        if not item:
            return
        if not ui_utils.solicitar_senha_fluxo(self.root):
            return

        id_banco = item[0]
        data_pagamento = None

        novo_status = ui_utils.normalizar_status_menu(novo_status, ui_utils.STATUS_MENU_FINANCEIRO)

        if novo_status == "Pago":
            # Busca a data de pagamento atual no banco de dados
            with database.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT data_pagamento FROM financeiro WHERE id = ?", (id_banco,))
                resultado = cursor.fetchone()
                data_existente = resultado[0] if resultado else None

            hoje = datetime.now().strftime("%Y-%m-%d")

            # Para status pago, registra a data atual se ainda não existir ou se confirmar alteração
            if data_existente:
                data_formatada = self.formatar_data_exibicao(data_existente)
                pergunta = (
                    f"Este registro já foi pago em {data_formatada}.\n"
                    f"Deseja alterar a data do pagamento para hoje ({ui_utils.formatar_data_exibicao(datetime.now().strftime('%Y-%m-%d'))})?"
                )
                if messagebox.askyesno("Alterar Data de Pagamento", pergunta, parent=self.root):
                    data_pagamento = hoje
                else:
                    data_pagamento = data_existente
            else:
                data_pagamento = hoje
        else:
            data_pagamento = None

        if messagebox.askyesno("Confirmar", f"Deseja realmente alterar o status do registro para '{novo_status}'?", parent=self.root):
            with database.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE financeiro SET status = ?, data_pagamento = ? WHERE id = ?",
                    (novo_status, data_pagamento, id_banco)
                )
                conn.commit()

            self.exibir_financeiro()

    def _mudar_status_venda(self, novo_status):
        item = self.tree.selection()
        st = ui_utils.normalizar_status_menu(novo_status, ui_utils.STATUS_MENU_VENDA)
        if not item:
            return
        if st == "Cancelada":
            if messagebox.askyesno("Confirmar", "Estornar esta venda e devolver estoque?"):
                ok, msg = database.cancelar_venda(item[0])
                if ok:
                    messagebox.showinfo("Sucesso", msg)
                    self.exibir_vendas()
                else:
                    messagebox.showerror("Erro", msg)
            return
        if st == config.STATUS_VENDA_FINALIZADA:
            messagebox.showinfo(
                "Vendas",
                "Para finalizar a venda, registre o pagamento em Gerenciar Receitas.\n"
                "O estoque só é baixado após a confirmação do pagamento.",
                parent=self.root,
            )
            return
        if messagebox.askyesno("Confirmar", f"Mudar status da venda para {st}?"):
            with database.conectar() as conn:
                conn.execute("UPDATE vendas SET status_venda = ? WHERE id = ?", (st, item[0]))
                conn.commit()
            self.exibir_vendas()
  
    # --- Função de edição específica para vendas, que abre a janela de cadastro de vendas já preenchida com os dados da venda selecionada ---
    def editar_venda(self):
        item = self.tree.selection()
        if not item:
            return
        from cadastro_vendas import JanelaCadastroVendas
        v = database.obter_venda_por_id(item[0])
        if v:
            dados_venda = {'id': v[0], 'desconto': v[6], 'forma': v[8], 'parcelas': v[9]}
            cliente_selecionado = (v[1], v[2], v[3])
            JanelaCadastroVendas(self.root, cliente_selecionado=cliente_selecionado, dados_venda=dados_venda)
            self.exibir_vendas()
  
    def editar_despesa(self):
        item = self.tree.selection()
        if not item: return
        if not messagebox.askyesno("Confirmar", "Deseja editar este lançamento financeiro?", parent=self.root):
            return
        id_banco = item[0]
        
        from gerenciar_despesas import JanelaGerenciarDespesas
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM financeiro WHERE id=?", (id_banco,))
            dados = cursor.fetchone()
            if dados:
                JanelaGerenciarDespesas(self.root, dados_despesa=dados)
                self.exibir_financeiro()
    
    # --- Função de visualização detalhada para vendas, que abre uma janela mostrando um resumo completo da venda selecionada, incluindo itens, cliente, forma de pagamento e status ---
    def visualizar_venda(self):
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
        janela.title("Alê Sapatilhas - Formulario da Venda")
        janela.configure(bg=self.bg_fundo)
        janela.transient(self.root)
        janela.grab_set()
        ui_utils.calcular_dimensoes_janela(janela, largura_desejada=450, altura_desejada=690)
        janela.resizable(True, True)
        
        main_frame = tk.Frame(janela, bg=self.bg_fundo, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(main_frame, text="🧾 DETALHES DA VENDA", bg=self.bg_fundo, fg=self.cor_destaque, font=("Arial Black", 12, "bold"), anchor="center").pack(fill="x", pady=(0, 15))
        
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
        
        info_frame = tk.Frame(main_frame, bg=self.bg_card, relief="solid", borderwidth=1, padx=10, pady=10)
        info_frame.pack(fill="both", expand=True, pady=(0, 15))

        txt_info = tk.Text(info_frame, bg=self.bg_card, fg=self.cor_texto, font=("Arial Black", 10), wrap="word", bd=0, highlightthickness=0)
        txt_info.insert("1.0", info_text.strip())
        txt_info.tag_configure("center", justify="center")
        txt_info.tag_add("center", "1.0", "end")
        txt_info.configure(state="disabled")
        txt_info.pack(fill="both", expand=True, side="left")

        scroll = tk.Scrollbar(info_frame, command=txt_info.yview)
        scroll.pack(side="right", fill="y")
        txt_info.configure(yscrollcommand=scroll.set)

        tk.Button(main_frame, text="FECHAR JANELA", bg=self.cor_destaque, fg="white", font=("Arial Black", 10), command=janela.destroy).pack(pady=(10, 0))
    
    def visualizar_cliente(self):
        item = self.tree.selection()
        if not item: return
        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tipo, nome, cpf, telefone, email, aniversario, tamanho_calcado, endereco_completo, bairro, cidade, cep, observacao, limite_credito, status_cliente FROM clientes WHERE id = ?", (item[0],))
            dados = cursor.fetchone()
        if not dados: return
        
        janela = tk.Toplevel(self.root)
        janela.title("Alê Sapatilhas - Formulario do Cliente")
        janela.configure(bg=self.bg_fundo)
        ui_utils.calcular_dimensoes_janela(janela, largura_desejada=450, altura_desejada=550)
        janela.resizable(True, True)

        frame = tk.Frame(janela, bg=self.bg_fundo, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        
        info_text = f"""
Tipo: {dados[0]}
Nome: {dados[1]}
CPF: {dados[2] or 'N/A'}
Telefone: {dados[3] or 'N/A'}
Email: {dados[4] or 'N/A'}
Aniversário: {dados[5] or 'N/A'}
Tamanho Calçado: {dados[6] or 'N/A'}
Endereço: {dados[7] or 'N/A'}
Bairro: {dados[8] or 'N/A'}
Cidade: {dados[9] or 'N/A'}
CEP: {dados[10] or 'N/A'}
Observação: {dados[11] or 'N/A'}
Limite de Crédito: R$ {float(dados[12] or 0):.2f}
Status: {dados[13]}
        """

        tk.Label(frame, text="👤 DETALHES DO CLIENTE", bg=self.bg_fundo, fg=self.cor_destaque, font=("Arial Black", 12, "bold"), anchor="center").pack(fill="x", pady=(0, 20))
        info_frame = tk.Frame(frame, bg=self.bg_card, relief="solid", borderwidth=1, padx=10, pady=10)
        info_frame.pack(fill="both", expand=True)
        tk.Label(info_frame, text=info_text.strip(), bg=self.bg_card, fg=self.cor_texto, font=("Arial Black", 10), justify="center", anchor="center", wraplength=460).pack(fill="both", expand=True)
        tk.Button(frame, text="FECHAR JANELA", bg=self.cor_destaque, fg="white", font=("Arial Black", 10), command=janela.destroy).pack(pady=10)
    
    
    def visualizar_despesa(self):
        item = self.tree.selection()
        if not item: return
        id_banco = item[0]

        with database.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tipo, entidade_nome, descricao, valor, parcelas_atual, total_parcelas,
                       data_vencimento, data_pagamento, forma_pagamento, categoria, status, recorrencia
                FROM financeiro WHERE id = ?
            """, (id_banco,))
            dados = cursor.fetchone()

        if not dados:
            messagebox.showerror("Erro", "Registro financeiro não encontrado.", parent=self.root)
            return

        tipo, entidade_nome, descricao, valor, parcela_atual, total_parcelas, data_vencimento, data_pagamento, forma_pagamento, categoria, status, recorrencia = dados
        
        # Determinar se é receita ou despesa para ajustar labels
        if tipo == "Receita":
            titulo = "💰 DETALHES DA RECEITA"
            entidade_label = "Cliente"
        else:
            titulo = "💰 DETALHES DA DESPESA"
            entidade_label = "Fornecedor"

        janela = tk.Toplevel(self.root)
        janela.title(f"Alê Sapatilhas - Formulario da {tipo}")
        janela.configure(bg=self.bg_fundo)
        janela.transient(self.root)
        janela.grab_set()
        ui_utils.calcular_dimensoes_janela(janela, largura_desejada=450, altura_desejada=550)
        janela.resizable(True, True)

        frame = tk.Frame(janela, bg=self.bg_fundo, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        info_text = f"""
{entidade_label}: {entidade_nome}
Descrição: {descricao}
Valor: R$ {valor:.2f}
Parcela: {parcela_atual} de {total_parcelas}
     Vencimento: {ui_utils.formatar_data_exibicao(data_vencimento) if data_vencimento else 'N/A'}
     Data de Pagamento: {ui_utils.formatar_data_exibicao(data_pagamento) if data_pagamento else 'N/A'}
Forma de Pagamento: {forma_pagamento or 'N/A'}
Categoria: {categoria or 'N/A'}
Status: {status}
Recorrência: {recorrencia or 'Não Recorrente'}
        """

        tk.Label(frame, text=titulo, bg=self.bg_fundo, fg=self.cor_destaque, font=("Arial Black", 12, "bold"), anchor="center").pack(fill="x", pady=(0, 20))
        info_frame = tk.Frame(frame, bg=self.bg_card, relief="solid", borderwidth=1, padx=10, pady=10)
        info_frame.pack(fill="both", expand=True)
        tk.Label(info_frame, text=info_text.strip(), bg=self.bg_card, fg=self.cor_texto, font=("Arial Black", 10), justify="center", anchor="center", wraplength=460).pack(fill="both", expand=True)
        tk.Button(frame, text="FECHAR JANELA", bg=self.cor_destaque, fg="white", font=("Arial Black", 10), command=janela.destroy).pack(pady=10)

    def visualizar_item(self):
        """Exibe ficha do produto (centralizado no shell principal)."""
        item = self.tree.selection()
        if not item:
            return
        with database.conectar() as conn:
            dados = conn.execute("SELECT * FROM produtos WHERE id = ?", (item[0],)).fetchone()
        if not dados:
            return

        janela = tk.Toplevel(self.root)
        janela.title("Alê Sapatilhas - Formulario do Produto")
        janela.configure(bg=self.bg_fundo)
        janela.transient(self.root)
        janela.grab_set()
        ui_utils.calcular_dimensoes_janela(janela, largura_desejada=450, altura_desejada=550)
        janela.resizable(True, True)

        frame = tk.Frame(janela, bg=self.bg_fundo, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tipo_ui = ui_utils.tipo_produto_para_ui(dados[2])
        info_text = f"""
SKU: {dados[1] or 'N/A'}
Tipo: {tipo_ui}
Produto: {dados[3]}
Cor: {dados[4]}
Tamanho: {dados[5]}
Preço de Custo: R$ {float(dados[6] or 0):.2f}
Preço de Venda: R$ {float(dados[7] or 0):.2f}
Quantidade em Estoque: {dados[8]}
Categoria: {dados[9] or 'N/A'}
Material: {dados[10] or 'N/A'}
Fornecedor: {dados[11] or 'N/A'}
Status: {dados[12]}
        """
        tk.Label(frame, text="📦 DETALHES DO PRODUTO", bg=self.bg_fundo, fg=self.cor_destaque,
                 font=("Arial Black", 12, "bold"), anchor="center").pack(fill="x", pady=(0, 15))
        info_frame = tk.Frame(frame, bg=self.bg_card, relief="solid", borderwidth=1, padx=10, pady=10)
        info_frame.pack(fill="both", expand=True, pady=(0, 15))
        tk.Label(info_frame, text=info_text.strip(), bg=self.bg_card, fg=self.cor_texto,
                 font=("Arial Black", 10), justify="center", anchor="center", wraplength=460).pack(fill="both", expand=True)
        tk.Button(frame, text="FECHAR JANELA", bg=self.cor_destaque, fg="white",
                  font=("Arial Black", 10), command=janela.destroy).pack()

    # --- Função para atualizar a lista exibida com base no modo atual, garantindo que as alterações sejam refletidas imediatamente após ações de edição ou status ---
  
    def atualizar_lista(self):
        """Recarrega a listagem conforme o modo_atual (botão Atualizar)."""
        if self.modo_atual == "clientes":
            self.exibir_clientes()
        elif self.modo_atual == "produtos":
            self.exibir_produtos()
        elif self.modo_atual == "financeiro":
            self.exibir_financeiro()
        elif self.modo_atual == "vendas":
            self.exibir_vendas()
        elif self.modo_atual == "dashboard":
            self.exibir_dashboard()
        elif self.modo_atual == "contas_receber":
            self.exibir_contas_a_receber()
        elif self.modo_atual == "contas_pagar":
            self.exibir_contas_a_pagar()


    def confirmar_saida(self):
        """Encerra o aplicativo após confirmação do usuário."""
        if messagebox.askyesno("Sair", "Deseja encerrar o sistema Ale Sapatilhas?"):
            self.root.destroy()

if __name__ == "__main__":
    # Garante schema antes de qualquer tela (padrão "migration on startup")
    database.criar_tabelas()
    root = tk.Tk()
    app = SistemaAleSapatilhas(root)
    root.mainloop()