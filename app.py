"""
Airbnb Analytics Platform - Dashboard Streamlit
------------------------------------------------
L'application lit les tables Gold materialisees par dbt dans DuckDB
et propose 4 axes d'analyse (logements, hotes, avis, pleine lune)
avec des filtres dynamiques.

Lancement :  streamlit run app.py
Prerequis  :  dbt seed && dbt run   (genere airbnb_analytics.duckdb)
"""

import os
import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# --- Localisation de la base : a cote de ce fichier, surchargeable par variable d'env ---
chemin_base = os.environ.get(
    "DUCKDB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "airbnb_analytics.duckdb"),
)

st.set_page_config(page_title="Airbnb Analytics", page_icon="🏠", layout="wide")


# --- Connexion DuckDB en lecture seule, mise en cache pour ne pas rouvrir a chaque interaction ---
@st.cache_resource
def get_connexion(path):
    return duckdb.connect(path, read_only=True)


# Si la base n'existe pas, on guide l'utilisateur au lieu de planter
if not os.path.exists(chemin_base):
    st.error(
        "Base DuckDB introuvable. Lance d'abord le pipeline dbt :\n\n"
        "```\ndbt seed\ndbt run\n```"
    )
    st.stop()

con = get_connexion(chemin_base)


# --- Options de filtres : on les lit une fois et on les met en cache ---
@st.cache_data
def charger_options():
    room_types = con.sql(
        "select distinct room_type from gold_reviews_enriched "
        "where room_type is not null order by room_type"
    ).df()["room_type"].tolist()

    hosts = con.sql(
        "select host_name from gold_reviews_enriched "
        "where host_name is not null group by host_name order by count(*) desc"
    ).df()["host_name"].tolist()

    bornes = con.sql(
        "select min(price_usd) p_min, max(price_usd) p_max, "
        "min(review_date) d_min, max(review_date) d_max from gold_reviews_enriched"
    ).df().iloc[0]

    return room_types, hosts, bornes


room_types, hosts, bornes = charger_options()

# =========================================================================
# BARRE LATERALE : FILTRES DYNAMIQUES
# =========================================================================
st.sidebar.title("Filtres")
st.sidebar.caption(
    "Note : le jeu de donnees ne contient pas de quartier, "
    "le filtre demande est remplace par type de logement / hote / prix."
)

f_room = st.sidebar.multiselect("Type de logement", room_types, default=room_types)

f_superhost = st.sidebar.selectbox("Superhost", ["Tous", "Oui", "Non"])

prix_min = float(bornes["p_min"])
prix_max = float(bornes["p_max"])
f_prix = st.sidebar.slider(
    "Prix par nuit ($)", prix_min, prix_max, (prix_min, prix_max)
)

f_dates = st.sidebar.date_input(
    "Periode des avis", value=(bornes["d_min"], bornes["d_max"])
)

f_lune = st.sidebar.radio(
    "Pleine lune", ["Tous les avis", "Pleine lune uniquement", "Hors pleine lune"]
)

f_hosts = st.sidebar.multiselect(
    "Hote (laisser vide = tous)", hosts, default=[]
)

# =========================================================================
# CONSTRUCTION DYNAMIQUE DE LA CLAUSE WHERE (requete parametree = pas d'injection)
# =========================================================================
conditions = ["price_usd between ? and ?"]
params = [f_prix[0], f_prix[1]]

# room_type : liste -> autant de '?' que de valeurs selectionnees
if f_room:
    conditions.append("room_type in (" + ",".join(["?"] * len(f_room)) + ")")
    params.extend(f_room)
else:
    conditions.append("1 = 0")  # aucun type coche -> aucun resultat

if f_superhost == "Oui":
    conditions.append("is_superhost = true")
elif f_superhost == "Non":
    conditions.append("is_superhost = false")

if f_lune == "Pleine lune uniquement":
    conditions.append("is_full_moon = true")
elif f_lune == "Hors pleine lune":
    conditions.append("is_full_moon = false")

if f_hosts:
    conditions.append("host_name in (" + ",".join(["?"] * len(f_hosts)) + ")")
    params.extend(f_hosts)

# date_input renvoie 1 date si l'utilisateur n'a pas fini sa selection
if isinstance(f_dates, (list, tuple)) and len(f_dates) == 2:
    conditions.append("review_date between ? and ?")
    params.extend([f_dates[0], f_dates[1]])

where = " and ".join(conditions)


def requete(select_sql):
    """Execute une requete sur la table de faits filtree et renvoie un DataFrame."""
    sql = f"select {select_sql} from gold_reviews_enriched where {where}"
    return con.execute(sql, params).df()


# =========================================================================
# EN-TETE + INDICATEURS CLES (KPI)
# =========================================================================
st.title("🏠 Airbnb Analytics Platform")
st.caption("Logements · Hotes · Avis · Effet de la pleine lune")

kpi = requete(
    "count(*) avis, count(distinct listing_id) logements, "
    "count(distinct host_id) hotes, round(100.0*avg(is_positive),1) pct_pos, "
    "round(avg(price_usd),0) prix_moy"
).iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Avis", f"{int(kpi['avis']):,}".replace(",", " "))
c2.metric("Logements", f"{int(kpi['logements']):,}".replace(",", " "))
c3.metric("Hotes", f"{int(kpi['hotes']):,}".replace(",", " "))
c4.metric("Avis positifs", f"{kpi['pct_pos']} %" if pd.notna(kpi["pct_pos"]) else "-")
c5.metric("Prix moyen", f"{kpi['prix_moy']:.0f} $" if pd.notna(kpi["prix_moy"]) else "-")

st.divider()

# =========================================================================
# VISU 1 - LOGEMENTS
# =========================================================================
st.subheader("1. Logements")
col_a, col_b = st.columns(2)

with col_a:
    prix = con.execute(
        f"select room_type, round(avg(price_usd),0) prix_moyen "
        f"from gold_reviews_enriched where {where} group by room_type order by prix_moyen desc",
        params,
    ).df()
    fig = px.bar(prix, x="room_type", y="prix_moyen", title="Prix moyen par type de logement",
                 labels={"room_type": "Type", "prix_moyen": "Prix moyen ($)"})
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    top_log = con.execute(
        f"select listing_name, count(*) n_avis "
        f"from gold_reviews_enriched where {where} "
        f"group by listing_name order by n_avis desc limit 10",
        params,
    ).df()
    fig = px.bar(top_log, x="n_avis", y="listing_name", orientation="h",
                 title="Top 10 logements par nombre d'avis",
                 labels={"n_avis": "Nombre d'avis", "listing_name": ""})
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# =========================================================================
# VISU 2 - HOTES
# =========================================================================
st.subheader("2. Hotes")
top_hosts = con.execute(
    f"select host_name, count(*) n_avis, "
    f"max(case when is_superhost then 'Superhost' else 'Standard' end) statut "
    f"from gold_reviews_enriched where {where} and host_name is not null "
    f"group by host_name order by n_avis desc limit 10",
    params,
).df()
fig = px.bar(top_hosts, x="n_avis", y="host_name", orientation="h", color="statut",
             title="Top 10 hotes les plus actifs (par volume d'avis)",
             labels={"n_avis": "Nombre d'avis", "host_name": "", "statut": "Statut"})
fig.update_yaxes(autorange="reversed")
st.plotly_chart(fig, use_container_width=True)

# =========================================================================
# VISU 3 - AVIS
# =========================================================================
st.subheader("3. Avis clients")
col_c, col_d = st.columns(2)

with col_c:
    trend = con.execute(
        f"select date_trunc('month', review_date) mois, count(*) n_avis "
        f"from gold_reviews_enriched where {where} group by 1 order by 1",
        params,
    ).df()
    fig = px.line(trend, x="mois", y="n_avis", title="Volume d'avis dans le temps",
                  labels={"mois": "Mois", "n_avis": "Nombre d'avis"})
    st.plotly_chart(fig, use_container_width=True)

with col_d:
    senti = con.execute(
        f"select coalesce(sentiment,'inconnu') sentiment, count(*) n "
        f"from gold_reviews_enriched where {where} group by 1 order by n desc",
        params,
    ).df()
    fig = px.pie(senti, names="sentiment", values="n", title="Repartition des sentiments", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

# =========================================================================
# VISU 4 - PLEINE LUNE (obligatoire)
# =========================================================================
st.subheader("4. Effet de la pleine lune")
lune = con.execute(
    f"select case when is_full_moon then 'Pleine lune' else 'Hors pleine lune' end periode, "
    f"count(*) n_avis, round(100.0*avg(is_positive),1) pct_positif "
    f"from gold_reviews_enriched where {where} group by is_full_moon order by is_full_moon",
    params,
).df()

col_e, col_f = st.columns(2)
with col_e:
    fig = px.bar(lune, x="periode", y="pct_positif", color="periode",
                 title="% d'avis positifs : pleine lune vs hors",
                 labels={"periode": "", "pct_positif": "% positifs"})
    st.plotly_chart(fig, use_container_width=True)
with col_f:
    st.dataframe(lune.rename(columns={
        "periode": "Periode", "n_avis": "Nombre d'avis", "pct_positif": "% positifs"
    }), use_container_width=True, hide_index=True)
    st.caption(
        "Les volumes ne sont pas comparables directement (il y a beaucoup moins "
        "de nuits de pleine lune). La comparaison pertinente est le % d'avis positifs."
    )
