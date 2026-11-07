"""Fase 3 — Definición, cálculo y verificación de KPIs (StreamView Analytics, EP3).

Uso desde la raíz del proyecto (después de python src/limpieza.py):
    python src/kpis.py

Entradas : data/processed/contenido_unificado.csv, contenido_por_genero.csv, contenido_por_pais.csv
Salidas  : data/processed/looker_contenido.csv   (tabla única que alimenta Looker Studio)
           data/processed/looker_genero.csv      (tabla larga para gráficos de género en Looker)
           data/processed/kpis_resumen.csv       (KPIs globales y por tipo)
           data/processed/kpis_por_anio.csv, kpis_por_genero.csv, kpis_por_pais.csv
           data/processed/kpis_verificacion.csv  (cálculo principal vs segunda vía)

Regla de porcentajes: siempre suma(numerador) / cuenta(registros); nunca promedio de porcentajes.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
NO_ESP = "No especificado"

UMBRAL_ALTO_ENGAGEMENT = 75   # percentil dentro del tipo desde el cual un título es de "alto engagement"
UMBRAL_ESTRELLA_NOTA = 7      # nota mínima (con votos confiables) para ser título "estrella"
PAISES_ES = {
    "United States of America": "Estados Unidos", "Japan": "Japón", "United Kingdom": "Reino Unido",
    "China": "China", "South Korea": "Corea del Sur", "France": "Francia", "Canada": "Canadá",
    "Germany": "Alemania", "India": "India", "Spain": "España", "Belgium": "Bélgica", "Italy": "Italia",
    "Mexico": "México", "Philippines": "Filipinas", "Hong Kong": "Hong Kong", "Australia": "Australia",
    "Brazil": "Brasil", "Russia": "Rusia", "Turkey": "Turquía", "Sweden": "Suecia", "Thailand": "Tailandia",
    "Denmark": "Dinamarca", "Netherlands": "Países Bajos", "Poland": "Polonia", "Ireland": "Irlanda",
    "Taiwan": "Taiwán", "Norway": "Noruega", "Egypt": "Egipto", "Argentina": "Argentina", "Chile": "Chile",
    "Czech Republic": "Chequia", "Switzerland": "Suiza", "Colombia": "Colombia", "Austria": "Austria",
    "South Africa": "Sudáfrica", "Finland": "Finlandia", "Portugal": "Portugal", "Indonesia": "Indonesia",
    "Israel": "Israel", "Greece": "Grecia", "New Zealand": "Nueva Zelanda", "Hungary": "Hungría",
    "Bulgaria": "Bulgaria", "Luxembourg": "Luxemburgo", "United States Minor Outlying Islands": "Islas Menores de EE. UU.", "Puerto Rico": "Puerto Rico", "Taiwan, Province of China": "Taiwán",
    "Pakistan": "Pakistán", "Malaysia": "Malasia", "Romania": "Rumania", "Ukraine": "Ucrania",
    "Serbia": "Serbia", "Iran": "Irán", "United Arab Emirates": "Emiratos Árabes Unidos",
    "Venezuela": "Venezuela", "Singapore": "Singapur", "Slovakia": "Eslovaquia", "Croatia": "Croacia",
    "Iceland": "Islandia", "Estonia": "Estonia", "Syrian Arab Republic": "Siria", "Vietnam": "Vietnam",
    "Lebanon": "Líbano", "Peru": "Perú", "Saudi Arabia": "Arabia Saudita", "Lithuania": "Lituania",
    "Georgia": "Georgia", "Morocco": "Marruecos", "Iraq": "Irak",
}
# ---------------------------------------------------------------- tabla para Looker
def preparar_looker(df, gen, pais):
    """Una fila por título. Agrega columnas pensadas para que Looker calcule con SUM/COUNT/AVG."""
    out = df.copy()
    out["genero_principal"] = out["content_id"].map(gen.groupby("content_id")["genero_unificado"].first())
    out["pais_principal"] = out["content_id"].map(pais.groupby("content_id")["pais"].first())
    out["genero_principal"] = out["genero_principal"].fillna(NO_ESP)
    out["pais_principal"] = out["pais_principal"].fillna(NO_ESP)
    out["pais_principal"] = out["pais_principal"].map(PAISES_ES).fillna(out["pais_principal"])
    out["alto_engagement"] = (out["indice_engagement"] >= UMBRAL_ALTO_ENGAGEMENT).astype(int)
    out["es_estrella"] = ((out["indice_engagement"] >= UMBRAL_ALTO_ENGAGEMENT)
                          & out["calificacion_confiable"].astype(bool)
                          & (out["vote_average_clean"] >= UMBRAL_ESTRELLA_NOTA)).astype(int)
    out["es_pelicula"] = (out["tipo_contenido"] == "Película").astype(int)
    out["confiable_num"] = out["calificacion_confiable"].astype(int)
    fin = out["tiene_datos_financieros"]
    out["presupuesto_roi"] = out["budget_clean"].where(fin)    # solo filas con ambos datos
    out["ingresos_roi"] = out["revenue_clean"].where(fin)
    out["financiero_num"] = fin.astype(int)

    # Extraer primer director, unificar hermanos Russo, limpiar espacios y capitalización
    out["director_principal"] = (out["director"].str.split(r",\s*", regex=True).str[0]
                                 .str.replace(r"\s+", " ", regex=True).str.strip())
    out["director_principal"] = out["director_principal"].replace(
        {"Anthony Russo": "Anthony Russo / Joe Russo", "Joe Russo": "Anthony Russo / Joe Russo"}
    ).fillna(NO_ESP)
    dp = out["director_principal"]
    out["director_principal"] = dp.str.casefold().map(dp.groupby(dp.str.casefold()).agg(lambda s: s.mode().iat[0]))

    # Presencia real (todos los géneros / países del título) para los dos hallazgos centrales: 1 columna 0/1 por título
    out["es_drama"] = out["content_id"].isin(gen.loc[gen["genero_unificado"] == "Drama", "content_id"]).astype(int)
    out["es_eeuu"] = out["content_id"].isin(pais.loc[pais["pais"] == "United States of America", "content_id"]).astype(int)

    cols = ["content_id", "title", "tipo_contenido", "es_pelicula", "release_year", "idioma",
            "genero_principal", "pais_principal", "director_principal", "popularity", "indice_engagement", "alto_engagement", "es_estrella", "vote_count",
            "vote_average_clean", "confiable_num", "financiero_num", "presupuesto_roi", "ingresos_roi", "roi",
            "es_drama", "es_eeuu"]
    return out[cols]

def preparar_looker_genero(gen):
    """Una fila por título y género: fuente de TODOS los gráficos de género en Looker
    (misma base que G3 y G4 del notebook; un título aparece una vez por cada género)."""
    out = gen[gen["genero_unificado"] != NO_ESP].copy()
    out["confiable_num"] = out["calificacion_confiable"].astype(int)
    out["alto_engagement"] = (out["indice_engagement"] >= UMBRAL_ALTO_ENGAGEMENT).astype(int)
    cols = ["content_id", "title", "tipo_contenido", "release_year", "idioma", "genero_unificado",
            "indice_engagement", "alto_engagement", "vote_average_clean", "confiable_num"]
    return out[cols]


def verificar_genero(lg, por_gen, n_tipo):
    """Replica en estilo Looker (COUNT_DISTINCT / total del tipo) el % por género y lo compara con kpis_por_genero."""
    filas = []
    for (tipo, gen_), d in lg.groupby(["tipo_contenido", "genero_unificado"]):
        ref = por_gen[(por_gen.tipo_contenido == tipo) & (por_gen.genero_unificado == gen_)]
        if ref.empty:       # kpis_por_genero solo incluye géneros con >= 100 títulos
            continue
        pct = d["content_id"].nunique() / n_tipo[tipo] * 100
        cal = d["vote_average_clean"].dropna()
        ok = np.isclose(pct, ref["pct_del_tipo"].iloc[0]) and np.isclose(cal.mean(), ref["calificacion_prom"].iloc[0])
        filas.append((tipo, gen_, pct, ref["pct_del_tipo"].iloc[0], bool(ok)))
    return pd.DataFrame(filas, columns=["tipo_contenido", "genero", "pct_looker", "pct_kpis_por_genero", "ok"])


# ---------------------------------------------------------------- vía 1: pandas
def kpis_pandas(d):
    """KPIs de una selección de títulos (una fila por título)."""
    n = len(d)
    peliculas = d[d["tipo_contenido"] == "Película"]
    fin = d[d["financiero_num"] == 1]
    return {
        "titulos": n,
        "calificacion_prom": d["vote_average_clean"].mean(),
        "pct_confiable": d["confiable_num"].sum() / n * 100 if n else np.nan,
        "pct_alto_engagement": d["alto_engagement"].sum() / n * 100 if n else np.nan,
        "pct_estrella": d["es_estrella"].sum() / n * 100 if n else np.nan,
        "pct_drama": d["es_drama"].sum() / n * 100 if n else np.nan,
        "pct_eeuu": d["es_eeuu"].sum() / n * 100 if n else np.nan,
        "roi_agregado": fin["ingresos_roi"].sum() / fin["presupuesto_roi"].sum() if len(fin) else np.nan,
        "roi_mediano": fin["roi"].median() if len(fin) else np.nan,
        "peliculas_con_datos_fin": len(fin),
        "pct_cobertura_fin": len(fin) / len(peliculas) * 100 if len(peliculas) else np.nan,
    }


# ---------------------------------------------------------------- vía 2: numpy / estilo Looker
def kpis_looker(d):
    """Segunda vía, sin groupby ni .mean(): replica lo que hará Looker (SUM / COUNT sobre campos)."""
    n = d["content_id"].nunique()
    cal = d["vote_average_clean"].to_numpy(float)
    ok = ~np.isnan(cal)
    alto = d["alto_engagement"].to_numpy(float)
    est = d["es_estrella"].to_numpy(float)
    drama = d["es_drama"].to_numpy(float)
    eeuu = d["es_eeuu"].to_numpy(float)
    conf = d["confiable_num"].to_numpy(float)
    fin = d["financiero_num"].to_numpy(float) == 1
    pel = d["es_pelicula"].to_numpy(float)
    ing, pre = d["ingresos_roi"].to_numpy(float), d["presupuesto_roi"].to_numpy(float)
    roi = np.sort(d["roi"].to_numpy(float)[fin])
    mediana = np.nan if roi.size == 0 else (roi[roi.size // 2] if roi.size % 2 else roi[roi.size // 2 - 1: roi.size // 2 + 1].mean())
    cal_prom = cal[ok].sum() / ok.sum() if ok.sum() else np.nan
    return {
        "titulos": n,
        "calificacion_prom": cal_prom,
        "pct_confiable": conf.sum() / n * 100 if n else np.nan,
        "pct_alto_engagement": alto.sum() / n * 100 if n else np.nan,
        "pct_estrella": est.sum() / n * 100 if n else np.nan,
        "pct_drama": drama.sum() / n * 100 if n else np.nan,
        "pct_eeuu": eeuu.sum() / n * 100 if n else np.nan,
        "roi_agregado": np.nansum(ing[fin]) / np.nansum(pre[fin]) if fin.any() else np.nan,
        "roi_mediano": mediana,
        "peliculas_con_datos_fin": int(fin.sum()),
        "pct_cobertura_fin": fin.sum() / pel.sum() * 100 if pel.sum() else np.nan,
    }


def verificar(looker, semilla=7):
    """Compara ambas vías en la base completa, por tipo y en 30 selecciones aleatorias (año × género × país)."""
    rng = np.random.default_rng(semilla)
    sels = {"Total": looker,
            "Películas": looker[looker.tipo_contenido == "Película"],
            "Series": looker[looker.tipo_contenido == "Serie"]}
    gens, paises = looker.genero_principal.unique(), looker.pais_principal.unique()
    for i in range(30):
        a0 = int(rng.integers(looker.release_year.min(), looker.release_year.max()))
        sel = looker[(looker.release_year >= a0) & (looker.genero_principal.isin(rng.choice(gens, 3, replace=False)))
                     & (looker.pais_principal.isin(rng.choice(paises, 4, replace=False)))]
        if len(sel):
            sels[f"Selección aleatoria {i + 1}"] = sel
    filas = []
    for nombre, sel in sels.items():
        a, b = kpis_pandas(sel), kpis_looker(sel)
        for k in a:
            va, vb = a[k], b[k]
            igual = (np.isnan(va) and np.isnan(vb)) or np.isclose(va, vb, rtol=1e-9, atol=1e-9)
            filas.append((nombre, k, va, vb, bool(igual)))
    return pd.DataFrame(filas, columns=["seleccion", "kpi", "via_pandas", "via_looker", "ok"])


# ---------------------------------------------------------------- agregados
def tabla_por(looker, col):
    filas = []
    for clave, d in looker.groupby(col):
        filas.append({col: clave, **kpis_pandas(d)})
    return pd.DataFrame(filas)


def tabla_largas(largo, col, minimo=100):
    """KPIs por género/país desde la tabla larga (un título puede aparecer en varios grupos)."""
    filas = []
    for (tipo, clave), d in largo.groupby(["tipo_contenido", col]):
        d = d.assign(confiable_num=d.calificacion_confiable.astype(int),
                     alto_engagement=(d.indice_engagement >= UMBRAL_ALTO_ENGAGEMENT).astype(int))
        n = len(d)
        if n < minimo:
            continue
        filas.append({"tipo_contenido": tipo, col: clave, "titulos": n,
                      "pct_del_tipo": np.nan,  # se completa abajo (base fija = total del tipo)
                      "calificacion_prom": d.vote_average_clean.mean(),
                      "pct_confiable": d.confiable_num.sum() / n * 100,
                      "pct_alto_engagement": d.alto_engagement.sum() / n * 100})
    return pd.DataFrame(filas)


def ejecutar(guardar=True):
    df = pd.read_csv(PROC / "contenido_unificado.csv")
    gen = pd.read_csv(PROC / "contenido_por_genero.csv")
    pais = pd.read_csv(PROC / "contenido_por_pais.csv")
    looker = preparar_looker(df, gen, pais)
    n_tipo = looker.groupby("tipo_contenido").size()

    resumen = pd.DataFrame({"Total": kpis_pandas(looker),
                            "Película": kpis_pandas(looker[looker.tipo_contenido == "Película"]),
                            "Serie": kpis_pandas(looker[looker.tipo_contenido == "Serie"])}).T
    resumen.index.name = "ambito"
    resumen["pct_del_catalogo"] = resumen["titulos"] / len(looker) * 100   # base fija = total unificado

    por_anio = tabla_por(looker.assign(tipo_anio=looker.tipo_contenido + " " + looker.release_year.astype(str)), "tipo_anio")
    por_anio[["tipo_contenido", "release_year"]] = por_anio.pop("tipo_anio").str.rsplit(" ", n=1, expand=True)
    por_gen = tabla_largas(gen, "genero_unificado")
    por_gen["pct_del_tipo"] = por_gen.titulos / por_gen.tipo_contenido.map(n_tipo) * 100
    por_pais = tabla_largas(pais, "pais")
    por_pais["pct_del_tipo"] = por_pais.titulos / por_pais.tipo_contenido.map(n_tipo) * 100

    ver = verificar(looker)
    lg = preparar_looker_genero(gen)
    ver_gen = verificar_genero(lg, por_gen, n_tipo)
    ver = pd.concat([ver, ver_gen.assign(seleccion="Género (tabla larga)", kpi="pct_del_tipo + calificacion_prom")
                     [["seleccion", "kpi", "pct_looker", "pct_kpis_por_genero", "ok"]]
                     .rename(columns={"pct_looker": "via_pandas", "pct_kpis_por_genero": "via_looker"})], ignore_index=True)
    if guardar:
        looker.to_csv(PROC / "looker_contenido.csv", index=False)
        lg.to_csv(PROC / "looker_genero.csv", index=False)
        resumen.to_csv(PROC / "kpis_resumen.csv")
        por_anio.to_csv(PROC / "kpis_por_anio.csv", index=False)
        por_gen.to_csv(PROC / "kpis_por_genero.csv", index=False)
        por_pais.to_csv(PROC / "kpis_por_pais.csv", index=False)
        ver.to_csv(PROC / "kpis_verificacion.csv", index=False)
    return looker, resumen, por_anio, por_gen, por_pais, ver


# Cifras de la Entrada 03 de NOTAS.md (películas / series) para contrastar la base real.
REFERENCIAS = [("Película", "titulos", 16000, 0), ("Serie", "titulos", 15991, 0),
               ("Película", "calificacion_prom", 6.309, 0.001), ("Serie", "calificacion_prom", 7.024, 0.001),
               ("Película", "pct_confiable", 88.6, 0.05), ("Serie", "pct_confiable", 38.4, 0.05),
               ("Película", "peliculas_con_datos_fin", 3540, 0), ("Película", "pct_cobertura_fin", 22.1, 0.05),
               ("Película", "roi_mediano", 1.70, 0.005),
               ("Película", "pct_drama", 43.2, 0.05), ("Serie", "pct_drama", 49.1, 0.05),      # G4 (todos los géneros)
               ("Película", "pct_eeuu", 48.5, 0.05), ("Serie", "pct_eeuu", 20.0, 0.05)]       # G6 (todos los países)


def contrastar(resumen):
    filas = [(a, k, esp, resumen.loc[a, k], abs(resumen.loc[a, k] - esp) <= tol + 1e-12)
             for a, k, esp, tol in REFERENCIAS]
    return pd.DataFrame(filas, columns=["ambito", "kpi", "esperado_notas", "obtenido", "ok"])


if __name__ == "__main__":
    looker, resumen, *_, ver = ejecutar()
    print(resumen.round(3).T.to_string())
    ref = contrastar(resumen)
    print("\nContraste con cifras de NOTAS.md:\n", ref.round(3).to_string(index=False))
    print(f"\nVerificación entre vías: {int(ver.ok.sum())}/{len(ver)} coinciden")
    if not (ver.ok.all() and ref.ok.all()):
        raise SystemExit("Hay KPIs que no coinciden: revisar kpis_verificacion.csv")
    print("OK: KPIs verificados.")