"""
cadastro_clientes.py — Cadastro unificado de contatos (CRM).

Um único cadastro atende Cliente e Fornecedor (campo tipo), padrão ERP:
  - Vendas e receitas → tipo Cliente
  - Despesas e produtos → tipo Fornecedor

Evita duplicar CPF/telefone em tabelas separadas.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import database
import ui_utils


class JanelaCadastroClientes(tk.Toplevel):
    """
    Ficha unificada de contato (Cliente ou Fornecedor) para CRM e financeiro.

    Gerar venda salva o contato e abre o PDV com os dados carregados.
    """
    def __init__(self, master, dados_cliente=None, on_salvo=None):
        """Inicializa formulário; preenche campos se dados_cliente (SELECT *) for passado."""
        super().__init__(master)
        self.on_salvo = on_salvo

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
        self.cor_btn_acao1  = paleta["cor_btn_acao1"]
        self.cor_btn_acao2  = paleta["cor_btn_acao2"]
        self.cor_hover_btn  = paleta["cor_hover_btn"]
        self.cor_hover_field = paleta["cor_hover_field"]
        
        # --- Configurações da janela ---
        self.title("Alê Sapatilhas - Gestão de Clientes")
        self.configure(bg=self.bg_fundo)
        self.resizable(False, False)

        self._manter_em_primeiro_plano()
        
        ui_utils.calcular_dimensoes_janela(self, largura_desejada=ui_utils.LARGURA_MODULO_PADRAO, altura_desejada=660)

        self.cliente_id = dados_cliente[0] if dados_cliente else None
        self.cor_base_acao = self.cor_btn_acao1

        self.criar_widgets()
        self._atualizar_botao_salvar()
        self._rastreador = ui_utils.RastreadorAlteracoes(lambda: str(self.get_dados_campos()))
        if dados_cliente:
            self.preencher_dados(dados_cliente)
            self._rastreador.marcar_limpo()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def formatar_data_para_bd(self, data_str):
        try:
            return datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except: return None

    def _aplicar_estilo_foco(self, ent):
        def on_enter(e):
            if self.focus_get() != ent: ent.config(highlightbackground=self.cor_hover_field)
        def on_leave(e):
            if self.focus_get() != ent: ent.config(highlightbackground=self.cor_borda)
        def on_focus_in(e): ent.config(highlightbackground=self.cor_destaque, highlightthickness=2)
        def on_focus_out(e): ent.config(highlightbackground=self.cor_borda, highlightthickness=1)
        ent.bind("<Enter>", on_enter); ent.bind("<Leave>", on_leave)
        ent.bind("<FocusIn>", on_focus_in); ent.bind("<FocusOut>", on_focus_out)

    def _criar_campo(self, parent, texto, row, col=0, colspan=2):
        tk.Label(parent, text=texto, bg=self.bg_fundo, fg=self.cor_lbl, 
                 font=("Segoe UI", 8, "bold")).grid(row=row, column=col, sticky="w", pady=(3, 0)) 
        ent = tk.Entry(parent, font=("Segoe UI", 10), bg=self.bg_card, fg=self.cor_texto,
                        relief="flat", highlightbackground=self.cor_borda, highlightthickness=1)
        ent.grid(row=row+1, column=col, columnspan=colspan, sticky="ew", ipady=3, padx=(0, 5) if colspan==1 else 0)
        self._aplicar_estilo_foco(ent)
        return ent

    def _criar_botao_padrao(self, parent, texto, cor, comando, row, col, colspan=1, padx=0):
        btn = tk.Button(parent, text=texto, bg=cor, fg="white", font=("Segoe UI", 10, "bold"),
                        relief="flat", cursor="hand2", command=comando)
        btn.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=padx, ipady=6)
        btn.bind("<Enter>", lambda e: btn.config(bg=self.cor_hover_btn))
        btn.bind("<Leave>", lambda e: btn.config(bg=cor))
        return btn

    def criar_widgets(self):
        main_frame = tk.Frame(self, bg=self.bg_fundo, padx=20, pady=10)
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure((0, 1), weight=1)

        tk.Label(main_frame, text="Ficha Cadastral do Contato", bg=self.bg_fundo,
                 fg=self.cor_texto, font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        form = tk.LabelFrame(main_frame, text=" Dados do contato ", bg=self.bg_fundo, fg=self.cor_destaque,
                             font=("Segoe UI", 9, "bold"), relief="solid", borderwidth=1, padx=10, pady=8)
        form.grid(row=1, column=0, columnspan=2, sticky="ew")
        form.columnconfigure((0, 1), weight=1)

        tk.Label(form, text="TIPO DE CONTATO*", bg=self.bg_fundo, fg=self.cor_lbl,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", pady=(3, 0))
        tk.Label(form, text="CLASSIFICAÇÃO", bg=self.bg_fundo, fg=self.cor_lbl,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="w", pady=(3, 0))
        self.var_tipo = tk.StringVar(value="Cliente")
        self.opt_tipo = tk.OptionMenu(form, self.var_tipo, "Cliente", "Fornecedor")
        self.opt_tipo.config(bg=self.bg_card, fg=self.cor_texto, relief="flat", font=("Segoe UI", 10), cursor="hand2")
        self.opt_tipo.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=(0, 6))
        self.var_status = tk.StringVar(value="Ativo")
        self.opt_status = tk.OptionMenu(form, self.var_status, "Vip", "Ativo", "Inativo", "Bloqueado")
        self.opt_status.config(bg=self.bg_card, fg=self.cor_texto, relief="flat",
                               highlightthickness=1, highlightbackground=self.cor_borda,
                               font=("Segoe UI", 10), cursor="hand2")
        self.opt_status.grid(row=1, column=1, sticky="ew", pady=(0, 6))

        self.ent_nome   = self._criar_campo(form, "NOME COMPLETO*", 2)
        self.ent_cpf    = self._criar_campo(form, "CPF/ CNPJ (APENAS NÚMEROS)*", 4)
        self.ent_tel    = self._criar_campo(form, "TELEFONE / WHATSAPP*", 6, col=0, colspan=1)
        self.ent_email  = self._criar_campo(form, "E-MAIL", 6, col=1, colspan=1)
        self.ent_niver  = self._criar_campo(form, "ANIVERSÁRIO (DD/MM/AAAA)", 8, col=0, colspan=1)
        ui_utils.anexar_botao_calendario(form, self.ent_niver, row=9, column=0, sticky="e")
        self.ent_tam    = self._criar_campo(form, "TAM. CALÇADO", 8, col=1, colspan=1)
        self.ent_logra  = self._criar_campo(form, "ENDEREÇO COMPLETO", 10)
        self.ent_bairro = self._criar_campo(form, "BAIRRO", 12, col=0, colspan=1)
        self.ent_cidade = self._criar_campo(form, "CIDADE", 12, col=1, colspan=1)
        self.ent_cep    = self._criar_campo(form, "CEP", 14, col=0, colspan=1)

        tk.Label(form, text="LIMITE DE CRÉDITO", bg=self.bg_fundo, fg=self.cor_lbl, font=("Segoe UI", 8, "bold")).grid(row=14, column=1, sticky="w", pady=(4, 0))
        self.ent_limite = tk.Entry(form, font=("Segoe UI", 10), bg=self.bg_card, fg=self.cor_texto, relief="flat", highlightthickness=1, highlightbackground=self.cor_borda)
        self.ent_limite.grid(row=15, column=1, sticky="ew", ipady=2)
        self.ent_limite.insert(0, "0.00")
        self._aplicar_estilo_foco(self.ent_limite)

        self.ent_obs = self._criar_campo(form, "OBSERVAÇÕES", 16)

        _pal = ui_utils.get_paleta()
        frame_rodape = tk.Frame(main_frame, bg=self.bg_fundo)
        frame_rodape.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        frame_rodape.columnconfigure((0, 1, 2), weight=1, uniform="rodape_cli")
        self.btn_salvar = ui_utils.criar_botao_rodape(
            frame_rodape,
            ui_utils.texto_botao_salvar("Contato", bool(self.cliente_id)),
            self.salvar_dados,
            "acao1",
            _pal,
        )
        self.btn_salvar.grid(row=0, column=0, sticky="ew", padx=(0, 4), ipady=6)
        self.btn_gerar_venda = ui_utils.criar_botao_rodape(
            frame_rodape, "Lançar Venda", self.gerar_venda, "acao2", _pal,
        )
        self.btn_gerar_venda.grid(row=0, column=1, sticky="ew", padx=4, ipady=6)
        self.btn_cancelar = ui_utils.criar_botao_rodape(
            frame_rodape, "Fechar Janela", self._fechar, "sair", _pal,
        )
        self.btn_cancelar.grid(row=0, column=2, sticky="ew", padx=(4, 0), ipady=6)

    def _atualizar_botao_salvar(self):
        em_edicao = bool(self.cliente_id)
        self.btn_salvar.config(text=ui_utils.texto_botao_salvar("Contato", em_edicao))
        ui_utils.atualizar_cor_botao_rodape(
            self.btn_salvar, "acao2" if em_edicao else "acao1", ui_utils.get_paleta(),
        )

    def _fechar(self):
        if ui_utils.confirmar_fechar_formulario(self, self._rastreador):
            self.destroy()

    def get_dados_campos(self):
        """Retorna um dicionário com os dados da tela limpos"""
        return {
            "nome": self.ent_nome.get().strip(),
            "cpf": self.ent_cpf.get().strip(),
            "tel": self.ent_tel.get().strip(),
            "email": self.ent_email.get().strip(),
            "niver": self.formatar_data_para_bd(self.ent_niver.get().strip()) if self.ent_niver.get().strip() else None,
            "tam": self.ent_tam.get().strip() or 0,
            "endereco": self.ent_logra.get().strip(),
            "bairro": self.ent_bairro.get().strip(),
            "cidade": self.ent_cidade.get().strip(),
            "cep": self.ent_cep.get().strip(),
            "obs": self.ent_obs.get().strip(),
            "limite": self.ent_limite.get().strip() or 0,
            "status": self.var_status.get(),
            "tipo": self.var_tipo.get()
        }

    def salvar_dados(self):
        d = self.get_dados_campos()
        if not d["nome"] or not d["cpf"] or not d["tel"]:
            messagebox.showwarning("Atenção", "Preencha os campos obrigatórios (Nome, CPF e Telefone).", parent=self)
            return

        try:
            dados_atualizacao = {
                'tipo': d['tipo'], 'nome': d['nome'], 'cpf': d['cpf'], 'telefone': d['tel'], 'email': d['email'],
                'aniversario': d['niver'], 'tamanho_calcado': d['tam'], 'endereco_completo': d['endereco'],
                'bairro': d['bairro'], 'cidade': d['cidade'], 'cep': d['cep'], 'observacao': d['obs'],
                'limite_credito': d['limite'], 'status_cliente': d['status']
            }
            cid = self.cliente_id
            if self.cliente_id:
                database.atualizar_cliente(self.cliente_id, **dados_atualizacao)
                messagebox.showinfo("Sucesso", "Cadastro atualizado!", parent=self)
            else:
                cid = database.cadastrar_cliente(
                    d['nome'], d['cpf'], d['tel'], d['email'], d['niver'], d['tam'],
                    d['endereco'], d['bairro'], d['cidade'], d['cep'], d['obs'], d['limite'], d['tipo']
                )
                if not cid:
                    messagebox.showerror("Erro", "Não foi possível cadastrar o cliente. Verifique o CPF e tente novamente.", parent=self)
                    return
                messagebox.showinfo("Sucesso", "Cliente cadastrado!", parent=self)

            if hasattr(self.master, "exibir_clientes"):
                self.master.exibir_clientes()
            cb = self.on_salvo
            self.destroy()
            if cb and cid:
                cb(cid)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar: {e}", parent=self)

    def gerar_venda(self):
        if not ui_utils.confirmar(self, "Gerar venda", "Salvar contato e abrir o PDV com estes dados?"):
            return
        d = self.get_dados_campos()
        if not d["nome"]:
            messagebox.showwarning("Atenção", "Preencha pelo menos o nome para gerar venda.", parent=self)
            return
        d["tipo"] = "Cliente"

        try:
            if self.cliente_id:
                dados_atualizacao = {
                    'nome': d['nome'], 'cpf': d['cpf'], 'telefone': d['tel'], 'email': d['email'],
                    'aniversario': d['niver'], 'tamanho_calcado': d['tam'], 'endereco_completo': d['endereco'],
                    'bairro': d['bairro'], 'cidade': d['cidade'], 'cep': d['cep'], 'observacao': d['obs'],
                    'limite_credito': d['limite'], 'status_cliente': d['status'], 'tipo': d['tipo'],
                }
                database.atualizar_cliente(self.cliente_id, **dados_atualizacao)
                cid = self.cliente_id
            else:
                cid = database.cadastrar_cliente(
                    d['nome'], d['cpf'], d['tel'], d['email'], d['niver'], d['tam'],
                    d['endereco'], d['bairro'], d['cidade'], d['cep'], d['obs'], d['limite'], d['tipo']
                )
                if not cid:
                    messagebox.showerror("Erro", "Não foi possível cadastrar o cliente. Verifique CPF e tente novamente.", parent=self)
                    return
            
            self.destroy()
            from cadastro_vendas import JanelaCadastroVendas
            JanelaCadastroVendas(self.master, cliente_selecionado=(cid, d["nome"], d["tel"]))
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao processar: {e}", parent=self)

    def _manter_em_primeiro_plano(self):
        try:
            self.attributes("-topmost", True)
        except Exception as e:
            messagebox.showwarning("Aviso", f"Não foi possível manter esta janela em primeiro plano: {e}", parent=self)

    def formatar_data_exibicao(self, data_str):
        return ui_utils.formatar_data_exibicao(data_str)

    def preencher_dados(self, d):
        # SELECT * : id, tipo, nome, cpf, telefone, email, aniversario, tamanho_calcado, endereco, bairro, cidade, cep, obs, limite, data_cadastro, status
        self.var_tipo.set(d[1] if len(d) > 1 and d[1] in ('Cliente', 'Fornecedor') else 'Cliente')
        mapping = [
            (self.ent_nome, d[2]), (self.ent_cpf, d[3]), (self.ent_tel, d[4]),
            (self.ent_email, d[5]), (self.ent_niver, self.formatar_data_exibicao(d[6])), (self.ent_tam, d[7]),
            (self.ent_logra, d[8]), (self.ent_bairro, d[9]), (self.ent_cidade, d[10]),
            (self.ent_cep, d[11]), (self.ent_obs, d[12])
        ]
        for widget, valor in mapping:
            widget.delete(0, tk.END)
            widget.insert(0, valor if valor else "")
        
        self.ent_limite.delete(0, "end")
        self.ent_limite.insert(0, f"{float(d[13] or 0):.2f}" if len(d) > 13 else "0.00")
        self.var_status.set(d[15] if len(d) > 15 else "Ativo")
        self._atualizar_botao_salvar()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    JanelaCadastroClientes(root)
    root.mainloop()