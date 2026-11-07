# StreamView Analytics — EV3 / EP5

Proyecto de Visualización de Datos (ADY1104). La base de trabajo es la integración de películas y series desarrollada y validada en EV2. EV1 no se utiliza como referencia para las correcciones de esta entrega.

Repositorio: https://github.com/carlos31255/EV3_Visualizacion_datos

## Problema y audiencia

Apoyar a la Gerencia de Contenido y a la Dirección Ejecutiva en la exploración de películas, series, géneros y países para orientar la evaluación de oportunidades de adquisición.

**Pregunta:** ¿qué señales de popularidad relativa, calificación y oferta por género y país pueden orientar la selección de contenidos?

Los datos permiten formular recomendaciones exploratorias. No permiten determinar una distribución óptima del presupuesto ni medir retención, reproducciones o engagement real de usuarios.

## Fuentes y alcance

| Archivo de entrada en `data/raw/` | Registros originales | Registros tras deduplicación |
|---|---:|---:|
| `netflix_movies_detailed_up_to_2025.csv` | 16.000 | 16.000 |
| `netflix_tv_shows_detailed_up_to_2025.csv` | 16.000 | 15.991 |
| **Total** | **32.000** | **31.991** |

Los archivos abarcan 2010–2025. Cada fuente contiene originalmente 1.000 títulos por año; tras eliminar nueve duplicados, series de 2025 queda con 991 títulos. Esta distribución no permite inferir la composición temporal del catálogo real.

Variables centrales: identificador, tipo, título, año, géneros, países, idioma, directores, popularidad, cantidad de votos y calificación. Presupuesto y recaudación están disponibles solo para películas.

## Organización prevista para la entrega

Esta tabla describe la estructura que debe completarse en el proyecto local; no certifica que todos los archivos ya estén publicados en GitHub.

| Ruta | Contenido |
|---|---|
| `data/raw/` | Los dos CSV originales |
| `data/processed/` | Tablas generadas por limpieza, KPIs y controles |
| `src/limpieza.py` | Integración, limpieza y controles de calidad |
| `src/kpis.py` | KPIs y tabla maestra destinada a Looker Studio |
| `notebooks/01_integracion_y_limpieza.ipynb` | Evidencias de integración y diccionario |
| `notebooks/02_eda_visualizaciones.ipynb` | EDA, ocho gráficos G1–G8 y controles de consistencia |
| `images/` | Ocho PNG generados por el notebook EDA |
| `dashboard/` | Capturas finales, PDF del dashboard, PDF de la infografía y enlace verificado |
| `reports/` | Informe ejecutivo y resumen ejecutivo para EP5 |
| `glosario.md` | Definiciones de variables, métricas y limitaciones |
| `requirements.txt` | Dependencias Python |

`dashboard/` debe completarse después de corregir Looker Studio. El informe ejecutivo final debe entregarse en PDF y el resumen ejecutivo en PDF o PowerPoint, conforme a EP5.

## Instalación

Usar Python 3.10 o superior en un entorno virtual. Las dependencias tienen versiones mínimas; no se garantiza cualquier combinación futura sin comprobarla.

Desde la raíz del proyecto, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si utilizas Git Bash, activa el mismo entorno con:

```bash
source .venv/Scripts/activate
```

Looker Studio funciona en el navegador y no requiere Streamlit, Plotly ni Seaborn. Esas dependencias se retiraron conforme a la revisión de EV2.

## Reproducción

Antes de ejecutar, confirma que están presentes ambos CSV en `data/raw/`, los dos scripts de `src/` y los dos notebooks. Este README y `requirements.txt` no sustituyen esos archivos.

Desde la raíz, con el entorno activo:

```bash
python src/limpieza.py
python src/kpis.py
```

Después inicia Jupyter desde `notebooks/`, porque las rutas de los cuadernos actuales toman su carpeta padre como raíz:

```bash
cd notebooks
jupyter notebook
```

Abre y ejecuta con **Restart Kernel and Run All Cells**, en este orden:

1. `01_integracion_y_limpieza.ipynb`.
2. `02_eda_visualizaciones.ipynb`.

El primer cuaderno vuelve a ejecutar la limpieza con exportación. Si se modifican datos o reglas de limpieza, regenera también los KPIs antes del segundo cuaderno para evitar comparar archivos de versiones distintas.

Las salidas utilizadas por los notebooks incluyen:

- `contenido_unificado.csv`.
- `contenido_por_genero.csv`.
- `contenido_por_pais.csv`.
- `contenido_por_director.csv`.
- `looker_contenido.csv`.

El notebook EDA exporta `cifras_clave_eda.csv`, `control_g4_vs_looker.csv`, `control_g6_vs_looker.csv` y `control_g8_vs_looker.csv` en `data/processed/`.

## Criterios metodológicos

- **Identificación:** `content_id` usa prefijos `M-` y `S-`; los 397 identificadores originales compartidos entre fuentes no se consideran duplicados entre tipos.
- **Duplicados de series:** conservar la fila con más votos y, en caso de empate, mayor popularidad.
- **Calificación:** `vote_average_clean` excluye títulos sin votos. El umbral de ≥10 votos es un criterio operativo de selección, no una garantía estadística de confiabilidad.
- **Popularidad relativa:** `indice_engagement` conserva su nombre técnico por compatibilidad, pero es un percentil de popularidad dentro de cada tipo. No mide consumo ni permite comparar niveles absolutos entre películas y series.
- **Alto engagement:** percentil ≥75; su proporción global ronda el 25 % por construcción y resulta más informativa al explorar subconjuntos.
- **Título estrella:** percentil ≥75, nota ≥7 y ≥10 votos. No está fijado al 25 %, porque combina tres condiciones.
- **Géneros:** se homologan ambas taxonomías y se evita contar dos veces el mismo título dentro de un género unificado. Los 628 telefilms se mantienen como títulos, pero `TV Movie` se excluye de la dimensión de género.
- **Finanzas:** 3.540 películas tienen presupuesto y recaudación mayores que cero. La variable `roi` es recaudación/presupuesto, un múltiplo bruto, no rentabilidad neta. 1× solo iguala el presupuesto registrado.
- **Atribución:** el EDA cuenta todas las categorías de cada título; Looker utiliza género, país y director principal. Las diferencias esperadas se documentan mediante los controles exportados.

## Visualizaciones de la base EV2

| Gráfico | Contenido |
|---|---|
| G1 | Calificación por tipo y cobertura de títulos con ≥10 votos |
| G2 | Distribución de popularidad mediante boxplots |
| G3 | Popularidad relativa mediana y calificación por género, separados por tipo |
| G4 | Presencia de géneros sobre el total de títulos de cada tipo |
| G5 | Calificación y cobertura de votos por año de estreno |
| G6 | Países de producción por tipo |
| G7 | Asociación entre popularidad relativa y calificación mediante hexbin |
| G8 | Múltiplo bruto recaudación/presupuesto por director, solo películas |

G1 y G5 promedian títulos con votos; G3 y G7 restringen la calificación a títulos con ≥10 votos. En G3, la popularidad mediana se calcula sobre todos los títulos del género: las bases de ambas métricas deben explicitarse al reproducirlo en otra herramienta.

## Validación y estado de EV3

La retroalimentación de EV2 confirmó la reproducción del pipeline, 17 controles de calidad y 360 comparaciones de métricas. Esto documenta la base validada; no sustituye una ejecución nueva de EV3.

Referencias de EV2 para contrastar después de ejecutar:

| Indicador | Valor |
|---|---:|
| Títulos | 31.991 |
| Calificación media con votos, películas | 6,31 |
| Calificación media con votos, series | 7,02 |
| Títulos con ≥10 votos, conjunto integrado | 63,55 % |
| Alto engagement, conjunto integrado | 25,01 % |
| Títulos estrella, conjunto integrado | 8,47 % |
| Cobertura financiera de películas | 22,13 % |
| Múltiplo financiero agregado | 2,92× |
| Múltiplo financiero mediano | 1,70× |

Estos valores son referencias del dataset base, no metas de negocio.

Pendientes de cierre:

- Corregir las etiquetas superpuestas del panel de series en G3 y revisar los textos metodológicos del EDA.
- Ejecutar la versión final desde un entorno limpio y comprobar tablas, ocho PNG y controles.
- Completar las mejoras de Looker Studio: filtrado cruzado comprobado, separación por tipo, paleta consistente, comparaciones de KPIs y representación gráfica financiera.
- Ampliar la infografía para incluir series y países; retirar los controles de navegación de su exportación.
- Incorporar el enlace real y verificado del dashboard al cerrar esa etapa. Actualmente no se publica un enlace en este documento.
- Completar `dashboard/`, el informe y el resumen ejecutivo; revisar que sus cifras correspondan a la misma ejecución.

No se declara drill-down como implementado. La documentación final debe describir únicamente las interacciones verificadas y los ejes reales de la infografía corregida.
