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

:: 1. Entrar a la carpeta exacta
:: Usamos %%~dp0 para que detecte la ruta originaria auto-dinamica
cd /d "%~dp0"

:: 2. Ejecutar el servidor en esta misma ventana
:: (OJO: No usar "start cmd /k" porque abriria doble ventana y seria dificil de apagar luego)
python app.py

:: 3. Esperar unos segundos para que levante (Ejemplo comentado)
:: timeout /t 3 >nul

:: 4. Abrir navegador automaticamente hacia la IP de red de la PC (Ejemplo de Produccion)
:: start http://172.16.3.15:5000

:: Si la ventana se cierra es porque hay un error critico, el pause lo mantendra abierto
pause
