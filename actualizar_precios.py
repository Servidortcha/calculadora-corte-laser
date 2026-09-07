#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Actualizador automático de precios de chapas - Corte Láser
Scrapea 5 fuentes argentinas y actualiza calculadora-corte-laser.html

Fuentes:
 - Acero carbono: Serviprod (https://serviprod.com.ar/chapas/)
 - Inox 304: acerosinoxidables.com.ar + Provecom
 - Aluminio: Alumina Argentina (https://www.alumina-argentina.com.ar/aluminio/chapas-de-aluminio/)
 - MDF: Sodimac (https://www.sodimac.com.ar/ ...)
 - Acrílico: Laminados PAI (https://www.laminadospai.com/...)

Ejecución: python actualizar_precios.py
Se puede programar semanal con Windows Task Scheduler.
"""
import re
import json
import time
import pathlib
import sys
from datetime import datetime
# Fix Windows cp1252 encoding for emojis
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except:
    pass

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Faltan dependencias. Instalando requests + beautifulsoup4...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "lxml"])
    import requests
    from bs4 import BeautifulSoup

BASE_DIR = pathlib.Path(__file__).parent
HTML_PATH = BASE_DIR / "calculadora-corte-laser.html"
JSON_PATH = BASE_DIR / "precios.json"
LOG_PATH = BASE_DIR / "precios_log.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

DENSIDADES = {
    "acero_carbono": 7850,
    "inox": 7900,
    "aluminio": 2700,
    "mdf": 750,
    "acrilico": 1190,
}

# Valores por defecto si falla todo (Sep 2026 relevado)
DEFAULTS = {
    "acero_carbono": 2800,
    "inox": 10000,
    "aluminio": 13200,
    "mdf": 1050,
    "acrilico": 28300,
}

def parse_price_ars(text):
    """Convierte '$40.048,54' o '$ 40.048' o '52650' -> float ARS"""
    if not text:
        return None
    # limpiar
    t = text.strip()
    # quitar $ y espacios
    t = re.sub(r"[^\d,\.]", "", t)
    if not t:
        return None
    # Si tiene coma, es formato AR: 40.048,54 -> 40048.54
    # Si solo tiene punto y 2 decimales al final, también puede ser
    # Detectar
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    else:
        # solo puntos: si tiene varios puntos, son miles -> quitar
        # si tiene un punto con 2 decimales al final, dejarlo
        if t.count(".") > 1:
            t = t.replace(".", "")
        # si tiene 1 punto y 3 dígitos después, es miles -> quitar
        elif "." in t:
            parts = t.split(".")
            if len(parts[-1]) == 3 and len(t) > 6:
                t = t.replace(".", "")
    try:
        return float(t)
    except:
        return None

def fetch(url, retries=2):
    for i in range(retries+1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return r.text
            else:
                print(f"  ! HTTP {r.status_code} para {url}")
                time.sleep(2)
        except Exception as e:
            print(f"  ! Error fetch {url}: {e}")
            time.sleep(2)
    return None

def scrape_acero_carbono():
    """Serviprod - 3 chapas lisas LAF via pmwDataLayer JS"""
    print("[1/5] Acero carbono - Serviprod...")
    html = fetch("https://serviprod.com.ar/chapas/")
    if not html:
        return None
    # Serviprod oculta precios en JS: window.pmwDataLayer.products[ID] = {"sku":"chli90200","price":40048.54,...}
    # Mapeo SKU -> peso conocido
    sku_pesos = {
        "chli90200": 14.3,   # 0.90mm 1000x2000
        "chli125200": 19.86, # 1.25mm 1000x2000
        "chli160288": 37.84, # 1.60mm 1220x2440
        "chli90200v": 14.3,
        "chli125200v": 19.86,
    }
    kgs = []
    # Buscar bloques pmw
    blocks = re.findall(r'"sku"\s*:\s*"([^"]+)"\s*,\s*"price"\s*:\s*([\d\.]+)', html, flags=re.IGNORECASE)
    # blocks es lista de (sku, price)
    for sku, price_str in blocks:
        sku_low = sku.lower()
        if sku_low in sku_pesos:
            price = float(price_str)
            peso = sku_pesos[sku_low]
            if 30000 < price < 200000:
                kgp = price / peso
                print(f"  -> {sku} ${round(price)} / {peso}kg = {round(kgp)}/kg")
                if 1500 < kgp < 5000:
                    kgs.append(kgp)
    if kgs:
        avg = sum(kgs)/len(kgs)
        print(f"  => Acero avg {round(avg)} $/kg sobre {len(kgs)} muestras")
        return round(avg)
    # Fallback 2: buscar cualquier "price":XXXX dentro de pmwDataLayer
    raw_prices = re.findall(r'"price"\s*:\s*([\d\.]+)', html)
    raw_prices = [float(p) for p in raw_prices if 30000 < float(p) < 150000]
    print(f"  -> raw prices fallback {raw_prices[:5]}")
    if len(raw_prices) >= 2:
        pesos = [14.3, 19.86, 37.84]
        kgs2 = [p/peso for p, peso in zip(raw_prices[:3], pesos)]
        kgs2 = [k for k in kgs2 if 1500 < k < 5000]
        if kgs2:
            return round(sum(kgs2)/len(kgs2))
    return None

def scrape_inox():
    """Aceros inoxidables - TiendaNube JSON-LD"""
    print("[2/5] Inox 304 - acerosinoxidables.com.ar + Provecom...")
    # URLs representativas (varias medidas para promediar)
    urls = [
        "https://www.acerosinoxidables.com.ar/productos/chapa-aceros-inoxidables-esmerilada-304-1-00-mm--1000-x-3000-mm/",
        "https://www.acerosinoxidables.com.ar/productos/chapa-aceros-inoxidables-mate-304-0-90-mm-1250-x-3000-mm/",
        "https://www.acerosinoxidables.com.ar/productos/chapa-aceros-inoxidables-esmerilada-304-0-50-mm--1000-x-3000-mm/",
    ]
    # Alternativa: fetch categoría y extraer JSON-LD
    html_cat = fetch("https://www.acerosinoxidables.com.ar/chapa/")
    kgs = []
    if html_cat:
        # Extraer todos los prices del JSON-LD en categoría
        prices = re.findall(r'"price"\s*:\s*"(\d+)"', html_cat)
        prices += re.findall(r'"price"\s*:\s*(\d+)', html_cat)
        # Filtrar precios plausibles inox (50k-600k)
        prices = [float(p) for p in prices if 40000 < float(p) < 700000]
        # Intentar inferir espesor y medida del contexto: buscar texto alrededor
        # Para simplificar, usar 3 productos representativos con peso teórico:
        # Si tenemos N precios, asignamos pesos promedio para thicknesses típicas 0.5,0.9,1.0,1.5
        # Mejor: usar URLs individuales para precisión
        if prices:
            print(f"  -> {len(prices)} precios en categoría (ej: {prices[:3]})")
    # Fetch productos individuales para cálculo preciso peso/precio
    detalles = [
        # (url, espesor mm, ancho mm, largo mm)
        ("https://www.acerosinoxidables.com.ar/productos/chapa-aceros-inoxidables-esmerilada-304-0-50-mm--1000-x-3000-mm/", 0.5, 1000, 3000),
        ("https://www.acerosinoxidables.com.ar/productos/chapa-aceros-inoxidables-esmerilada-304-1-00-mm--1000-x-3000-mm/", 1.0, 1000, 3000),
        ("https://www.acerosinoxidables.com.ar/productos/chapa-aceros-inoxidables-mate-304-0-90-mm-1250-x-3000-mm/", 0.9, 1250, 3000),
    ]
    # También agregar Provecom como fallback
    provecom_html = fetch("https://provecom.com.ar/producto-categoria/inoxidable/chapas-aisi-304/aisi-304-esmeriladas/")
    if provecom_html:
        p_prices = re.findall(r"\$\s*([\d\.,]+)", provecom_html)
        # primer precio que parece inox 0.5mm $88.000
        pp = [parse_price_ars(x) for x in p_prices if parse_price_ars(x) and 50000 < parse_price_ars(x) < 600000]
        if pp:
            print(f"  -> Provecom {len(pp)} precios (ej {pp[:3]})")
            # Estimación: usar precio promedio 88k para 0.5mm 1000x2000 (7.9kg) => 11139/kg, etc.
            # No calculamos aquí, solo informativo

    for url, esp, w, l in detalles:
        html = fetch(url)
        if not html:
            continue
        # Buscar price en JSON-LD
        m = re.search(r'"price"\s*:\s*"?(\d+)"?', html)
        if m:
            price = float(m.group(1))
            # Algunos sitios guardan price sin descuento (lista), hay precio con 5% off en visible
            # El price en JSON es el de lista (mayor). Usar el visible con descuento si está:
            m2 = re.search(r"\$\s*([\d\.\,]+)\s*\\n.*5% OFF", html)
            # Buscar precio visible con descuento: suele estar como $271.042,00 luego \ -5% OFF $285.307
            # El primero es el precio final con descuento (el que paga cliente transferencia)
            visible = re.findall(r"\$\s*([\d\.\,]+)", html)
            v_vals = [parse_price_ars(x) for x in visible if parse_price_ars(x) and 50000 < parse_price_ars(x) < 700000]
            if v_vals:
                # el menor de los dos grandes es el con descuento (ej 271k vs 285k) -> usar menor (cliente)
                price = min(v_vals[:2]) if len(v_vals)>=2 else v_vals[0]
            area = (w/1000)*(l/1000)
            peso = area * (esp/1000) * DENSIDADES["inox"]
            kg_price = price / peso
            print(f"  -> Inox {esp}mm {w}x{l} = {round(peso,2)}kg -> ${round(price)} => ${round(kg_price)}/kg (src {url.split('/')[-2]})")
            if 5000 < kg_price < 20000:  # rango plausible
                kgs.append(kg_price)
        time.sleep(0.7)

    if kgs:
        avg = sum(kgs)/len(kgs)
        print(f"  => Inox avg {round(avg)} $/kg sobre {len(kgs)} muestras")
        return round(avg)
    # fallback a categoría precios si no hubo detalles
    if 'prices' in locals() and prices:
        # Estimar peso promedio: usar 1mm 1000x2000 =15.8kg como referencia
        avg_price = sum(prices[:6])/min(6,len(prices))
        # peso promedio asumido 15kg (mezcla espesores)
        est_kg = avg_price / 15
        if 6000 < est_kg < 18000:
            print(f"  => fallback categ avg {round(est_kg)}/kg")
            return round(est_kg)
    return None

def scrape_aluminio():
    print("[3/5] Aluminio - Alumina Argentina...")
    html = fetch("https://www.alumina-argentina.com.ar/aluminio/chapas-de-aluminio/")
    if not html:
        return None
    # Extraer JSON-LD blocks completos para emparejar price y weight correctamente
    import json as js
    ld_blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, flags=re.DOTALL)
    kgs_ld = []
    kgs_weights = []  # para debug
    for block in ld_blocks:
        try:
            data = js.loads(block.strip())
            if isinstance(data, dict) and "weight" in data and "offers" in data:
                w = data["weight"].get("value")
                p = data["offers"].get("price")
                if w and p:
                    try:
                        w = float(w); p = float(p)
                        # Filtrar solo chapas LISAS grandes y espesor laser (0.5-3mm). 
                        # Peso >=2.5kg evita 500x500 y <20kg evita 6mm/premium. Rango kg 9k-16k es lisa standard
                        if 2.5 <= w < 20 and 5000 < p < 400000:
                            kgp = p / w
                            # Excluir premium (antideslizante/gofrada) que supera 17k
                            if 9000 < kgp < 16500:
                                kgs_ld.append(kgp)
                                kgs_weights.append(w)
                        elif 0.3 < w < 2.5:
                            pass
                    except:
                        pass
        except:
            continue
    if kgs_ld:
        print(f"  -> JSON-LD filtrado (>=2.5kg) {len(kgs_ld)} muestras $/kg: {[round(x) for x in kgs_ld[:5]]} (pesos {kgs_weights[:5]}) => avg {round(sum(kgs_ld)/len(kgs_ld))}")
        kgs_sorted = sorted(kgs_ld)
        trim = int(len(kgs_sorted)*0.2)
        if trim > 0 and len(kgs_sorted) > 4:
            trimmed = kgs_sorted[trim:-trim]
        else:
            trimmed = kgs_sorted
        return round(sum(trimmed)/len(trimmed))
    # Fallback genérico regex estricto KGM
    prices = re.findall(r'"price"\s*:\s*"?(\d+)"?', html)
    prices = [float(p) for p in prices if 5000 < float(p) < 700000]
    # Buscar peso con KGM en orden correcto: unitCode antes de value
    weights = re.findall(r'"unitCode"\s*:\s*"KGM"\s*,\s*"value"\s*:\s*"?([\d\.]+)"?', html)
    if not weights:
        weights = re.findall(r'"value"\s*:\s*"?([\d\.]+)"?\s*,\s*"unitCode"\s*:\s*"KGM"', html)
    weights_f = [float(w) for w in weights if 0.3 < float(w) < 70]
    print(f"  -> fallback {len(prices)} prices, {len(weights_f)} weights (ej {prices[:3]}, {weights_f[:3]})")
    if prices and weights_f and len(weights_f) >= 3:
        n = min(len(prices), len(weights_f), 8)
        kgs = [prices[i]/weights_f[i] for i in range(n) if weights_f[i]>0]
        kgs = [k for k in kgs if 8000 < k < 25000]
        if kgs:
            return round(sum(kgs)/len(kgs))
    # fallback: parse manual 3 productos conocidos
    detalles = [
        ("https://www.alumina-argentina.com.ar/productos/chapa-aluminio-05-mm-x-1000-mm-x-2000-mm/", 0.5, 1000, 2000),
        ("https://www.alumina-argentina.com.ar/productos/chapa-aluminio-1-mm-x-1000-mm-x-2000-mm/", 1.0, 1000, 2000),
        ("https://www.alumina-argentina.com.ar/productos/chapa-aluminio-6-mm-x-1000-mm-x-2000-mm/", 6.0, 1000, 2000),
    ]
    kgs2 = []
    for url, esp, w, l in detalles:
        h = fetch(url)
        if not h:
            continue
        m = re.search(r'"price"\s*:\s*"?(\d+)"?', h)
        mw = re.search(r'"value"\s*:\s*"?([\d\.]+)"?\s*,\s*"unitCode"\s*:\s*"KGM"', h)
        if m:
            price = float(m.group(1))
            if mw:
                weight = float(mw.group(1))
            else:
                area = (w/1000)*(l/1000)
                weight = area*(esp/1000)*DENSIDADES["aluminio"]
            kgp = price/weight
            print(f"  -> Alu {esp}mm {w}x{l} {weight}kg ${price} => {round(kgp)}/kg")
            if 8000 < kgp < 25000:
                kgs2.append(kgp)
        time.sleep(0.5)
    if kgs2:
        return round(sum(kgs2)/len(kgs2))
    # último fallback: calcular desde precios conocidos hardcoded 0.5mm $35.696/2.7kg=13221
    return None

def scrape_mdf():
    print("[4/5] MDF - Sodimac + Facilplac (promedio 3mm y 18mm)...")
    import json as js
    kgs = []
    # 1) MDF 3mm Sodimac
    h = fetch("https://www.sodimac.com.ar/sodimac-ar/product/2400642/mdf-3-mm-183-x-260-cm/2400642/")
    if h:
        ld = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', h, flags=re.DOTALL)
        price = None
        for block in ld:
            try:
                data = js.loads(block.strip())
                if isinstance(data, dict) and "offers" in data:
                    offers = data["offers"]
                    if isinstance(offers, list):
                        for off in offers:
                            if "price" in off:
                                price = float(off["price"])
                                break
                    elif isinstance(offers, dict) and "price" in offers:
                        price = float(offers["price"])
                    if price:
                        break
            except:
                continue
        if not price:
            m = re.search(r'"price"\s*:\s*"?([\d\.]+)"?', h)
            if m:
                try: price = float(m.group(1))
                except: pass
        if price and 8000 < price < 100000:
            area = 1.83*2.60
            peso = area * 0.003 * DENSIDADES["mdf"]
            kgp = price / peso
            print(f"  -> MDF 3mm 183x260 {round(peso,2)}kg ${price} => {round(kgp)}/kg")
            if 600 < kgp < 2500:
                kgs.append(kgp)
        else:
            print(f"  ! MDF 3mm precio no encontrado ({price})")
        time.sleep(0.5)
    # 2) MDF 18mm Facilplac / Sodimac  - para balancear (18mm es mas barato por kg)
    h2 = fetch("https://facilplac.com.ar/producto/crudos/nova/tablero-fibrofacil-nova-18-mm/")
    price2 = None
    if h2:
        # Buscar $72.701
        ms = re.findall(r"\$\s*([\d\.\,]+)", h2)
        candidates = [parse_price_ars(x) for x in ms if parse_price_ars(x) and 30000 < parse_price_ars(x) < 150000]
        if candidates:
            # El primero suele ser precio tachado 85k, segundo 72k -> tomar el menor que es el vigente
            price2 = min(candidates)
            # Validar que sea MDF 18mm
            if price2:
                area2 = 3.66*1.83
                peso2 = area2 * 0.018 * DENSIDADES["mdf"]
                kgp2 = price2 / peso2
                print(f"  -> MDF 18mm 366x183 {round(peso2,2)}kg ${price2} => {round(kgp2)}/kg")
                if 600 < kgp2 < 2000:
                    kgs.append(kgp2)
    if kgs:
        avg = sum(kgs)/len(kgs)
        print(f"  => MDF avg {round(avg)}/kg sobre {len(kgs)} espesores (3mm+18mm)")
        return round(avg)
    # Intento 2: MDF 18mm
    h2 = fetch("https://facilplac.com.ar/producto/crudos/nova/tablero-fibrofacil-nova-18-mm/")
    if h2:
        m = re.search(r"\$\s*([\d\.\,]+)", h2)
        if m:
            v = parse_price_ars(m.group(1))
            if v:
                area2 = 3.66*1.83
                peso2 = area2*0.018*DENSIDADES["mdf"]
                kgp2 = v/peso2
                print(f"  -> MDF 18mm 366x183 {round(peso2,2)}kg ${v} => {round(kgp2)}/kg")
                if 600 < kgp2 < 2500:
                    # promediar ambos?
                    if 'kgp' in locals():
                        return round((kgp+kgp2)/2)
                    return round(kgp2)
    return None

def scrape_acrilico():
    print("[5/5] Acrílico - Laminados PAI...")
    h = fetch("https://www.laminadospai.com/productos/placa-acrilico-transparente-3mm/")
    if not h:
        return None
    # Buscar precios variados: 1.25x2.47 $310.700, 1.25x1.22 $166.200...
    # En JSON-LD hay lowPrice/highPrice y offers con price por variante
    prices = re.findall(r'"price"\s*:\s*"?(\d+)"?', h)
    prices = [float(p) for p in prices if 30000 < float(p) < 600000]
    # Filtrar los relevantes: 3mm grande es 310700
    # Para 3mm 125x247 =3.0875m2, peso=11.02kg => kg=28200
    # Para 5mm 125x247 =3.0875m2, peso=18.37kg => kg=28443 (si precio 522500)
    # Buscamos también 5mm
    h5 = fetch("https://www.laminadospai.com/productos/placa-acrilico-transparente-5mm/")
    if h5:
        p5 = re.findall(r'"price"\s*:\s*"?(\d+)"?', h5)
        p5 = [float(p) for p in p5 if 30000 < float(p) < 700000]
        if p5:
            # tomar el mayor que suele ser 1.25x2.47
            max5 = max(p5)
            print(f"  -> Acrílico 5mm precio max {max5}")
            prices.append(max5)
    if prices:
        # Tomar los 2-3 precios más grandes (placa entera)
        # Para 3mm, 310700 es el entero; para 5mm 522500
        # Calcular kg para cada
        kgs = []
        # 3mm entero
        if any(300000 < p < 350000 for p in prices):
            p3 = [p for p in prices if 300000 < p < 350000][0]
            peso3 = 1.25*2.47 * 0.003 * DENSIDADES["acrilico"]  # 11.02
            kgs.append(p3/peso3)
            print(f"  -> Acrílico 3mm 125x247 {round(peso3,2)}kg ${p3} => {round(p3/peso3)}/kg")
        if any(500000 < p < 600000 for p in prices):
            p5m = [p for p in prices if 500000 < p < 600000][0]
            peso5 = 1.25*2.47 * 0.005 * DENSIDADES["acrilico"]  # 18.37
            kgs.append(p5m/peso5)
            print(f"  -> Acrílico 5mm 125x247 {round(peso5,2)}kg ${p5m} => {round(p5m/peso5)}/kg")
        if kgs:
            avg = sum(kgs)/len(kgs)
            print(f"  => Acrílico avg {round(avg)}/kg")
            return round(avg)
    return None

def load_precios_json():
    if JSON_PATH.exists():
        try:
            return json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except:
            pass
    return {
        "fecha": "2026-09-03",
        "precios": DEFAULTS.copy(),
        "fuentes": {}
    }

def update_html(precios_dict, fecha):
    if not HTML_PATH.exists():
        print(f"! No existe {HTML_PATH}")
        return False
    html = HTML_PATH.read_text(encoding="utf-8")
    # Reemplazar bloque preciosInternet
    # Buscar const preciosInternet = { ... };
    pattern = r"const preciosInternet = \{.*?\};"
    nuevo_bloque = f"""const preciosInternet = {{
  acero_carbono: {{ kg: {precios_dict['acero_carbono']}, fuente: "Serviprod" }},
  inox: {{ kg: {precios_dict['inox']}, fuente: "acerosinoxidables.com.ar / Provecom" }},
  aluminio: {{ kg: {precios_dict['aluminio']}, fuente: "Alumina Argentina (Aluar)" }},
  mdf: {{ kg: {precios_dict['mdf']}, fuente: "Sodimac / Maderera" }},
  acrilico: {{ kg: {precios_dict['acrilico']}, fuente: "Laminados PAI" }},
  custom: {{ kg: {precios_dict['acero_carbono']}, fuente: "-" }}
}};"""
    # flags DOTALL
    new_html, n = re.subn(pattern, nuevo_bloque, html, flags=re.DOTALL)
    if n == 0:
        print("! No se encontró bloque preciosInternet para reemplazar")
        return False
    # Actualizar fecha en banner y en fuentes detalladas
    # Banner: Precios de chapas actualizados <b>Sep 2026</b>
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        fecha_str = fecha_dt.strftime("%b %Y").replace("Jan","Ene").replace("Feb","Feb").replace("Mar","Mar").replace("Apr","Abr").replace("May","May").replace("Jun","Jun").replace("Jul","Jul").replace("Aug","Ago").replace("Sep","Sep").replace("Oct","Oct").replace("Nov","Nov").replace("Dec","Dic")
    except:
        fecha_str = fecha
    new_html = re.sub(r"Precios de chapas actualizados <b>.*?</b>", f"Precios de chapas actualizados <b>{fecha_str}</b>", new_html)
    new_html = re.sub(r"Fuentes verificadas .*?:", f"Fuentes verificadas {fecha}:", new_html)
    # También actualizar valor por defecto del input precioKg si es acero
    # No necesario, el JS ya lo carga dinámico
    HTML_PATH.write_text(new_html, encoding="utf-8")
    print(f"[OK] HTML actualizado ({n} reemplazo) -> {HTML_PATH.name}")
    return True

def main():
    print("="*60)
    print(f"Actualizador precios chapas - {datetime.now().isoformat()}")
    print("="*60)
    data = load_precios_json()
    old = data.get("precios", DEFAULTS.copy())
    nuevos = {}
    fuentes_status = {}
    
    scrapers = {
        "acero_carbono": scrape_acero_carbono,
        "inox": scrape_inox,
        "aluminio": scrape_aluminio,
        "mdf": scrape_mdf,
        "acrilico": scrape_acrilico,
    }
    
    for mat, func in scrapers.items():
        try:
            val = func()
            time.sleep(1.2)  # cortesía
            if val and 300 < val < 60000:  # rango válido kg
                # Validar variación: umbral por material (MDF varía mucho por espesor)
                umbral = 0.85 if mat == "mdf" else 0.70
                old_val = old.get(mat, DEFAULTS[mat])
                if old_val and abs(val - old_val)/old_val > umbral:
                    print(f"  ! Variacion excesiva {mat}: {old_val} -> {val} (>{int(umbral*100)}%), se conserva anterior y se alerta")
                    fuentes_status[mat] = f"variacion_excesiva_{val}_conserva_{old_val}"
                    nuevos[mat] = old_val
                else:
                    nuevos[mat] = val
                    fuentes_status[mat] = "ok"
                    print(f"  [OK] {mat}: {old_val} -> {val} $/kg")
            else:
                print(f"  ! {mat}: scrape fallo o valor invalido ({val}), conserva {old.get(mat)}")
                nuevos[mat] = old.get(mat, DEFAULTS[mat])
                fuentes_status[mat] = f"fallo_conserva_{old.get(mat)}"
        except Exception as e:
            print(f"  ! Error {mat}: {e}")
            import traceback; traceback.print_exc()
            nuevos[mat] = old.get(mat, DEFAULTS[mat])
            fuentes_status[mat] = f"error_{e}"
    
    fecha = datetime.now().strftime("%Y-%m-%d")
    # Guardar JSON
    out = {
        "fecha": fecha,
        "precios": nuevos,
        "fuentes": fuentes_status,
        "detalle": "Precios ARS con IVA por kg, relevados automáticamente"
    }
    JSON_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] JSON guardado: {JSON_PATH}")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    
    # Actualizar HTML
    update_html(nuevos, fecha)
    
    # Log
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().isoformat()}] {json.dumps(out, ensure_ascii=False)}\n")
    
    print("\n" + "="*60)
    print("Resumen:")
    for k,v in nuevos.items():
        oldv = old.get(k)
        diff = f" ({v-oldv:+d} { (v/oldv-1)*100:+.1f}%)" if oldv else ""
        print(f"  {k:15s} ${v:5d}/kg{diff}  [{fuentes_status[k]}]")
    print("="*60)
    print("Listo. Recarga la calculadora (F5) para ver los nuevos precios.")
    # Retornar código 0 si al menos 3 OK
    oks = sum(1 for v in fuentes_status.values() if v=="ok")
    if oks < 3:
        print(f"Advertencia: solo {oks}/5 fuentes OK. Revisar log.")

if __name__ == "__main__":
    main()
