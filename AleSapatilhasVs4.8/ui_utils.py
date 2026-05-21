"""
ui_utils.py — Camada de apresentação compartilhada (Design System leve).

Por que centralizar cores e estilos?
  - Consistência visual entre dezenas de telas Tkinter
  - Alteração de tema em um único arquivo
  - Separação entre "como aparece" (UI) e "o que faz" (database)

STATUS_MENU_*: mapeiam rótulos amigáveis do menu de contexto para valores
gravados no SQLite (constraints CHECK exigem texto exato).
"""

import calendar
import os
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from datetime import datetime, timedelta

import config
import database

# --- PALETA DE CORES PADRONIZADA ---
LARGURA_MODULO_PADRAO = 700

TIPOS_PRODUTO_UI = ("Calçado", "Vestuário")
TIPO_PRODUTO_UI_PARA_BD = {"Calçado": "Calçados", "Vestuário": "Confecções"}
TIPO_PRODUTO_BD_PARA_UI = {v: k for k, v in TIPO_PRODUTO_UI_PARA_BD.items()}

PALETA = {
    "bg_fundo": "#F1F5F9",
    "bg_card": "#FFFFFF",
    "cor_borda": "#8BA2BD",
    "cor_texto": "#0B1933",
    "cor_lbl": "#020C18",
    "cor_destaque": "#6366F1",
    "cor_btn_menu": "#1E293B",
    "cor_btn_sair": "#25324E",
    "cor_btn_acao1": "#425074",
    "cor_btn_acao2": "#6366F1",
    "cor_letra_botoes": "#FFFFFF",
    "cor_btn_acao": "#425074",
    "cor_hover_btn": "#6F7CA0",
    "cor_hover_field": "#484AD6",
}

def calcular_dimensoes_janela(root, largura_desejada=700, altura_desejada=850, maximizar=False):
    """
    Calcula e define as dimensões da janela respeitando:
    - Tamanho do monitor
    - Barra de tarefas do SO
    - Centralização na tela
    
    Args:
        root: Janela Tkinter
        largura_desejada: Largura desejada (padrão 700)
        altura_desejada: Altura desejada (padrão 850)
        maximizar: Se True, maximiza; se False, usa dimensões padrão
    """
    # Atualiza para capturar dimensões corretas
    root.update_idletasks()
    
    # Dimensões do monitor (aproximadamente)
    largura_tela = root.winfo_screenwidth()
    altura_tela = root.winfo_screenheight()
    
    if maximizar:
        # Maximiza deixando espaço para barra de tarefas e bordas da janela
        root.geometry(f"{largura_tela}x{altura_tela - 70}+0+0")
    else:
        # Usa dimensões padrão
        # Verifica se o tamanho desejado cabe na tela
        largura_final = min(largura_desejada, largura_tela - 20)
        altura_final = min(altura_desejada, altura_tela - 100)
        
        # Centraliza a janela
        x = (largura_tela - largura_final) // 2
        y = (altura_tela - altura_final) // 2
        
        root.geometry(f"{largura_final}x{altura_final}+{x}+{y}")

def get_paleta():
    """Retorna a paleta de cores padronizada (cópia para painel de temas futuro)."""
    p = PALETA.copy()
    p.setdefault("cor_btn_acao1", p.get("cor_btn_acao", "#425074"))
    p.setdefault("cor_btn_acao2", p.get("cor_destaque", "#6366F1"))
    p.setdefault("cor_letra_botoes", "#FFFFFF")
    return p


def cor_botao(paleta, estilo):
    """Resolve cor do botão: acao1 | acao2 | sair."""
    mapa = {
        "acao1": paleta.get("cor_btn_acao1", paleta.get("cor_btn_acao")),
        "acao2": paleta.get("cor_btn_acao2", paleta.get("cor_destaque")),
        "sair": paleta.get("cor_btn_sair"),
    }
    return mapa.get(estilo, mapa["acao1"])

# Rótulos do menu de contexto → valores aceitos no banco (CHECK constraints)
STATUS_MENU_CLIENTE = {
    "✓ Ativo": "Ativo", "★ VIP": "Vip", "⛔ Bloqueado": "Bloqueado", "✗ Inativo": "Inativo",
}
STATUS_MENU_PRODUTO = {
    "✓ Disponível": "Disponível", "✗ Indisponível": "Indisponível", "★ Promocional": "Promocional",
}
STATUS_MENU_FINANCEIRO = {
    "◎ Pendente": "Pendente", "✓ Pago": "Pago", "⚠ Atrasado": "Atrasado", "✗ Cancelado": "Cancelado",
}
STATUS_MENU_VENDA = {
    "✓ Finalizada": "Finalizada", "⏳ Pendente": "Pendente", "✗ Cancelada": "Cancelada",
}

def normalizar_status_menu(rotulo, mapa):
    """Converte rótulo do menu para valor persistível."""
    if rotulo in mapa:
        return mapa[rotulo]
    for k, v in mapa.items():
        if v == rotulo or rotulo.endswith(v):
            return v
    return rotulo

def criar_style_padrao(root):
    """Configura estilos padrão para ttk.Combobox e ttk.Treeview"""
    from tkinter import ttk
    
    style = ttk.Style()
    style.theme_use('clam')
    
    # Combobox
    style.configure("TCombobox", 
                   fieldbackground=PALETA["bg_card"],
                   background=PALETA["bg_card"],
                   arrowcolor=PALETA["cor_btn_acao"],
                   bordercolor=PALETA["cor_borda"])
    
    # Treeview
    style.configure("Treeview",
                   background=PALETA["bg_card"],
                   foreground=PALETA["cor_texto"],
                   rowheight=22,
                   borderwidth=0,
                   font=("Segoe UI", 9))
    
    style.configure("Treeview.Heading",
                   font=("Segoe UI", 10, "bold"),
                   background=PALETA["bg_card"])
    
    style.map("Treeview",
             background=[('selected', PALETA["cor_destaque"])])
    
    return style


def confirmar(parent, titulo, mensagem):
    """Confirmação Sim/Não padronizada para ações destrutivas ou importantes."""
    return messagebox.askyesno(titulo, mensagem, parent=parent)


def solicitar_senha_fluxo(parent, titulo="Fluxo de Caixa"):
    """Exige senha padrão antes de baixar ou quitar títulos no fluxo de caixa."""
    senha = simpledialog.askstring(
        titulo,
        "Informe a senha para lançar recebimento/pagamento:",
        parent=parent,
        show="*",
    )
    if senha is None:
        return False
    if senha != config.obter_senha_fluxo_caixa():
        messagebox.showerror("Acesso negado", "Senha incorreta.", parent=parent)
        return False
    return True


class RastreadorAlteracoes:
    """Detecta alterações em formulários para confirmar saída apenas se houve edição."""

    def __init__(self, obter_snapshot):
        self._obter = obter_snapshot
        self._inicial = obter_snapshot()

    def marcar_limpo(self):
        self._inicial = self._obter()

    def alterado(self):
        return self._obter() != self._inicial


def confirmar_fechar_formulario(parent, rastreador, titulo="Fechar"):
    """Pergunta ao usuário somente se o formulário foi modificado."""
    if rastreador is None or not rastreador.alterado():
        return True
    return confirmar(parent, titulo, "Há alterações não salvas. Deseja fechar mesmo assim?")


def tipo_produto_para_bd(valor_ui):
    """Converte rótulo da UI (Calçado/Vestuário) para valor gravado no SQLite."""
    return TIPO_PRODUTO_UI_PARA_BD.get(valor_ui, valor_ui or "Calçados")


def tipo_produto_para_ui(valor_bd):
    """Converte valor do banco para exibição no formulário de produtos."""
    return TIPO_PRODUTO_BD_PARA_UI.get(valor_bd, "Calçado")


class MiniCalendario(tk.Toplevel):
    """Janela popup com calendário mensal para preencher um Entry com data DD/MM/AAAA."""

    DIAS_SEMANA = ("Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb")

    def __init__(self, master, entry_alvo, titulo="Selecionar data"):
        """Exibe o mês atual e grava a data escolhida em entry_alvo."""
        super().__init__(master)
        self.entry_alvo = entry_alvo
        self.title(titulo)
        self.configure(bg=PALETA["bg_fundo"])
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._hoje = datetime.now().date()
        self._coluna_hoje = (self._hoje.weekday() + 1) % 7
        self.ano = tk.IntVar(value=self._hoje.year)
        self.mes = tk.IntVar(value=self._hoje.month)

        topo = tk.Frame(self, bg=PALETA["bg_fundo"], padx=10, pady=8)
        topo.pack(fill="x")
        tk.Button(topo, text="◀", command=self._mes_anterior, width=3).pack(side="left")
        self.lbl_mes = tk.Label(topo, text="", font=("Segoe UI", 10, "bold"), bg=PALETA["bg_fundo"])
        self.lbl_mes.pack(side="left", expand=True)
        tk.Button(topo, text="▶", command=self._mes_proximo, width=3).pack(side="right")

        self.grid_dias = tk.Frame(self, bg=PALETA["bg_fundo"], padx=8, pady=4)
        self.grid_dias.pack()
        self._lbl_dias = []
        for i, d in enumerate(self.DIAS_SEMANA):
            destaque = i == self._coluna_hoje
            lbl = tk.Label(
                self.grid_dias, text=d, width=4,
                font=("Segoe UI", 8, "bold"),
                bg=PALETA["cor_destaque"] if destaque else PALETA["bg_fundo"],
                fg="white" if destaque else PALETA["cor_texto"],
            )
            lbl.grid(row=0, column=i, padx=1, pady=(0, 2))
            self._lbl_dias.append(lbl)

        self._desenhar_dias()
        calcular_dimensoes_janela(self, largura_desejada=300, altura_desejada=340)

    def _mes_anterior(self):
        m, a = self.mes.get(), self.ano.get()
        if m == 1:
            self.mes.set(12)
            self.ano.set(a - 1)
        else:
            self.mes.set(m - 1)
        self._desenhar_dias()

    def _mes_proximo(self):
        m, a = self.mes.get(), self.ano.get()
        if m == 12:
            self.mes.set(1)
            self.ano.set(a + 1)
        else:
            self.mes.set(m + 1)
        self._desenhar_dias()

    def _desenhar_dias(self):
        for w in self.grid_dias.winfo_children():
            if int(w.grid_info().get("row", 0)) > 0:
                w.destroy()
        mes, ano = self.mes.get(), self.ano.get()
        meses_pt = (
            "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        )
        self.lbl_mes.config(text=f"{meses_pt[mes]} / {ano}")
        linha, col = 1, 0
        semanas = calendar.Calendar(firstweekday=calendar.SUNDAY).monthdayscalendar(ano, mes)
        for semana in semanas:
            for dia in semana:
                if dia == 0:
                    col += 1
                    continue
                eh_hoje = (
                    ano == self._hoje.year and mes == self._hoje.month and dia == self._hoje.day
                )
                btn = tk.Button(
                    self.grid_dias, text=str(dia), width=4, relief="flat",
                    font=("Segoe UI", 9, "bold" if eh_hoje else "normal"),
                    bg=PALETA["cor_destaque"] if eh_hoje else PALETA["bg_card"],
                    fg="white" if eh_hoje else PALETA["cor_texto"],
                    activebackground=PALETA["cor_hover_btn"],
                    command=lambda d=dia: self._selecionar(d),
                )
                btn.grid(row=linha, column=col, padx=1, pady=1)
                col += 1
            linha += 1
            col = 0

    def _selecionar(self, dia):
        data = datetime(self.ano.get(), self.mes.get(), dia).strftime("%d/%m/%Y")
        self.entry_alvo.delete(0, tk.END)
        self.entry_alvo.insert(0, data)
        self.destroy()


def anexar_botao_calendario(parent, entry, row, column=1, sticky="e"):
    """Adiciona botão 📅 ao lado de um Entry para abrir o mini calendário."""
    btn = tk.Button(
        parent, text="📅", relief="flat", cursor="hand2", width=2,
        command=lambda: MiniCalendario(parent.winfo_toplevel(), entry),
    )
    btn.grid(row=row, column=column, sticky=sticky, padx=(0, 5))
    return btn


def texto_botao_salvar(rotulo, em_edicao):
    """Rótulo dual mode: Salvar X (novo) ou Atualizar X (edição)."""
    return f"Atualizar {rotulo}" if em_edicao else f"Salvar {rotulo}"


def anexar_botao_calculadora(parent, entry, row, column=0, sticky="e"):
    """Adiciona botão 🧮 ao lado de um Entry; OK envia o resultado para o campo."""
    btn = tk.Button(
        parent, text="🧮", relief="flat", cursor="hand2", width=2,
        command=lambda: abrir_calculadora(parent.winfo_toplevel(), entry),
    )
    btn.grid(row=row, column=column, sticky=sticky, padx=(0, 5))
    return btn


def configurar_entry_inteiro(entry, master, permitir_vazio=True):
    """Restringe Entry a dígitos (quantidades, parcelas, etc.)."""
    def _valido(proposto):
        if proposto == "":
            return permitir_vazio
        return proposto.isdigit()

    vcmd = (master.register(_valido), "%P")
    entry.config(validate="key", validatecommand=vcmd)


def aplicar_estilo_foco_entry(ent, paleta=None):
    """Hover e foco consistentes em campos Entry."""
    p = paleta or PALETA

    def on_enter(_e):
        if ent.focus_get() != ent:
            ent.config(highlightbackground=p["cor_hover_field"])
    def on_leave(_e):
        if ent.focus_get() != ent:
            ent.config(highlightbackground=p["cor_borda"])
    def on_focus_in(_e):
        ent.config(highlightbackground=p["cor_destaque"], highlightthickness=2)
    def on_focus_out(_e):
        ent.config(highlightbackground=p["cor_borda"], highlightthickness=1)

    ent.bind("<Enter>", on_enter)
    ent.bind("<Leave>", on_leave)
    ent.bind("<FocusIn>", on_focus_in)
    ent.bind("<FocusOut>", on_focus_out)


def criar_botao_rodape(parent, texto, comando, estilo="acao1", paleta=None):
    """Botão de rodapé: estilo em acao1, acao2 ou sair."""
    p = paleta or get_paleta()
    cor = cor_botao(p, estilo)
    fg = p.get("cor_letra_botoes", "#FFFFFF")
    btn = tk.Button(
        parent, text=texto, bg=cor, fg=fg, font=("Segoe UI", 10, "bold"),
        relief="flat", cursor="hand2", command=comando,
        activeforeground=fg,
    )
    btn._cor_base = cor
    btn._estilo = estilo

    def _on_enter(_e):
        btn.config(bg=p["cor_hover_btn"])

    def _on_leave(_e):
        btn.config(bg=btn._cor_base)

    btn.bind("<Enter>", _on_enter)
    btn.bind("<Leave>", _on_leave)
    return btn


def atualizar_cor_botao_rodape(btn, estilo="acao1", paleta=None):
    """Atualiza estilo/cor do botão de rodapé (dual mode Salvar/Atualizar)."""
    p = paleta or get_paleta()
    cor = cor_botao(p, estilo)
    btn._cor_base = cor
    btn._estilo = estilo
    btn.config(bg=cor)


def carregar_miniatura_foto(caminho, tamanho=(40, 40)):
    """Retorna PhotoImage redimensionada ou None se indisponível."""
    if not caminho or not os.path.exists(caminho):
        return None
    try:
        from PIL import Image, ImageTk
        img = Image.open(caminho)
        img.thumbnail(tamanho, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        try:
            return tk.PhotoImage(file=caminho)
        except Exception:
            return None


class _CalculadoraPadrao:
    """Calculadora estilo Windows/iOS: % sobre total em +/- e OK para campo alvo."""

    def __init__(self, master, entry_alvo=None):
        self.entry_alvo = entry_alvo
        self.win = tk.Toplevel(master)
        self.win.title("Calculadora")
        self.win.configure(bg=PALETA["bg_fundo"])
        self.win.resizable(False, False)
        self.win.transient(master)

        self.display_var = tk.StringVar(value="0")
        self._acc = None
        self._op = None
        self._nova_entrada = True

        painel = tk.Frame(self.win, bg=PALETA["bg_card"], padx=8, pady=8)
        painel.pack(fill="both", expand=True, padx=10, pady=10)

        self.display = tk.Entry(
            painel, textvariable=self.display_var, font=("Segoe UI", 22), justify="right",
            relief="flat", bg=PALETA["bg_card"], fg=PALETA["cor_texto"],
            readonlybackground=PALETA["bg_card"], state="readonly",
        )
        self.display.pack(fill="x", ipady=10, pady=(0, 10))

        grid = tk.Frame(painel, bg=PALETA["bg_card"])
        grid.pack(fill="both", expand=True)
        for c in range(4):
            grid.columnconfigure(c, weight=1, uniform="calc")
        for r in range(5):
            grid.rowconfigure(r, weight=1, uniform="calc")

        layout = [
            ("CE", "func"), ("C", "func"), ("⌫", "func"), ("/", "op"),
            ("7", "num"), ("8", "num"), ("9", "num"), ("*", "op"),
            ("4", "num"), ("5", "num"), ("6", "num"), ("-", "op"),
            ("1", "num"), ("2", "num"), ("3", "num"), ("+", "op"),
            ("0", "num"), (".", "num"), ("%", "func"), ("=", "eq"),
        ]
        for i, (txt, tipo) in enumerate(layout):
            bg = PALETA["cor_btn_acao1"] if tipo in ("op", "eq") else PALETA["bg_fundo"]
            fg = PALETA["cor_letra_botoes"] if tipo in ("op", "eq") else PALETA["cor_texto"]
            if tipo == "func":
                bg, fg = PALETA["cor_btn_acao2"], PALETA["cor_letra_botoes"]
            tk.Button(
                grid, text=txt, command=lambda t=txt: self._pressionar(t),
                font=("Segoe UI", 14, "bold"), bg=bg, fg=fg, relief="flat",
                cursor="hand2", activebackground=PALETA["cor_hover_btn"],
            ).grid(row=i // 4, column=i % 4, padx=3, pady=3, sticky="nsew")

        if entry_alvo is not None:
            rodape = tk.Frame(self.win, bg=PALETA["bg_fundo"])
            rodape.pack(fill="x", padx=10, pady=(0, 10))
            criar_botao_rodape(rodape, "OK", self._confirmar_ok, "acao2").pack(fill="x", ipady=8)

        calcular_dimensoes_janela(self.win, largura_desejada=300, altura_desejada=440 if entry_alvo else 400)

    def _valor_display(self):
        try:
            return float(self.display_var.get().replace(",", "."))
        except ValueError:
            return 0.0

    def _set_display(self, valor):
        if isinstance(valor, str):
            self.display_var.set(valor or "0")
            return
        if isinstance(valor, float) and abs(valor - round(valor)) < 1e-9:
            self.display_var.set(str(int(round(valor))))
            return
        texto = f"{valor:.10g}".replace(".", ",")
        self.display_var.set(texto)

    def _pressionar(self, tecla):
        if tecla == "CE":
            self._set_display(0)
            self._nova_entrada = True
            return
        if tecla == "C":
            self._acc = None
            self._op = None
            self._set_display(0)
            self._nova_entrada = True
            return
        if tecla == "⌫":
            cur = self.display_var.get()
            if self._nova_entrada or cur in ("0", ""):
                self._set_display(0)
            else:
                self._set_display(cur[:-1] if len(cur) > 1 else "0")
            self._nova_entrada = False
            return
        if tecla == "%":
            self._aplicar_porcentagem()
            return
        if tecla in ("+", "-", "*", "/"):
            if self._op and not self._nova_entrada:
                self._calcular()
            self._acc = self._valor_display()
            self._op = tecla
            self._nova_entrada = True
            return
        if tecla == "=":
            self._calcular()
            self._op = None
            self._acc = None
            self._nova_entrada = True
            return
        if tecla == ".":
            cur = "" if self._nova_entrada else self.display_var.get()
            if "," not in cur and "." not in cur:
                self.display_var.set((cur or "0") + ",")
            self._nova_entrada = False
            return
        if tecla.isdigit():
            if self._nova_entrada or self.display_var.get() == "0":
                self.display_var.set(tecla)
                self._nova_entrada = False
            else:
                self.display_var.set(self.display_var.get() + tecla)

    def _aplicar_porcentagem(self):
        """% estilo calculadora comercial: 500 + 10% => 50; fora de +/- divide por 100."""
        atual = self._valor_display()
        if self._op in ("+", "-") and self._acc is not None:
            self._set_display(self._acc * atual / 100.0)
        else:
            self._set_display(atual / 100.0)
        self._nova_entrada = True

    def _calcular(self):
        if self._op is None or self._acc is None:
            return
        b = self._valor_display()
        a = self._acc
        try:
            if self._op == "+":
                self._set_display(a + b)
            elif self._op == "-":
                self._set_display(a - b)
            elif self._op == "*":
                self._set_display(a * b)
            elif self._op == "/":
                self._set_display(a / b if b else 0)
            self._acc = self._valor_display()
        except Exception:
            self.display_var.set("Erro")

    def _confirmar_ok(self):
        if self.entry_alvo is not None:
            try:
                v = self._valor_display()
                self.entry_alvo.delete(0, tk.END)
                self.entry_alvo.insert(0, f"{v:.2f}")
                self.entry_alvo.event_generate("<KeyRelease>")
            except Exception:
                pass
        self.win.destroy()


def abrir_calculadora(parent, entry_alvo=None):
    """Abre calculadora em layout padrão; OK envia valor ao entry_alvo."""
    _CalculadoraPadrao(parent, entry_alvo)


def abrir_calendario_info(parent):
    """Exibe calendário do mês atual (utilidade informativa)."""
    hoje = datetime.now()
    texto = calendar.month(hoje.year, hoje.month)
    messagebox.showinfo(
        "Calendário",
        f"Hoje: {hoje.strftime('%d/%m/%Y')}\n\n{texto}",
        parent=parent,
    )


def abrir_anotacoes(parent):
    """Anotações no banco: listar (alfabético), buscar por título e salvar."""
    win = tk.Toplevel(parent)
    win.title("Alê Sapatilhas — Anotações")
    win.configure(bg=PALETA["bg_fundo"])
    win.transient(parent)
    calcular_dimensoes_janela(win, largura_desejada=720, altura_desejada=680)

    moldura = tk.LabelFrame(
        win, text=" Anotações ", bg=PALETA["bg_fundo"], fg=PALETA["cor_destaque"],
        font=("Segoe UI", 10, "bold"), relief="solid", borderwidth=1, padx=12, pady=10,
    )
    moldura.pack(fill="both", expand=True, padx=14, pady=14)
    moldura.columnconfigure(1, weight=1)
    moldura.rowconfigure(2, weight=1)

    tk.Label(moldura, text="Notas salvas", bg=PALETA["bg_fundo"], font=("Segoe UI", 9, "bold")).grid(
        row=0, column=0, sticky="w", pady=(0, 4),
    )
    lista_frame = tk.Frame(moldura, bg=PALETA["bg_fundo"], highlightthickness=1,
                           highlightbackground=PALETA["cor_borda"])
    lista_frame.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
    scroll = ttk.Scrollbar(lista_frame, orient="vertical")
    lst = tk.Listbox(
        lista_frame, font=("Segoe UI", 9), height=18, width=26,
        yscrollcommand=scroll.set, relief="flat", bg=PALETA["bg_card"],
        highlightthickness=0,
    )
    scroll.config(command=lst.yview)
    scroll.pack(side="right", fill="y")
    lst.pack(side="left", fill="both", expand=True, padx=4, pady=4)

    direita = tk.Frame(moldura, bg=PALETA["bg_fundo"])
    direita.grid(row=0, column=1, rowspan=3, sticky="nsew")
    direita.columnconfigure(0, weight=1)
    direita.rowconfigure(3, weight=1)

    barra_titulo = tk.Frame(direita, bg=PALETA["bg_fundo"])
    barra_titulo.grid(row=0, column=0, sticky="ew")
    barra_titulo.columnconfigure(0, weight=1)

    tk.Label(barra_titulo, text="Título da nota", bg=PALETA["bg_fundo"], font=("Segoe UI", 9, "bold")).grid(
        row=0, column=0, sticky="w",
    )
    ent_nome = tk.Entry(
        barra_titulo, font=("Segoe UI", 10), relief="flat", bg=PALETA["bg_card"],
        highlightthickness=1, highlightbackground=PALETA["cor_borda"],
    )
    ent_nome.grid(row=1, column=0, sticky="ew", pady=(2, 0), ipady=4)
    ent_nome.insert(0, datetime.now().strftime("nota_%Y%m%d_%H%M%S"))

    tk.Label(barra_titulo, text="Buscar", bg=PALETA["bg_fundo"], font=("Segoe UI", 9, "bold")).grid(
        row=0, column=1, sticky="w", padx=(10, 0),
    )
    ent_buscar = tk.Entry(
        barra_titulo, font=("Segoe UI", 10), width=18, relief="flat", bg=PALETA["bg_card"],
        highlightthickness=1, highlightbackground=PALETA["cor_borda"],
    )
    ent_buscar.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(2, 0), ipady=4)

    tk.Label(direita, text="Conteúdo", bg=PALETA["bg_fundo"], font=("Segoe UI", 9, "bold")).grid(
        row=2, column=0, sticky="w", pady=(8, 2),
    )
    txt = tk.Text(
        direita, font=("Segoe UI", 10), wrap="word", relief="flat", bg=PALETA["bg_card"],
        highlightthickness=1, highlightbackground=PALETA["cor_borda"],
    )
    txt.grid(row=3, column=0, sticky="nsew")

    estado = {"anotacao_id": None}

    def preencher_form(row):
        if not row:
            return
        estado["anotacao_id"] = row[0]
        ent_nome.delete(0, tk.END)
        ent_nome.insert(0, row[1])
        txt.delete("1.0", tk.END)
        txt.insert("1.0", row[2] or "")

    def atualizar_lista(registros=None):
        lst.delete(0, tk.END)
        dados = registros if registros is not None else database.listar_anotacoes(ordem_alfabetica=True)
        for row in dados:
            lst.insert(tk.END, row[1])

    def listar_todas():
        ent_buscar.delete(0, tk.END)
        atualizar_lista()
        messagebox.showinfo("Anotações", f"{lst.size()} nota(s) carregada(s) do banco.", parent=win)

    def buscar_por_titulo():
        termo = ent_buscar.get().strip()
        if not termo:
            listar_todas()
            return
        rows = database.buscar_anotacao_por_titulo(termo)
        atualizar_lista(rows)
        if not rows:
            messagebox.showinfo("Anotações", "Nenhuma nota encontrada.", parent=win)

    def carregar_selecionada():
        sel = lst.curselection()
        if not sel:
            termo = ent_buscar.get().strip() or ent_nome.get().strip()
            if termo:
                rows = database.buscar_anotacao_por_titulo(termo)
                if rows:
                    preencher_form(rows[0])
            return
        titulo = lst.get(sel[0])
        rows = database.buscar_anotacao_por_titulo(titulo)
        if rows:
            preencher_form(rows[0])

    def salvar_nota():
        ok, msg = database.salvar_anotacao(
            ent_nome.get().strip(),
            txt.get("1.0", tk.END).strip(),
            estado["anotacao_id"],
        )
        if ok:
            if not estado["anotacao_id"]:
                rows = database.buscar_anotacao_por_titulo(ent_nome.get().strip())
                if rows:
                    estado["anotacao_id"] = rows[0][0]
            listar_todas()
            messagebox.showinfo("Anotações", msg, parent=win)
        else:
            messagebox.showwarning("Anotações", msg, parent=win)

    def excluir_nota():
        if not estado["anotacao_id"]:
            carregar_selecionada()
        if not estado["anotacao_id"]:
            messagebox.showwarning("Anotações", "Selecione uma nota para excluir.", parent=win)
            return
        if not confirmar(win, "Excluir nota", "Excluir esta nota permanentemente?"):
            return
        database.excluir_anotacao(estado["anotacao_id"])
        estado["anotacao_id"] = None
        ent_nome.delete(0, tk.END)
        ent_nome.insert(0, datetime.now().strftime("nota_%Y%m%d_%H%M%S"))
        txt.delete("1.0", tk.END)
        listar_todas()
        messagebox.showinfo("Anotações", "Nota excluída.", parent=win)

    lst.bind("<Double-1>", lambda _e: carregar_selecionada())
    ent_buscar.bind("<Return>", lambda _e: buscar_por_titulo())

    rodape = tk.Frame(moldura, bg=PALETA["bg_fundo"])
    rodape.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    rodape.columnconfigure((0, 1, 2), weight=1, uniform="notas_btn")
    criar_botao_rodape(rodape, "Salvar Nota", salvar_nota, "acao1").grid(row=0, column=0, sticky="ew", padx=(0, 4), ipady=6)
    criar_botao_rodape(rodape, "Listar", listar_todas, "acao2").grid(row=0, column=1, sticky="ew", padx=4, ipady=6)
    criar_botao_rodape(rodape, "Excluir Nota", excluir_nota, "sair").grid(row=0, column=2, sticky="ew", padx=(4, 0), ipady=6)

    listar_todas()


def abrir_configuracoes(parent):
    """Configurações locais: opções e fluxo de troca de senha (Segurança)."""
    win = tk.Toplevel(parent)
    win.title("Configurações")
    win.configure(bg=PALETA["bg_fundo"])
    win.transient(parent)
    calcular_dimensoes_janela(win, largura_desejada=560, altura_desejada=460)
    win.resizable(True, True)

    topo = tk.Frame(win, bg=PALETA["bg_fundo"], padx=12, pady=8)
    topo.pack(fill="x")

    opcao_var = tk.StringVar(value="Opção 1")
    opcoes = ["Opção 1", "Opção 2", "Opção 3", "Opção 4", "Segurança"]
    tk.Label(topo, text="Seção:", bg=PALETA["bg_fundo"], font=("Segoe UI", 9, "bold")).pack(side="left")
    tk.OptionMenu(topo, opcao_var, *opcoes).pack(side="left", padx=(8, 0))

    conteudo = tk.Frame(win, bg=PALETA["bg_fundo"], padx=16, pady=8)
    conteudo.pack(fill="both", expand=True)

    aviso_base = (
        "A senha fica em secrets.local.json (não vai para o Git).\n"
        f"Arquivo: {config.SECRETS_PATH}"
    )

    def limpar_conteudo():
        for c in conteudo.winfo_children():
            c.destroy()

    def mostrar_geral():
        limpar_conteudo()
        aviso = aviso_base
        if not config.secrets_configurado():
            aviso += "\n\n⚠ Usando senha padrão de instalação. Defina uma senha na seção Segurança."
        tk.Label(conteudo, text=aviso, bg=PALETA["bg_fundo"], font=("Segoe UI", 9),
                 justify="left", wraplength=420).pack(anchor="w")

    def mostrar_seguranca():
        limpar_conteudo()
        tk.Label(conteudo, text="Segurança — Trocar senha do fluxo de caixa", bg=PALETA["bg_fundo"],
                 fg=PALETA["cor_destaque"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))

        tk.Label(conteudo, text=aviso_base, bg=PALETA["bg_fundo"], font=("Segoe UI", 9),
                 justify="left", wraplength=420).pack(anchor="w", pady=(0, 8))

        lbl_cur = tk.Label(conteudo, text="Senha atual", bg=PALETA["bg_fundo"], font=("Segoe UI", 9))
        lbl_cur.pack(anchor="w")
        ent_cur = tk.Entry(conteudo, font=("Segoe UI", 10), show="*", relief="flat",
                           highlightthickness=1, highlightbackground=PALETA["cor_borda"])
        ent_cur.pack(fill="x", ipady=4, pady=(4, 8))

        lbl_new = tk.Label(conteudo, text="Nova senha", bg=PALETA["bg_fundo"], font=("Segoe UI", 9))
        lbl_new.pack(anchor="w")
        ent_new = tk.Entry(conteudo, font=("Segoe UI", 10), show="*", relief="flat",
                           highlightthickness=1, highlightbackground=PALETA["cor_borda"])
        ent_new.pack(fill="x", ipady=4, pady=(4, 8))

        lbl_conf = tk.Label(conteudo, text="Confirmar nova senha", bg=PALETA["bg_fundo"], font=("Segoe UI", 9))
        lbl_conf.pack(anchor="w")
        ent_conf = tk.Entry(conteudo, font=("Segoe UI", 10), show="*", relief="flat",
                            highlightthickness=1, highlightbackground=PALETA["cor_borda"])
        ent_conf.pack(fill="x", ipady=4, pady=(4, 12))

        def trocar_senha():
            atual = (ent_cur.get() or "").strip()
            nova = (ent_new.get() or "").strip()
            conf = (ent_conf.get() or "").strip()
            if not atual:
                messagebox.showwarning("Segurança", "Informe a senha atual.", parent=win)
                return
            if atual != config.obter_senha_fluxo_caixa():
                messagebox.showerror("Segurança", "Senha atual incorreta.", parent=win)
                return
            if not nova:
                messagebox.showwarning("Segurança", "Informe a nova senha.", parent=win)
                return
            if nova != conf:
                messagebox.showwarning("Segurança", "Nova senha e confirmação não conferem.", parent=win)
                return
            ok, msg = config.salvar_senha_fluxo_caixa(nova)
            if ok:
                messagebox.showinfo("Segurança", msg, parent=win)
                win.destroy()
            else:
                messagebox.showerror("Segurança", msg, parent=win)

        rodape_local = tk.Frame(conteudo, bg=PALETA["bg_fundo"])
        rodape_local.pack(fill="x")
        criar_botao_rodape(rodape_local, "Trocar senha", trocar_senha, "acao1").pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 4))
        criar_botao_rodape(rodape_local, "Cancelar", win.destroy, "sair").pack(side="left", fill="x", expand=True, ipady=6)

    def on_opcao_change(*_a):
        sel = opcao_var.get()
        if sel == "Segurança":
            mostrar_seguranca()
        else:
            mostrar_geral()

    opcao_var.trace_add("write", on_opcao_change)
    mostrar_geral()

    rodape = tk.Frame(win, bg=PALETA["bg_fundo"], padx=16, pady=8)
    rodape.pack(fill="x")
    criar_botao_rodape(rodape, "Fechar", win.destroy, "sair").pack(side="left", fill="x", expand=True, ipady=6)


def filtro_data_periodo(opcao, data_str):
    """Retorna True se data_str (DD/MM/YYYY ou YYYY-MM-DD) está no período."""
    if not data_str:
        return False
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(str(data_str), fmt).date()
            break
        except ValueError:
            dt = None
    if not dt:
        return False
    hoje = datetime.now().date()
    if opcao == "Dia":
        return dt == hoje
    if opcao == "Semana":
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
        return inicio <= dt <= fim
    if opcao == "Mês":
        return dt.year == hoje.year and dt.month == hoje.month
    return True


def formatar_data_exibicao(data_str):
    """Normaliza e formata data para exibição DD/MM/YYYY.

    Aceita strings em YYYY-MM-DD ou DD/MM/YYYY.
    """
    if not data_str:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(data_str), fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return str(data_str)
