@echo off
REM Crea tarea programada semanal (Lunes 9:00 AM) para actualizar precios
REM Ejecutar como Administrador

echo Creando tarea programada "ActualizarPreciosCorteLaser"...

schtasks /create /tn "ActualizarPreciosCorteLaser" /tr "\"%~dp0actualizar_precios.bat\"" /sc weekly /d MON /st 09:00 /f /rl highest

if %errorlevel% equ 0 (
    echo.
    echo [OK] Tarea creada: todos los lunes 09:00
    echo Verifica en: Task Scheduler ^> Biblioteca ^> ActualizarPreciosCorteLaser
    schtasks /query /tn "ActualizarPreciosCorteLaser" /v /fo list | findstr /i "TaskName Next Run Time"
) else (
    echo.
    echo [ERROR] No se pudo crear. Ejecuta este .bat como Administrador (click derecho ^> Ejecutar como administrador)
)

echo.
echo Para ejecutar manual: schtasks /run /tn "ActualizarPreciosCorteLaser"
echo Para borrar: schtasks /delete /tn "ActualizarPreciosCorteLaser" /f
pause
