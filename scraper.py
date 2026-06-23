"""
Scraper diario de noticias sobre incautaciones de cigarrillos ilegales
en Colombia.

Flujo:
1. Busca noticias recientes en Google News RSS (sin necesidad de API key).
2. Descarga el texto completo de cada artículo nuevo.
3. Le pide a Claude que extraiga datos estructurados (fecha, cantidad,
   lugar, entidad) y que decida si la noticia es relevante.
4. Antes de insertar, busca si ya existe un incidente "parecido" (mismo
   departamento, fecha cercana) y le pregunta a Claude si es el MISMO
   operativo reportado por otra fuente. Si es así, no duplica el
   conteo: solo agrega el link como fuente adicional.

Requiere la variable de entorno ANTHROPIC_API_KEY.
Se ejecuta con: python scraper.py
"""

import json
import time
from datetime import datetime
from urllib.parse import quote_plus

import feedparser
import trafilatura
import anthropic

import db

# Modelo económico (Haiku) porque se procesan muchos artículos por día.
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

CONSULTAS = [
    "incautación cigarrillos ilegales Colombia",
    "aprehensión cigarrillos contrabando Colombia",
    "decomiso cigarrillos ilegales Colombia",
    "contrabando de cigarrillos Colombia",
    "DIAN cigarrillos ilegales",
    "Policía Nacional cigarrillos contrabando",
    "Ejército incautación cigarrillos",
]

PROMPT_EXTRACCION = """Eres un analista que revisa noticias colombianas sobre \
incautaciones de cigarrillos ilegales o de contrabando.

Lee la noticia y responde UNICAMENTE con un JSON (sin texto adicional, sin \
markdown, sin backticks) con esta forma exacta:

{{
  "es_relevante": true o false,
  "fecha_evento": "YYYY-MM-DD" o null,
  "cantidad": numero o null,
  "unidad": "cigarrillos" o "cajetillas" o "millares" o "toneladas" o "cajas" o null,
  "cantidad_cigarrillos": numero entero estimado de cigarrillos individuales o null,
  "departamento": string o null,
  "municipio": string o null,
  "entidad_responsable": string o null,
  "resumen": "resumen de maximo 2 frases en espanol",
  "titular_noticia": "string"
}}

Reglas:
- "es_relevante" es true SOLO si la noticia trata sobre una incautacion, \
decomiso o aprehension de cigarrillos ilegales o de contrabando en Colombia \
(no aplica a tabaco en rama, vapeadores, licores ni otros productos de \
contrabando).
- Para normalizar "cantidad_cigarrillos": 1 cajetilla equivale aprox. a 20 \
cigarrillos, 1 millar equivale a 1000 cigarrillos. Si el dato viene en \
toneladas o cajas sin mas detalle, intenta una estimacion razonable; si no \
es posible, deja el campo en null.
- Si no puedes determinar un campo, usa null. No inventes datos que no \
estan en el texto.

Titulo de la noticia: {titulo}

Texto de la noticia: {texto}
"""

PROMPT_DEDUP = """Compara estos dos reportes de operativos de incautacion de \
cigarrillos ilegales en Colombia y determina si describen el MISMO \
operativo (mismo lugar y fecha cercana, aunque la fuente que lo reporta sea \
distinta) o si son operativos DIFERENTES.

Reporte A: {a}

Reporte B: {b}

Responde UNICAMENTE con JSON: {{"mismo_operativo": true o false}}
"""


def cliente_anthropic():
    return anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno


def _extraer_json(texto_respuesta):
    texto = texto_respuesta.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.lower().startswith("json"):
            texto = texto[4:]
    return json.loads(texto.strip())


def analizar_noticia(client, titulo, texto_articulo):
    prompt = PROMPT_EXTRACCION.format(titulo=titulo, texto=texto_articulo[:6000])
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extraer_json(resp.content[0].text)


def es_mismo_operativo(client, resumen_a, resumen_b):
    prompt = PROMPT_DEDUP.format(a=resumen_a, b=resumen_b)
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=50,
        messages=[{"role": "user", "content": prompt}],
    )
    data = _extraer_json(resp.content[0].text)
    return bool(data.get("mismo_operativo"))


def _parsear_fecha(entry):
    try:
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if not parsed:
            return None
        return datetime(*parsed[:6]).strftime("%Y-%m-%d")
    except Exception:
        return None


def obtener_entradas_rss():
    entradas = []
    vistos = set()
    for consulta in CONSULTAS:
        url_rss = (
            f"https://news.google.com/rss/search?q={quote_plus(consulta)}"
            "&hl=es-419&gl=CO&ceid=CO:es"
        )
        feed = feedparser.parse(url_rss)
        for entry in feed.entries:
            link = entry.get("link")
            if not link or link in vistos:
                continue
            vistos.add(link)
            fuente = entry.get("source", {})
            entradas.append({
                "url": link,
                "titulo": entry.get("title", ""),
                "medio": fuente.get("title", "") if isinstance(fuente, dict) else "",
                "fecha_publicacion": _parsear_fecha(entry),
            })
    return entradas


def descargar_texto(url):
    try:
        descargado = trafilatura.fetch_url(url)
        if not descargado:
            return ""
        return trafilatura.extract(descargado) or ""
    except Exception:
        return ""


def procesar():
    db.init_db()
    client = cliente_anthropic()
    entradas = obtener_entradas_rss()
    print(f"Encontradas {len(entradas)} noticias en RSS (antes de filtrar ya procesadas).")

    nuevos, duplicados, descartados, errores = 0, 0, 0, 0

    for entrada in entradas:
        url = entrada["url"]
        if db.url_ya_procesada(url):
            continue

        texto = descargar_texto(url)
        if not texto or len(texto) < 200:
            db.marcar_url_procesada(url, es_relevante=False)
            continue

        try:
            extraido = analizar_noticia(client, entrada["titulo"], texto)
        except Exception as e:
            print(f"Error analizando {url}: {e}")
            errores += 1
            continue

        if not extraido.get("es_relevante"):
            db.marcar_url_procesada(url, es_relevante=False)
            descartados += 1
            continue

        extraido["url"] = url
        extraido["medio"] = entrada.get("medio")
        if not extraido.get("fecha_evento"):
            extraido["fecha_evento"] = entrada.get("fecha_publicacion")
        extraido["fecha_publicacion"] = entrada.get("fecha_publicacion") or extraido.get("fecha_evento")

        candidatos = db.buscar_candidatos_duplicado(
            extraido.get("fecha_evento"), extraido.get("departamento")
        )

        incidente_existente = None
        for candidato in candidatos:
            try:
                if es_mismo_operativo(client, candidato.get("resumen", ""), extraido.get("resumen", "")):
                    incidente_existente = candidato
                    break
            except Exception:
                continue

        if incidente_existente:
            db.agregar_fuente_a_incidente(incidente_existente["id"], extraido)
            db.marcar_url_procesada(url, es_relevante=True, incidente_id=incidente_existente["id"])
            duplicados += 1
            print(f"[duplicado fusionado] {url} -> incidente {incidente_existente['id']}")
        else:
            incidente_id = db.insertar_incidente(extraido)
            db.marcar_url_procesada(url, es_relevante=True, incidente_id=incidente_id)
            nuevos += 1
            print(f"[nuevo incidente {incidente_id}] {extraido.get('titular_noticia')}")

        time.sleep(1)  # margen prudente entre llamadas a la API

    print(
        f"\nResumen: nuevos={nuevos} | duplicados fusionados={duplicados} "
        f"| descartados (no relevantes)={descartados} | errores={errores}"
    )


if __name__ == "__main__":
    procesar()
