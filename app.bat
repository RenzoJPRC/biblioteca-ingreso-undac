@echo off
title SISTEMA INGRESO UNDAC
color 0a

echo.
echo ======================================================
echo    SISTEMA BIBLIOTECARIO UNDAC - ENTORNO DE PRODUCCION
echo ======================================================
echo.
echo El servidor WSGI Waitress esta arrancando...
echo.

cd /d "%~dp0"

:: 1. Ejecutar el servidor en esta misma ventana
:: OJO: No usar "start" para evitar abrir 2 ventanas y confundirse al cerrarlo
python app.py

:: 2. Esperar unos segundos para que levante (si quieres abrir navegador auto)
:: timeout /t 3 >nul

:: 3. Abrir navegador automaticamente en entorno local
start http://127.0.0.1:5000

:: ==============================================================
:: NOTA PARA PRODUCCION (EN LA BIBLIOTECA):
:: Cambiar la linea de arriba ("start http://127.0.0.1:5000") por:
:: start http://172.16.3.15:5000
:: ==============================================================

pause
