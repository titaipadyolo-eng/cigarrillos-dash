# Dashboard de incautaciones de cigarrillos ilegales — Colombia

Sistema que lee noticias todos los días, extrae los datos de cada operativo
de incautación/aprehensión de cigarrillos ilegales con la API de Claude, evita
contar dos veces el mismo operativo cuando varios medios lo reportan, y
alimenta un dashboard filtrable por mes y año.

## Cómo funciona

1. **`scraper.py`** busca noticias recientes en Google News RSS (sin
   necesitar ninguna API key de noticias), descarga el texto de cada
   artículo nuevo y le pide a Claude que extraiga: fecha del operativo,
   cantidad (normalizada a cigarrillos individuales), departamento,
   municipio, entidad responsable y un resumen corto.
2. **Deduplicación**: antes de guardar un registro nuevo, el sistema busca
   en la base de datos incidentes en el mismo departamento y en una
   ventana de ±5 días. Si encuentra alguno, le pregunta a Claude si los dos
   resúmenes describen el mismo operativo. Si la respuesta es sí, **no se
   crea un incidente nuevo** (evita inflar el conteo de cigarrillos): el
   artículo se guarda solo como una fuente adicional del incidente ya
   existente. Así, una misma incautación reportada por 5 medios distintos
   cuenta una sola vez en las cifras, pero conservas los 5 links como
   evidencia.
3. **`db.py`** guarda todo en SQLite (`data/incidentes.db`), con dos tablas
   principales: `incidentes` (un registro por operativo real) y `fuentes`
   (todos los artículos que reportaron cada incidente).
4. **`dashboard.py`** (Streamlit) lee esa base de datos y muestra:
   - Filtros por año y mes.
   - Total de cigarrillos incautados, número de operativos, promedio.
   - Top 3 noticias con mayor incautación (con sus links de fuente).
   - Top 10 departamentos con más cigarrillos incautados.
   - Tendencia mensual.
   - Tabla detallada de todos los incidentes del período.
5. **`.github/workflows/scraper_diario.yml`** corre `scraper.py`
   automáticamente todos los días a las 7am hora Colombia, usando GitHub
   Actions (gratis para repos públicos y con buen margen gratuito para
   privados), y guarda los cambios de la base de datos en el repositorio.

## Por qué corre "afuera" y no dentro de un chat

Una conversación de Claude no se ejecuta sola cada día — necesita que tú
(o un cron) la invoquen. Por eso el scraping diario vive en GitHub Actions:
es gratis, no requiere servidor propio, y simplemente llama a la API de
Claude con tu propia llave.

## Instalación local (para probar)

```bash
git clone <tu-repositorio>
cd cigarrillos-dashboard
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY="tu-api-key-aqui"

# Correr el scraper una vez para poblar datos
python scraper.py

# Levantar el dashboard
streamlit run dashboard.py
```

## Despliegue completo (gratis)

1. **Sube este proyecto a un repositorio de GitHub** (puede ser privado).
2. **Agrega tu API key como secreto**: en el repo, ve a
   `Settings → Secrets and variables → Actions → New repository secret`,
   nombre `ANTHROPIC_API_KEY`, y pega tu llave de
   [console.anthropic.com](https://console.anthropic.com).
3. El workflow en `.github/workflows/scraper_diario.yml` ya queda corriendo
   solo cada día (también puedes ejecutarlo manualmente desde la pestaña
   *Actions* → *Run workflow*).
4. **Dashboard**: crea una cuenta gratis en
   [share.streamlit.io](https://share.streamlit.io), conecta el mismo
   repositorio y selecciona `dashboard.py` como archivo principal. Cada vez
   que el scraper haga `git push` con datos nuevos, Streamlit Cloud
   refleja la base de datos actualizada.

## Costos a tener en cuenta

- GitHub Actions: gratis dentro de los límites estándar para este volumen
  (una corrida diaria corta).
- Streamlit Community Cloud: gratis.
- API de Claude: se usa el modelo Haiku (económico) tanto para extracción
  como para la comparación de duplicados. El costo depende del volumen de
  noticias diarias, pero para este caso de uso (decenas de artículos al
  día) suele ser de unos pocos dólares al mes. Puedes revisar tu consumo
  en el dashboard de uso de [console.anthropic.com](https://console.anthropic.com).

## Limitaciones a tener en cuenta

- La cantidad de cigarrillos depende de lo que la noticia reporte
  explícitamente; si el medio no da una cifra clara, el campo queda en
  `null` y ese incidente no suma al total (pero sí aparece en el detalle).
- La deduplicación es semántica (vía IA), no perfecta: operativos muy
  similares en el mismo departamento y semana, pero genuinamente distintos,
  podrían fusionarse por error en casos ambiguos. Puedes ajustar la
  ventana de días en `db.py` (`dias_ventana`) si ves falsos positivos.
- Google News RSS no cubre el 100% de medios regionales; si tienes medios
  específicos que quieres asegurar (ej. un diario regional), se le puede
  agregar su feed RSS directo a la lista `CONSULTAS` en `scraper.py`.

## Próximos pasos sugeridos

- Agregar más fuentes (comunicados oficiales de Policía/DIAN/Ejército,
  que suelen tener cifras más precisas que la prensa).
- Exportar reportes mensuales en PDF o Excel directamente desde el
  dashboard.
- Agregar un mapa de Colombia con las incautaciones por departamento.
