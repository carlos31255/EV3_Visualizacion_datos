# Glosario de Variables y Métricas — StreamView Analytics (EV3 / EP5)

Tabla prevista como fuente única del dashboard y de la infografía, generada por `src/kpis.py`:
- `data/processed/looker_contenido.csv`: tabla maestra de 31.991 filas (una fila por título) y 22 columnas. Fuente única prevista para Looker Studio; su revisión final queda pendiente.
- `data/processed/looker_genero.csv`: tabla desagregada por género utilizada exclusivamente para contraste y verificación interna frente a los notebooks. No se conecta a Looker Studio.

Las fórmulas siguientes definen cómo deben responder los indicadores a los filtros; su funcionamiento en Looker se verificará al final. Las proporciones agregadas se calculan como la suma del numerador dividida por el total de registros del subconjunto, evitando el promedio de porcentajes precalculados.

---

## 1. Variables del dataset maestro (`looker_contenido.csv`)

* **content_id:** Identificador alfanumérico único por título ("M-" para películas y "S-" para series). Llave primaria que resuelve el solapamiento de identificadores originales entre formatos.
* **title:** Nombre oficial de la obra audiovisual.
* **tipo_contenido:** Clasificación del formato entre Película y Serie.
* **es_pelicula:** Variable binaria que asigna valor 1 a películas y 0 a series.
* **release_year:** Año de estreno oficial de la obra, en formato numérico entero (2010 a 2025). Permite control temporal continuo.
* **idioma:** Nombre del idioma original en español cuando existe traducción en `IDIOMAS`; en los demás casos conserva el código original.
* **genero_principal:** Primer género registrado del título según la taxonomía homologada en español. Asigna "No especificado" si carece de registro. Omite la categoría "TV Movie", pero conserva las películas que la contienen.
* **pais_principal:** Primer país de producción registrado, normalizado al español. Asigna "No especificado" si carece de registro.
* **director_principal:** Primer director registrado. Unifica la variante "Anthony Russo / Joe Russo" y asigna "No especificado" en obras sin registro.
* **popularity:** Índice de popularidad bruto suministrado por la fuente. Estos CSV no contienen reproducciones ni actividad individual de usuarios.
* **indice_engagement:** Percentil de `popularity` dentro de cada tipo, calculado con `rank(pct=True) * 100` y redondeado a dos decimales. Mide posición relativa; no mide engagement real ni permite comparar consumo absoluto entre películas y series.
* **alto_engagement:** Indicador binario con valor 1 si el título pertenece al percentil 75 o superior de su tipo (grupo de mayor popularidad relativa), y 0 en caso contrario.
* **es_estrella:** Indicador binario con valor 1 si el título cumple conjuntamente: percentil de popularidad relativa ≥ 75, calificación promedio ≥ 7,0 y respaldo de al menos 10 votos.
* **vote_count:** Conteo total de evaluaciones emitidas por los usuarios.
* **vote_average_clean:** Calificación promedio de la audiencia en escala 0 a 10. Contiene valor nulo para títulos con 0 votos para evitar el sesgo de calificar con cero títulos sin evaluación.
* **confiable_num:** Indicador binario con valor 1 si la calificación cuenta con al menos 10 votos (`vote_count` ≥ 10), y 0 si tiene menos de 10 votos.
* **financiero_num:** Indicador binario con valor 1 si el título cuenta simultáneamente con presupuesto e ingresos mayores a cero, y 0 en caso contrario.
* **presupuesto_roi:** Presupuesto de producción en USD asignado al título, restringido a registros con datos financieros válidos.
* **ingresos_roi:** Recaudación global en taquilla en USD asignada al título, restringida a registros con datos financieros válidos.
* **roi:** Múltiplo bruto de recaudación sobre presupuesto (`ingresos_roi / presupuesto_roi`). No es rentabilidad neta: faltan otros costos y el reparto de recaudación. Se conserva el nombre técnico por compatibilidad.
* **es_drama:** Indicador binario con valor 1 si el título incluye Drama entre cualquiera de sus géneros registrados (principales o secundarios), y 0 en caso contrario.
* **es_eeuu:** Indicador binario con valor 1 si el título incluye a Estados Unidos entre cualquiera de sus países de producción (principales o secundarios), y 0 en caso contrario.

---

## 2. Métricas e indicadores de Looker Studio

* **Títulos totales:** Conteo de obras únicas presentes en la selección activa (`COUNT_DISTINCT(content_id)`). Base: una fila por título.
* **% del catálogo:** Proporción de títulos seleccionados respecto al total fijo unificado de 31.991 obras (`COUNT_DISTINCT(content_id) / 31991`). Denominador fijo.
* **Calificación promedio:** Media aritmética de las calificaciones válidas (`AVG(vote_average_clean)`). Excluye títulos sin votos.
* **% con votos suficientes:** Proporción de títulos que alcanzan el umbral operativo de 10 votos (`SUM(confiable_num) / COUNT_DISTINCT(content_id)`). Este umbral no garantiza representatividad ni precisión estadística.
* **% alto engagement:** Proporción de títulos pertenecientes al percentil 75 o superior de su formato (`SUM(alto_engagement) / COUNT_DISTINCT(content_id)`). Ronda el 25 % global por construcción (25,01 % en esta base); empates y redondeo pueden modificar ligeramente la proporción.
* **% de títulos estrella:** Proporción de títulos que cumplen popularidad relativa ≥75, nota ≥7 y ≥10 votos (`SUM(es_estrella) / COUNT_DISTINCT(content_id)`). Su valor global es 8,47 %; no está fijado al 25 %.
* **% con Drama (todos sus géneros):** Proporción de títulos que registran Drama en cualquiera de sus posiciones de género (`SUM(es_drama) / COUNT_DISTINCT(content_id)`). Coincide con G4 (43,2 % en películas, 49,1 % en series).
* **% con EE. UU. (todos los países):** Proporción de títulos con producción en Estados Unidos en cualquier orden de registro (`SUM(es_eeuu) / COUNT_DISTINCT(content_id)`). Coincide con G6 (48,5 % en películas, 20,0 % en series).
* **Cobertura financiera:** Porcentaje de películas que cuentan con registros válidos de presupuesto y recaudación (`SUM(financiero_num) / SUM(es_pelicula)`). Representa el 22,1 % de las películas; no hay registros financieros de series. Si se seleccionan solo series, este indicador referido a películas queda sin denominador y debe mostrarse como no aplicable, no como 0 %.
* **Múltiplo agregado (`roi_agregado`):** Cociente entre recaudación total y presupuesto total del conjunto con ambos datos (`SUM(ingresos_roi) / SUM(presupuesto_roi)`). Requiere un mínimo de 5 títulos con datos al evaluar directores.
* **Múltiplo mediano (`roi_mediano`):** Mediana del cociente individual recaudación/presupuesto (`roi`) para títulos con información financiera. Representa 1,70× a escala global.

---

## 3. Criterios de asignación y limitaciones metodológicas

* **Atribución principal (género, país y director):** Para garantizar que cada título compute una sola vez en tablas y filtros cruzados, el dashboard emplea exclusivamente el primer valor listado en la fuente original. Las ausencias se agrupan bajo "No especificado" (1.088 títulos sin género, 2.261 sin país y 11.092 sin director), categoría excluida de los rankings de categorías.
* **Diferencia entre EDA y Dashboard:** En el análisis exploratorio (G4, G6) los títulos se cuentan en cada categoría secundaria que posean, mientras que en el dashboard computan una única vez. Por ello, las proporciones por atributo principal difieren de la cobertura transversal (Drama en películas: 22,9 % principal vs. 43,2 % transversal; EE. UU. en películas: 35,6 % principal vs. 48,5 % transversal; EE. UU. en series: 15,5 % principal vs. 20,0 % transversal). Las variables `es_drama` y `es_eeuu` restituyen la medición transversal sin duplicar registros.
* **Exclusión de telefilms:** Las producciones catalogadas como "TV Movie" (628 títulos) contienen una etiqueta de formato, no de género temático. Se retira esa etiqueta de la dimensión; los 628 títulos permanecen. Si no queda otro género, se asigna "No especificado".
* **Directores unificados:** Se homologan las variantes del dúo de realizadores a "Anthony Russo / Joe Russo" y se depuran espacios y formatos de mayúsculas.
* **Umbral de votos:** se usa ≥10 como criterio operativo. G1 y G5 incluyen todas las notas con votos; G3 calcula notas solo con ≥10 votos, pero popularidad mediana con todos los títulos del género; G7 restringe ambas variables a títulos con ≥10 votos. G3 exige además ≥100 títulos y ≥30 notas válidas por género.

## 4. Lectura de porcentajes y controles

- Las fórmulas de proporciones se muestran como cocientes entre 0 y 1 para formatear como porcentaje en Looker. Los CSV de KPIs y el EDA multiplican por 100: no volver a multiplicarlos al mostrarlos.
- `% del catálogo` usa el total fijo 31.991; los porcentajes dentro de una selección usan el número de títulos de esa selección. G4 y G6 usan como denominador todos los títulos del tipo.
- No sumar los totales de géneros, países o directores múltiples como si fueran títulos únicos: una obra puede pertenecer a varias categorías.
- `No especificado` representa ausencia de categoría y no cuenta como género real: hay 11 géneros reales compartidos entre tipos, 5 exclusivos de películas y 4 de series en esta base.
- Los controles exportados son `control_g4_vs_looker.csv`, `control_g6_vs_looker.csv`, `control_g8_vs_looker.csv` y `cifras_clave_eda.csv`. Comparan criterios de atribución; no prueban por sí solos el funcionamiento del dashboard en vivo.
- En los scripts actuales, la bandera financiera comprueba valores no nulos después de sustituir ceros. En estos datos coincide con presupuesto y recaudación positivos; para nuevas fuentes debe validarse explícitamente la ausencia de importes negativos.
- Los datos son una extracción histórica, no una actualización automática. La baja cobertura de votos de 2025 se refiere a esa extracción y no prueba por sí sola su causa.
