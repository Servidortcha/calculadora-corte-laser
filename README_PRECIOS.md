# Calculadora Corte Láser - Actualizador de Precios

## Archivos
- `calculadora-corte-laser.html` → calculadora (abrir con doble click)
- `actualizar_precios.py` → scraper que actualiza precios desde internet
- `actualizar_precios.bat` → ejecutable manual (doble click)
- `crear_tarea_programada.bat` → programa actualización semanal automática
- `precios.json` → últimos precios relevados (generado auto)
- `precios_log.txt` → historial de actualizaciones

## Uso manual
1. Doble click en `actualizar_precios.bat`
2. Esperar 15-30 seg (scrapea 5 sitios)
3. Recargar calculadora con F5

## Automático semanal
1. Click derecho en `crear_tarea_programada.bat` → **Ejecutar como administrador**
2. Listo: cada **lunes 09:00** se actualiza solo, aunque no abras la calculadora.

Para verificar:
```
schtasks /query /tn "ActualizarPreciosCorteLaser"
```

Para ejecutar la tarea ahora:
```
schtasks /run /tn "ActualizarPreciosCorteLaser"
```

## Qué scrapea
| Material | Fuente | URL |
|---|---|---|
| Acero carbono | Serviprod | https://serviprod.com.ar/chapas/ |
| Inox 304 | acerosinoxidables.com.ar + Provecom | https://www.acerosinoxidables.com.ar/chapa/ |
| Aluminio | Alumina Argentina | https://www.alumina-argentina.com.ar/aluminio/chapas-de-aluminio/ |
| MDF | Sodimac + Facilplac | https://www.sodimac.com.ar/.../mdf-3-mm-183-x-260-cm/ |
| Acrílico | Laminados PAI | https://www.laminadospai.com/productos/placa-acrilico-transparente-3mm/ |

Si un sitio falla (bloqueo, cambio de HTML, sin internet) conserva el precio anterior y lo registra en `precios.json` → `fuentes`.

## Dependencias
Se instalan solas la primera vez: `requests`, `beautifulsoup4`, `lxml`
Manual: `pip install requests beautifulsoup4 lxml`

## Personalización
Edita `DEFAULTS` en `actualizar_precios.py` si querés otro precio base.
Edita `preciosInternet` en el HTML si querés ajuste manual sin scraper.
