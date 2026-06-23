"""
Capa de acceso a datos (SQLite) para el sistema de monitoreo de
incautaciones de cigarrillos ilegales en Colombia.

Tablas:
- incidentes: un registro por operativo (ya deduplicado entre fuentes)
- fuentes: todos los artículos/links que reportaron ese mismo operativo
- urls_procesadas: control para no volver a leer/analizar la misma noticia
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "data" / "incidentes.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_evento TEXT,
    fecha_publicacion TEXT,
    anio INTEGER,
    mes INTEGER,
    cantidad_raw TEXT,
    unidad_raw TEXT,
    cantidad_cigarrillos INTEGER,
    departamento TEXT,
    municipio TEXT,
    entidad TEXT,
    resumen TEXT,
    titular_principal TEXT,
    url_principal TEXT,
    creado_en TEXT
);

CREATE TABLE IF NOT EXISTS fuentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incidente_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    medio TEXT,
    titular TEXT,
    fecha_publicacion TEXT,
    FOREIGN KEY (incidente_id) REFERENCES incidentes(id)
);

CREATE TABLE IF NOT EXISTS urls_procesadas (
    url TEXT PRIMARY KEY,
    es_relevante INTEGER,
    incidente_id INTEGER,
    procesado_en TEXT
);
"""


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def url_ya_procesada(url):
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM urls_procesadas WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row is not None


def marcar_url_procesada(url, es_relevante, incidente_id=None):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO urls_procesadas
           (url, es_relevante, incidente_id, procesado_en) VALUES (?, ?, ?, ?)""",
        (url, int(bool(es_relevante)), incidente_id, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def buscar_candidatos_duplicado(fecha_evento, departamento, dias_ventana=5):
    """
    Trae incidentes ya registrados en el mismo departamento y en una
    ventana de +/- N días respecto a la fecha del evento. Estos son los
    'candidatos' que luego se comparan semánticamente para decidir si
    son el mismo operativo reportado por otra fuente.
    """
    if not fecha_evento or not departamento:
        return []
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM incidentes
        WHERE departamento = ?
          AND fecha_evento IS NOT NULL
          AND ABS(julianday(fecha_evento) - julianday(?)) <= ?
        """,
        (departamento, fecha_evento, dias_ventana),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insertar_incidente(data):
    conn = get_connection()
    fecha = data.get("fecha_evento") or data.get("fecha_publicacion")
    anio = int(fecha[:4]) if fecha else None
    mes = int(fecha[5:7]) if fecha else None
    cur = conn.execute(
        """
        INSERT INTO incidentes
        (fecha_evento, fecha_publicacion, anio, mes, cantidad_raw, unidad_raw,
         cantidad_cigarrillos, departamento, municipio, entidad, resumen,
         titular_principal, url_principal, creado_en)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("fecha_evento"),
            data.get("fecha_publicacion"),
            anio, mes,
            str(data.get("cantidad")),
            data.get("unidad"),
            data.get("cantidad_cigarrillos"),
            data.get("departamento"),
            data.get("municipio"),
            data.get("entidad_responsable"),
            data.get("resumen"),
            data.get("titular_noticia"),
            data.get("url"),
            datetime.utcnow().isoformat(),
        ),
    )
    incidente_id = cur.lastrowid
    conn.execute(
        """INSERT INTO fuentes (incidente_id, url, medio, titular, fecha_publicacion)
           VALUES (?, ?, ?, ?, ?)""",
        (incidente_id, data.get("url"), data.get("medio"),
         data.get("titular_noticia"), data.get("fecha_publicacion")),
    )
    conn.commit()
    conn.close()
    return incidente_id


def agregar_fuente_a_incidente(incidente_id, data):
    """Cuando una noticia resulta ser el MISMO operativo ya registrado,
    no se crea un incidente nuevo (evita doble conteo): solo se añade
    el link como fuente adicional de ese incidente."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO fuentes (incidente_id, url, medio, titular, fecha_publicacion)
           VALUES (?, ?, ?, ?, ?)""",
        (incidente_id, data.get("url"), data.get("medio"),
         data.get("titular_noticia"), data.get("fecha_publicacion")),
    )
    conn.commit()
    conn.close()
