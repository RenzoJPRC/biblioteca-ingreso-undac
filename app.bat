@echo off
title SISTEMA INGRESO UNDAC
color 0a

:: =========================================================================
:: INSTRUCCIONES PARA DESPLEGAR EN UNA COMPUTADORA NUEVA (NUEVO SERVIDOR)
:: 1. Instalar Python 3.10 o superior (marcar siempre la casilla "Add to PATH").
:: 2. Ejecutar instalar dependencias: pip install -r requirements.txt
:: =========================================================================

echo.
echo ======================================================
echo    SISTEMA BIBLIOTECARIO UNDAC - ENTORNO DE PRODUCCION
echo ======================================================
echo.
echo El servidor WSGI Waitress esta arrancando, esto permitira cientos de lecturas
echo simultaneas sin colgarse. Puedes minimizar esta ventana pero NO LA CIERRES.
echo.

:: 1. Entrar a la carpeta exacta (usando comillas por los espacios)
:: Usamos %%~dp0 para que detecte la ruta originaria (Mejor que hardcodear C:\Archivos de Programa)
cd /d "%~dp0"

:: 2. Ejecutar el servidor (veo que se llama app.py)
python app.py

:: Si la ventana se cierra es porque hay un error, el pause lo mantendra abierto para que lo veas
pause
