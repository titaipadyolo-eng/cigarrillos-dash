"""
Carga histórica (backfill) de incidentes de incautación de cigarrillos
ilegales en Colombia durante 2026, investigados manualmente para poblar
la base de datos antes de que el scraper diario empiece a alimentarla
hacia adelante.

Se ejecuta UNA SOLA VEZ con: python backfill_historico.py
No requiere ANTHROPIC_API_KEY (los datos ya vienen extraídos).

Nota sobre fechas: la mayoría de fechas corresponden a la fecha de
publicación de la noticia (la fecha exacta del operativo no siempre se
reporta). Dos registros (Ipiales 2-jun y Cauca 10-jun) tienen fecha
aproximada porque la fuente no precisó el día exacto.
"""

import db

INCIDENTES_HISTORICOS = [
    {
        "fecha_evento": "2026-03-17",
        "cantidad": 36000,
        "unidad": "cajetillas",
        "cantidad_cigarrillos": 720000,
        "departamento": "La Guajira",
        "municipio": "Maicao",
        "entidad_responsable": "Policía Fiscal y Aduanera (Polfa) y DIAN",
        "resumen": (
            "Operativo vial en Maicao donde la Polfa, en coordinacion con la "
            "Dian, aprehendio un cargamento de 36.000 cajetillas de "
            "cigarrillos de contrabando avaluado en 470 millones de pesos."
        ),
        "titular_noticia": "Policía incauta 720 mil cigarrillos de contrabando en carreteras de La Guajira",
        "url": "https://laguajirahoy.com/judiciales/policia-incauta-720-mil-cigarrillos-de-contrabando-en-carreteras-de-la-guajira.html",
        "medio": "La Guajira Hoy",
    },
    {
        "fecha_evento": "2026-03-26",
        "cantidad": 7000,
        "unidad": "cajetillas",
        "cantidad_cigarrillos": 140000,
        "departamento": "Tolima",
        "municipio": "Herveo",
        "entidad_responsable": "Grupo Operativo Anticontrabando del Tolima (GOAT) y Policía de Tránsito (SETRA)",
        "resumen": (
            "El GOAT intercepto en un punto de control de Herveo un camion con "
            "14 cajas que contenian unas 7.000 cajetillas de cigarrillos de la "
            "marca WIN, avaluadas en 21 millones de pesos, con destino a Cali."
        ),
        "titular_noticia": "Golpe de $21 millones al contrabando: GOAT incauta 7.000 cajetillas ilegales en el norte del Tolima",
        "url": "https://tolima.gov.co/noticias/9419-golpe-de-21-millones-al-contrabando-goat-incauta-7-000-cajetillas-ilegales-en-el-norte-del-tolima",
        "medio": "Gobernación del Tolima",
    },
    {
        "fecha_evento": "2026-04-07",
        "cantidad": 200000,
        "unidad": "cajetillas",
        "cantidad_cigarrillos": 4000000,
        "departamento": "La Guajira",
        "municipio": "Maicao / Riohacha",
        "entidad_responsable": "Policía Fiscal y Aduanera (Polfa), DIAN y Fiscalía General de la Nación",
        "resumen": (
            "Dentro de un operativo simultaneo en 12 ciudades del pais, las "
            "autoridades incautaron en La Guajira 200.000 cajetillas de "
            "cigarrillos de contrabando, junto con licor y pescado de origen "
            "ilegal."
        ),
        "titular_noticia": "Operativos de la POLFA en 12 ciudades: incautan contrabando por más de 5.800 millones de pesos",
        "url": "https://www.minuto30.com/operativos-de-la-polfa-en-12-ciudades-incautan-contrabando-por-mas-de-5-800-millones-de-pesos/1703068/",
        "medio": "Minuto30",
    },
    {
        "fecha_evento": "2026-04-22",
        "cantidad": 14000,
        "unidad": "cajetillas",
        "cantidad_cigarrillos": 280000,
        "departamento": "Nariño",
        "municipio": "Ipiales",
        "entidad_responsable": "Policía Fiscal y Aduanera (Polfa) y DIAN",
        "resumen": (
            "En la frontera con Ecuador, la Policia Fiscal y Aduanera aprehendio "
            "14.000 cajetillas de cigarrillos de origen extranjero empacadas en "
            "cajas de carton, avaluadas en 81.76 millones de pesos, que "
            "presuntamente se distribuirian en Ipiales, Pasto, Popayan y Cali."
        ),
        "titular_noticia": "Millonario contrabando de cigarrillos extranjeros incautado en la frontera entre Colombia y Ecuador",
        "url": "https://www.eltiempo.com/amp/colombia/cali/millonario-contrabando-de-cigarrillos-extranjeros-fue-incautado-por-las-autoridades-en-la-frontera-entre-colombia-y-ecuador-3550025",
        "medio": "El Tiempo",
    },
    {
        "fecha_evento": "2026-05-06",
        "cantidad": 40750,
        "unidad": "cajetillas",
        "cantidad_cigarrillos": 815000,
        "departamento": "Nariño",
        "municipio": "Ipiales",
        "entidad_responsable": "Policía Fiscal y Aduanera (Polfa), DIAN y Ejército Nacional",
        "resumen": (
            "Tres allanamientos en zona rural de Ipiales (vereda Yaramal) "
            "permitieron hallar 40.750 cajetillas de cigarrillos de "
            "contrabando avaluadas en 137 millones de pesos. Tambien se "
            "encontro un arma de fuego y se capturaron dos personas."
        ),
        "titular_noticia": "Policía Fiscal y Aduanera incautó 40.750 cajetillas de cigarrillos de contrabando en la frontera con Ecuador",
        "url": "https://www.elpais.com.co/judicial/policia-fiscal-y-aduanera-incauto-40750-cajetillas-de-cigarrillos-de-contrabando-en-la-frontera-con-ecuador-0608.html",
        "medio": "El País",
    },
    {
        "fecha_evento": "2026-05-16",
        "cantidad": 94500,
        "unidad": "cajetillas",
        "cantidad_cigarrillos": 1890000,
        "departamento": "La Guajira",
        "municipio": "Maicao",
        "entidad_responsable": "Unipol (Policía Nacional) y Ejército Nacional",
        "resumen": (
            "En zona rural de Maicao (vereda La Paz), unidades de Unipol junto "
            "con el Ejercito hallaron 94.500 cajetillas de cigarrillos de "
            "contrabando y un arma traumatica, tras la huida de tres personas "
            "que abandonaron tres vehiculos en el lugar."
        ),
        "titular_noticia": "Policía incauta millonario cargamento de cigarrillos de contrabando en área rural de Maicao",
        "url": "https://www.elheraldo.co/la-guajira/2026/05/16/policia-incauta-millonario-cargamento-de-cigarrillos-de-contrabando-en-area-rural-de-maicao/",
        "medio": "El Heraldo",
    },
    {
        "fecha_evento": "2026-06-02",
        "cantidad": 411500,
        "unidad": "cajetillas",
        "cantidad_cigarrillos": 8230000,
        "departamento": "Nariño",
        "municipio": "Ipiales",
        "entidad_responsable": "Policía Nacional, DIAN y Ejército Nacional (Batallón Energético Vial N.° 20)",
        "resumen": (
            "Operacion conjunta en el perimetro urbano de Ipiales permitio "
            "aprehender 411.500 cajetillas de cigarrillos de origen extranjero "
            "que eran transportadas en varios vehiculos de carga sin la "
            "documentacion legal requerida."
        ),
        "titular_noticia": "Contundente ofensiva contra el contrabando en la frontera sur del país",
        "url": "https://www.policia.gov.co/noticia/contundente-ofensiva-contra-contrabando-en-frontera-sur-del-pais",
        "medio": "Policía Nacional de Colombia",
    },
    {
        "fecha_evento": "2026-06-10",
        "cantidad": 65500,
        "unidad": "cajetillas",
        "cantidad_cigarrillos": 1310000,
        "departamento": "Cauca",
        "municipio": "Santander de Quilichao",
        "entidad_responsable": "Policía Metropolitana de Cali",
        "resumen": (
            "Decomiso record en el norte del Cauca: 65.500 cajetillas de "
            "cigarrillos que habrian ingresado por contrabando a traves del "
            "puerto de Buenaventura bajo la modalidad de transito aduanero, "
            "avaluadas en 248 millones de pesos. Se desmantelo una bodega "
            "clandestina y se capturo a una persona."
        ),
        "titular_noticia": "Gigantesco decomiso de contrabando: 65.500 cajetillas de cigarrillos por $248 millones",
        "url": "https://www.eltiempo.com/colombia/cali/decomiso-record-por-contrabando-65-500-cajetillas-de-cigarrillo-destino-ecuador-822558",
        "medio": "El Tiempo",
    },
]


def cargar_historico():
    db.init_db()
    insertados = 0
    for registro in INCIDENTES_HISTORICOS:
        if db.url_ya_procesada(registro["url"]):
            print(f"Ya existia, se omite: {registro['titular_noticia']}")
            continue
        incidente_id = db.insertar_incidente(registro)
        db.marcar_url_procesada(registro["url"], es_relevante=True, incidente_id=incidente_id)
        print(f"[incidente {incidente_id}] {registro['fecha_evento']} - {registro['titular_noticia']}")
        insertados += 1
    print(f"\nListo. {insertados} incidentes históricos cargados.")


if __name__ == "__main__":
    cargar_historico()
