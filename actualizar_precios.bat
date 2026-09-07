@echo off
REM Actualizador automatico de precios - Corte Laser
REM Doble click para ejecutar manualmente
REM Tambien se ejecuta semanal via Task Scheduler

echo ============================================
echo  Actualizando precios de chapas...
echo  %date% %time%
echo ============================================
cd /d "%~dp0"
python actualizar_precios.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Fallo la actualizacion. Revisa precios_log.txt
    pause
) else (
    echo.
    echo [OK] Precios actualizados. Recarga la calculadora.
    timeout /t 5
)
