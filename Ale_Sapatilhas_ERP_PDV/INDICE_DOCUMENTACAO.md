# Índice de documentação do código (Vs 4.6)

Complemento aos docstrings nos arquivos `.py`. Cada função/método deve ter docstring no fonte; este índice resume o conjunto.

## main.py — `SistemaAleSapatilhas`

| Método | Função |
|--------|--------|
| `__init__` | Inicializa shell, paleta e lista inicial |
| `setup_ui` | Monta interface principal |
| `criar_barra_busca` | Busca + Filtrar + Limpar + Utilidades |
| `filtrar_busca` | Filtro textual com pilha de restauração |
| `abrir_menu_filtrar` | Filtros dinâmicos por modo |
| `abrir_menu_utilidades` | Ferramentas auxiliares |
| `exibir_*` | Carrega listas (clientes, produtos, vendas…) |
| `abrir_*` | Abre janelas modais de cadastro/financeiro |
| `editar_selecionado` | Duplo clique / edição contextual |

## database.py

| Função | Função |
|--------|--------|
| `conectar` | SQLite com FK ativas |
| `criar_tabelas` | Schema + migrações |
| `cadastrar_produto` | INSERT produto ou soma estoque se SKU igual |
| `realizar_venda_segura` | Venda atômica → retorna `(ok, msg, venda_id)` |
| `cancelar_venda` | Estorno + estoque + financeiro |
| `cadastrar_despesa` | Parcelas de saída |
| `listar_itens` | Estoque para PDV (com foto) |

## ui_utils.py

| Símbolo | Função |
|---------|--------|
| `confirmar` | Diálogo Sim/Não |
| `MiniCalendario` | Seletor de data |
| `tipo_produto_*` | Mapeamento Calçado/Vestuário ↔ BD |
| `abrir_calculadora` etc. | Utilidades do menu principal |

## Telas modais

- **cadastro_produtos**: SKU, variações, Salvar e Continuar  
- **cadastro_clientes**: CRM + Gerar venda → PDV  
- **cadastro_vendas**: PDV completo + Cadastrar pagamento  
- **gerenciar_despesas** / **gerenciar_receitas**: Financeiro  

## Testes

```powershell
python test_sistema.py
```

Executa testes sem GUI em banco temporário.
