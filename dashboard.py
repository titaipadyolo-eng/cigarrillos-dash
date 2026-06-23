"""
Dashboard de incautaciones de cigarrillos ilegales en Colombia.

Ejecutar con: streamlit run dashboard.py
Lee directamente de data/incidentes.db (la misma base que alimenta scraper.py).
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "incidentes.db"

MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

st.set_page_config(page_title="Incautaciones de cigarrillos ilegales · Colombia", layout="wide")


@st.cache_data(ttl=300)
def cargar_datos():
    if not DB_PATH.exists():
        return pd.DataFrame(), pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    incidentes = pd.read_sql_query("SELECT * FROM incidentes", conn)
    fuentes = pd.read_sql_query("SELECT * FROM fuentes", conn)
    conn.close()
    return incidentes, fuentes


incidentes, fuentes = cargar_datos()

st.title("Incautaciones de cigarrillos ilegales en Colombia")

if incidentes.empty:
    st.warning(
        "Todavia no hay datos. Corre `python scraper.py` (con tu "
        "ANTHROPIC_API_KEY configurada) para empezar a poblar la base de datos, "
        "o espera a que corra el GitHub Action diario."
    )
    st.stop()

anios_disponibles = sorted(incidentes["anio"].dropna().unique().astype(int), reverse=True)
meses_disponibles = sorted(incidentes["mes"].dropna().unique().astype(int))

col_f1, col_f2 = st.columns(2)
with col_f1:
    anios_sel = st.multiselect("Año", anios_disponibles, default=anios_disponibles)
with col_f2:
    meses_sel = st.multiselect(
        "Mes", meses_disponibles, default=meses_disponibles,
        format_func=lambda m: MESES.get(int(m), m),
    )

filtrado = incidentes[incidentes["anio"].isin(anios_sel) & incidentes["mes"].isin(meses_sel)].copy()

if filtrado.empty:
    st.info("No hay incidentes para el período seleccionado.")
    st.stop()

filtrado["cantidad_cigarrillos"] = filtrado["cantidad_cigarrillos"].fillna(0)

total_cigarrillos = filtrado["cantidad_cigarrillos"].sum()
num_operativos = len(filtrado)
promedio = total_cigarrillos / num_operativos if num_operativos else 0

c1, c2, c3 = st.columns(3)
c1.metric("Cigarrillos incautados (estimado)", f"{int(total_cigarrillos):,}")
c2.metric("Operativos registrados", num_operativos)
c3.metric("Promedio por operativo", f"{int(promedio):,}")

st.subheader("Top 3 noticias con mayor incautación")
top3 = filtrado.sort_values("cantidad_cigarrillos", ascending=False).head(3)
for _, fila in top3.iterrows():
    with st.container(border=True):
        st.markdown(f"**{fila['titular_principal'] or 'Sin titular'}**")
        st.write(
            f"{int(fila['cantidad_cigarrillos']):,} cigarrillos estimados · "
            f"{fila['municipio'] or ''}, {fila['departamento'] or 'lugar no identificado'} · "
            f"{fila['fecha_evento'] or fila['fecha_publicacion'] or 'fecha no identificada'}"
        )
        fuentes_inc = fuentes[fuentes["incidente_id"] == fila["id"]]
        enlaces = " · ".join(
            f"[{f['medio'] or 'fuente'}]({f['url']})" for _, f in fuentes_inc.iterrows() if f["url"]
        )
        if enlaces:
            st.markdown(enlaces)
        if len(fuentes_inc) > 1:
            st.caption(f"Reportado por {len(fuentes_inc)} fuentes distintas")

st.subheader("Top lugares con más incautaciones")
top_lugares = (
    filtrado.dropna(subset=["departamento"])
    .groupby("departamento")["cantidad_cigarrillos"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)
if not top_lugares.empty:
    fig_lugares = px.bar(
        top_lugares, x="departamento", y="cantidad_cigarrillos",
        labels={"departamento": "Departamento", "cantidad_cigarrillos": "Cigarrillos incautados"},
    )
    st.plotly_chart(fig_lugares, use_container_width=True)
else:
    st.caption("Sin datos de ubicación suficientes para este período.")

st.subheader("Tendencia mensual")
tendencia = (
    filtrado.groupby(["anio", "mes"])["cantidad_cigarrillos"]
    .sum()
    .reset_index()
    .sort_values(["anio", "mes"])
)
tendencia["periodo"] = tendencia.apply(
    lambda r: f"{MESES.get(int(r['mes']), r['mes'])} {int(r['anio'])}", axis=1
)
fig_tendencia = px.line(
    tendencia, x="periodo", y="cantidad_cigarrillos", markers=True,
    labels={"periodo": "Período", "cantidad_cigarrillos": "Cigarrillos incautados"},
)
st.plotly_chart(fig_tendencia, use_container_width=True)

st.subheader("Detalle de incidentes")
columnas_mostrar = ["fecha_evento", "departamento", "municipio", "entidad",
                    "cantidad_cigarrillos", "titular_principal"]
st.dataframe(
    filtrado[columnas_mostrar].sort_values("fecha_evento", ascending=False),
    use_container_width=True,
)
