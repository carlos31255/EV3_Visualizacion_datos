"""Fase 1 — Integración y limpieza de películas + series (StreamView Analytics, EP3).

Uso desde la raíz del proyecto:
    python src/limpieza.py

Entradas  : data/raw/netflix_movies_detailed_up_to_2025.csv
            data/raw/netflix_tv_shows_detailed_up_to_2025.csv
Salidas   : data/processed/contenido_unificado.csv
            data/processed/contenido_por_genero.csv
            data/processed/contenido_por_pais.csv
            data/processed/contenido_por_director.csv
            data/processed/mapa_generos.csv
            data/processed/control_calidad.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"

NO_ESP = "No especificado"
UMBRAL_VOTOS = 10  # mínimo de votos para considerar "confiable" una calificación
GENERO_FORMATO = "TV Movie"  # es un formato (telefilm), no un género narrativo: se marca y se excluye de la dimensión género

# Homologación de géneros: taxonomía de películas (TMDb movie) y de series (TMDb tv).
# Clave = género original; valor = género unificado (en español, para la audiencia).
MAPA_GENEROS = {
    # --- películas ---
    "Action": "Acción y Aventura", "Adventure": "Acción y Aventura",
    "Science Fiction": "Ciencia ficción y Fantasía", "Fantasy": "Ciencia ficción y Fantasía",
    "War": "Guerra y Política", "Thriller": "Suspenso", "Horror": "Terror",
    "Music": "Música", "History": "Historia",
    "Animation": "Animación", "Comedy": "Comedia", "Crime": "Crimen",
    "Documentary": "Documental", "Drama": "Drama", "Family": "Familia",
    "Mystery": "Misterio", "Romance": "Romance", "Western": "Western",
    # --- series ---
    "Action & Adventure": "Acción y Aventura",
    "Sci-Fi & Fantasy": "Ciencia ficción y Fantasía",
    "War & Politics": "Guerra y Política",
    "Kids": "Familia", "News": "Noticias", "Reality": "Reality",
    "Soap": "Telenovela", "Talk": "Talk show", "Unknown": NO_ESP,
}

IDIOMAS = {
    "en": "Inglés", "zh": "Chino (mandarín)", "cn": "Chino (cantonés)", "ja": "Japonés",
    "ko": "Coreano", "es": "Español", "fr": "Francés", "de": "Alemán", "hi": "Hindi",
    "tl": "Tagalo", "pt": "Portugués", "ru": "Ruso", "it": "Italiano", "tr": "Turco",
    "ar": "Árabe", "nl": "Neerlandés", "th": "Tailandés", "pl": "Polaco", "sv": "Sueco",
    "da": "Danés", "no": "Noruego", "id": "Indonesio", "cs": "Checo", "he": "Hebreo",
    "ta": "Tamil", "el": "Griego", "ur": "Urdu", "fi": "Finés", "te": "Telugu",
    "hu": "Húngaro", "fa": "Persa", "xx": "Sin idioma",
}


def cargar_crudos():
    peliculas = pd.read_csv(RAW / "netflix_movies_detailed_up_to_2025.csv")
    series = pd.read_csv(RAW / "netflix_tv_shows_detailed_up_to_2025.csv")
    return peliculas, series


def resolver_duplicados_series(series: pd.DataFrame):
    """Series: hay show_id repetidos (todos de 2025). Se conserva la fila con más votos
    y, a igualdad, la de mayor popularidad."""
    n_antes = len(series)
    ordenadas = series.sort_values(["show_id", "vote_count", "popularity"],
                                   ascending=[True, False, False])
    limpias = ordenadas.drop_duplicates("show_id", keep="first").sort_index()
    return limpias.reset_index(drop=True), n_antes - len(limpias)


def integrar(peliculas: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    """Une ambas fuentes con llave compuesta (los show_id se solapan entre archivos)."""
    p = peliculas.assign(tipo_contenido="Película")
    s = series.assign(tipo_contenido="Serie", budget=np.nan, revenue=np.nan)
    df = pd.concat([p, s], ignore_index=True)
    prefijo = np.where(df["tipo_contenido"] == "Película", "M-", "S-")
    df.insert(0, "content_id", prefijo + df["show_id"].astype(str))
    return df


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # columnas sin valor analítico: duration (vacía/constante), rating (== vote_average), type
    df = df.drop(columns=["duration", "rating", "type"])
    df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")

    for col in ["director", "cast", "country", "genres", "description"]:
        df[col] = df[col].fillna(NO_ESP)

    df["idioma"] = df["language"].map(IDIOMAS).fillna(df["language"])
    df["es_telefilm"] = df["genres"].str.contains(GENERO_FORMATO, regex=False)   # el texto original de genres no se modifica

    # Calificación: 0 con vote_count == 0 es "sin votos", no una nota real.
    df["tiene_votos"] = df["vote_count"] > 0
    df["vote_average_clean"] = df["vote_average"].where(df["tiene_votos"])
    df["calificacion_confiable"] = df["vote_count"] >= UMBRAL_VOTOS

    # Popularidad: escalas distintas por tipo -> percentil (0-100) dentro de cada tipo.
    df["indice_engagement"] = (df.groupby("tipo_contenido")["popularity"]
                               .rank(pct=True) * 100).round(2)

    # Finanzas (solo películas): 0 = dato no informado.
    df["budget_clean"] = df["budget"].replace(0, np.nan)
    df["revenue_clean"] = df["revenue"].replace(0, np.nan)
    df["tiene_datos_financieros"] = df["budget_clean"].notna() & df["revenue_clean"].notna()
    df["roi"] = df["revenue_clean"] / df["budget_clean"]
    df.loc[~df["tiene_datos_financieros"], "roi"] = np.nan
    return df


# Columnas que viajan a las tablas largas (sin textos pesados como description/cast)
COLS_LARGO = ["content_id", "tipo_contenido", "title", "release_year", "idioma", "popularity",
              "indice_engagement", "vote_count", "vote_average_clean", "tiene_votos",
              "calificacion_confiable", "budget_clean", "revenue_clean",
              "tiene_datos_financieros", "roi"]


def _largo(df, col_origen, col_nuevo):
    base = df[COLS_LARGO + [col_origen]]
    largo = base.assign(**{col_nuevo: base[col_origen].str.split(", ")}).explode(col_nuevo)
    largo = largo.drop(columns=[col_origen])
    largo[col_nuevo] = largo[col_nuevo].str.strip()
    return largo


def tabla_genero(df: pd.DataFrame) -> pd.DataFrame:
    g = _largo(df, "genres", "genero_original")
    # "TV Movie" sale de la dimensión género; si era el único género del título, queda "No especificado"
    es_tv = g["genero_original"] == GENERO_FORMATO
    g_tv, g = g[es_tv], g[~es_tv]
    solo_tv = g_tv[~g_tv["content_id"].isin(g["content_id"])].assign(genero_original=NO_ESP)
    g = pd.concat([g, solo_tv], ignore_index=True)
    g["genero_unificado"] = g["genero_original"].map(MAPA_GENEROS).fillna(g["genero_original"])
    g.loc[g["genero_original"] == NO_ESP, "genero_unificado"] = NO_ESP
    # Action + Adventure -> ambos "Acción y Aventura": evitar contar dos veces el mismo título.
    return g.drop_duplicates(["content_id", "genero_unificado"]).reset_index(drop=True)


def tabla_pais(df: pd.DataFrame) -> pd.DataFrame:
    p = _largo(df, "country", "pais")
    return p.drop_duplicates(["content_id", "pais"]).reset_index(drop=True)


def tabla_director(df: pd.DataFrame) -> pd.DataFrame:
    d = _largo(df, "director", "director_ind")
    d = d[d["director_ind"] != NO_ESP]
    return d.drop_duplicates(["content_id", "director_ind"]).reset_index(drop=True)


def control_calidad(p_raw, s_raw, s_dups, df, gen, pais, direc) -> pd.DataFrame:
    n_p, n_s = len(p_raw), len(s_raw) - s_dups
    filas = [
        ("Películas de entrada", 16000, len(p_raw)),
        ("Series de entrada", 16000, len(s_raw)),
        ("Series duplicadas eliminadas (show_id repetido)", 9, s_dups),
        ("Filas del dataset unificado = películas + series sin duplicados", n_p + n_s, len(df)),
        ("content_id único (duplicados)", 0, int(df["content_id"].duplicated().sum())),
        ("show_id que se solapan entre películas y series (resuelto con content_id)", 397,
         len(set(p_raw["show_id"]) & set(s_raw["show_id"]))),
        ("Nulos en content_id/tipo_contenido/release_year", 0,
         int(df[["content_id", "tipo_contenido", "release_year"]].isna().sum().sum())),
        ("Series con budget/revenue (deben ser 0)", 0,
         int(df.loc[df.tipo_contenido == "Serie", "tiene_datos_financieros"].sum())),
        ("Películas con datos financieros completos", 3540,
         int(df.loc[df.tipo_contenido == "Película", "tiene_datos_financieros"].sum())),
        ("vote_average_clean nulo solo si vote_count = 0 (inconsistencias)", 0,
         int((df["vote_average_clean"].isna() != (df["vote_count"] == 0)).sum())),
        ("Géneros unificados sin mapear (distintos de los esperados)", 0,
         int((~gen["genero_original"].isin(list(MAPA_GENEROS) + [NO_ESP])).sum())),
        ("Títulos duplicados en tabla de género (content_id + género)", 0,
         int(gen.duplicated(["content_id", "genero_unificado"]).sum())),
        ("Títulos de la tabla de género presentes en el unificado", df["content_id"].nunique(),
         gen["content_id"].nunique()),
        ("Títulos de la tabla de país presentes en el unificado", df["content_id"].nunique(),
         pais["content_id"].nunique()),
        ("Índice de engagement fuera de 0-100", 0,
         int((~df["indice_engagement"].between(0, 100)).sum())),
        ("Títulos marcados como telefilm (es_telefilm), excluidos del género", 628, int(df["es_telefilm"].sum())),
        ("Filas de TV Movie en la tabla de género (deben ser 0)", 0,
         int((gen["genero_original"] == GENERO_FORMATO).sum())),
    ]
    out = pd.DataFrame(filas, columns=["control", "esperado", "obtenido"])
    out["ok"] = out["esperado"] == out["obtenido"]
    return out


def ejecutar(guardar=True):
    p_raw, s_raw = cargar_crudos()
    s_ok, n_dups = resolver_duplicados_series(s_raw)
    df = limpiar(integrar(p_raw, s_ok))
    gen, pais, direc = tabla_genero(df), tabla_pais(df), tabla_director(df)
    mapa = (pd.DataFrame(list(MAPA_GENEROS.items()), columns=["genero_original", "genero_unificado"])
            .sort_values(["genero_unificado", "genero_original"]))
    qc = control_calidad(p_raw, s_raw, n_dups, df, gen, pais, direc)
    if guardar:
        PROC.mkdir(parents=True, exist_ok=True)
        df.to_csv(PROC / "contenido_unificado.csv", index=False)
        gen.to_csv(PROC / "contenido_por_genero.csv", index=False)
        pais.to_csv(PROC / "contenido_por_pais.csv", index=False)
        direc.to_csv(PROC / "contenido_por_director.csv", index=False)
        mapa.to_csv(PROC / "mapa_generos.csv", index=False)
        qc.to_csv(PROC / "control_calidad.csv", index=False)
    return df, gen, pais, direc, mapa, qc


if __name__ == "__main__":
    *_, qc = ejecutar()
    print(qc.to_string(index=False))
    if not qc["ok"].all():
        raise SystemExit("Hay controles de calidad que no se cumplen.")
    print("\nOK: todos los controles de calidad se cumplen.")