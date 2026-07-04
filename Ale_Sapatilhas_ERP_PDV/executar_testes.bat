@echo off
cd /d "%~dp0"
echo Compilando modulos...
python -m py_compile main.py cadastro_produtos.py cadastro_clientes.py cadastro_vendas.py gerenciar_despesas.py gerenciar_receitas.py ui_utils.py database.py test_sistema.py
if errorlevel 1 exit /b 1
echo.
echo Executando testes automatizados...
python test_sistema.py
pause
