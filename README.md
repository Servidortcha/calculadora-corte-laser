# Calculadora Precio Corte Láser 🇦🇷

Calculadora web para presupuestar corte láser fibra/CO2 con **precios de chapas actualizados automáticamente desde internet** (Argentina).

**Demo:** abrí `calculadora-corte-laser.html` en el navegador (sin instalar nada).

![Precio con IVA](https://img.shields.io/badge/precios-Sep%202026-emerald) ![Auto](https://img.shields.io/badge/auto--update-semanal-blue)

## Features
- **Precio = Material + Tiempo máquina + Margen + IVA**
- Materiales: Acero carbono, Inox 304, Aluminio, MDF, Acrílico (densidad + espesor)
- Tiempo = `Longitud / Velocidad + Perforaciones × t + Setup/lote`
- Velocidades por material/espesor/potencia (1kW/1.5kW/3kW/6kW) editables
- Tarifas: $/kg o $/m², $/min máquina, % desperdicio, setup, margen, IVA
- Presupuesto unitario/total con/sin IVA, desglose y barra visual
- Guardado localStorage + copiar resumen + imprimir PDF

## Precios desde internet (auto)

| Material | $/kg (IVA) | Fuente |
|---|---|---|
| Acero carbono | ~$2.831 | [Serviprod](https://serviprod.com.ar/chapas/) |
| Inox 304 | ~$11.672 | [acerosinoxidables.com.ar](https://www.acerosinoxidables.com.ar/chapa/) + Provecom |
| Aluminio | ~$12.671 | [Alumina Argentina](https://www.alumina-argentina.com.ar/aluminio/chapas-de-aluminio/) |
| MDF | ~$1.437 | [Sodimac](https://www.sodimac.com.ar/sodimac-ar/product/2400642/mdf-3-mm-183-x-260-cm/2400642/) |
| Acrílico | ~$28.315 | [Laminados PAI](https://www.laminadospai.com/productos/placa-acrilico-transparente-3mm/) |

> Actualizado: 2026-09-07. Ver `precios.json` y detalle en la calculadora sección 3.

## Actualizador automático

```bash
# Manual (doble click)
actualizar_precios.bat
# o
python actualizar_precios.py

# Automático semanal (Lunes 09:00) - Ejecutar como Administrador
crear_tarea_programada.bat
```

Dependencias: `pip install requests beautifulsoup4 lxml` (se instalan solas).

El scraper actualiza `calculadora-corte-laser.html` → `const preciosInternet` y `precios.json`. Si un sitio falla, conserva precio anterior.

## Estructura
```
calculadora-corte-laser.html   # calculadora (single-file, Tailwind CDN)
actualizar_precios.py          # scraper 5 fuentes
actualizar_precios.bat         # runner manual
crear_tarea_programada.bat     # task scheduler semanal
precios.json                   # últimos precios
README_PRECIOS.md              # docs actualizador
```

## Uso
1. Abrir `calculadora-corte-laser.html`
2. Elegir material/espesor/potencia, medidas, longitud de corte
3. Ajustar $/kg (auto desde internet) y tarifa $/min
4. Ver presupuesto a la derecha, copiar o imprimir

Licencia: MIT
