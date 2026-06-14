# Airbnb Analytics Platform

Mini plateforme analytique transformant des données Airbnb brutes en indicateurs
métier, exposés via un dashboard interactif. Le pipeline suit une architecture
en couches **Bronze → Silver → Gold** orchestrée par **dbt** sur **DuckDB**, et
la restitution est faite avec **Streamlit**.

L'un des axes d'analyse imposés est l'étude de l'impact des **nuits de pleine lune**
sur les avis clients.

---

## Stack technique

| Outil | Rôle |
|-------|------|
| **DuckDB** | Moteur analytique local (stockage + requêtes) |
| **dbt** | Transformations SQL et tests de qualité (Bronze / Silver / Gold) |
| **GitHub** | Versioning et collaboration |
| **Streamlit + Plotly** | Dashboard interactif |

---

## Architecture

```
        CSV bruts (S3)
              │
              ▼
   ┌──────────────────────┐
   │ BRONZE  (vues)       │  src_hosts · src_listings · src_reviews
   │  copie 1:1 du brut   │
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ SILVER  (vues)       │  stg_hosts · stg_listings · stg_reviews
   │  nettoyage + typage  │  + tests qualité (unique / not_null / valeurs)
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ GOLD    (tables)     │  gold_reviews_enriched (faits)
   │  indicateurs métier  │  gold_listing_metrics · gold_host_metrics
   │                      │  gold_review_trends · gold_full_moon_effect
   └──────────┬───────────┘
              ▼
        Streamlit (DuckDB)
              ▼
        Business Users
```

La table **`gold_reviews_enriched`** (1 ligne = 1 avis, enrichi du logement, de
l'hôte et du flag pleine lune) est le point d'entrée du dashboard : tous les
filtres et agrégations sont calculés en SQL directement dessus.

---

## Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/DONYOH/Airbnb_Analytics_Platform.git
cd Airbnb_Analytics_Platform

# 2. Environnement Python + dépendances
python -m venv .venv
# Windows : .venv\Scripts\activate   |   macOS/Linux : source .venv/bin/activate
pip install -r requirements.txt

# 3. Récupérer les données dans le dossier data/
mkdir -p data
cd data
curl -L -O https://logbrain-datasets.s3.eu-west-1.amazonaws.com/airbnb/hosts.csv
curl -L -O https://logbrain-datasets.s3.eu-west-1.amazonaws.com/airbnb/listings.csv
curl -L -O https://logbrain-datasets.s3.eu-west-1.amazonaws.com/airbnb/reviews.csv
cd ..
```

Le fichier `seed_full_moon_dates.csv` est versionné dans `seeds/` (c'est un seed dbt).

`profiles.yml` (connexion DuckDB) est fourni à la racine du projet :

```yaml
airbnb_project:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: airbnb_analytics.duckdb
      threads: 4
```

---

## Exécution

```bash
# Générer la base DuckDB (Bronze → Silver → Gold)
dbt seed     # charge les dates de pleine lune
dbt run      # construit tous les modèles
dbt test     # contrôle qualité des données

# Documentation + lineage
dbt docs generate
dbt docs serve

# Lancer le dashboard
streamlit run app.py
```

---

## Fonctionnalités du dashboard

**Filtres dynamiques** (barre latérale) : type de logement, hôte, fourchette de
prix, statut superhost, période, pleine lune / hors pleine lune.

**4 axes de visualisation :**

1. **Logements** — prix moyen par type, top 10 des logements par volume d'avis.
2. **Hôtes** — top 10 des hôtes les plus actifs, distinction superhost / standard.
3. **Avis** — volume d'avis dans le temps, répartition des sentiments.
4. **Pleine lune** — comparaison du % d'avis positifs pleine lune vs hors pleine lune.

**Indicateurs clés (KPI)** recalculés à chaque filtre : nombre d'avis, de logements,
d'hôtes, % d'avis positifs, prix moyen.

---

## Notes d'analyse (choix liés aux données)

- Les données **ne contiennent pas de quartier** : le filtre est remplacé par
  type de logement / hôte / prix.
- Les avis n'ont **pas de note numérique** mais un **sentiment** (positive /
  neutral / negative) : les indicateurs de qualité sont exprimés en **% d'avis
  positifs**, et non en note moyenne.
- Les avis bruts n'ayant pas d'identifiant, une **clé technique `review_id`** est
  générée en couche Silver.
- **Résultat pleine lune :** environ 56,4 % d'avis positifs les nuits de pleine
  lune contre 56,7 % le reste du temps — l'écart est négligeable, la pleine lune
  n'a pas d'effet notable sur la satisfaction.

---

## Qualité des données (tests dbt)

22 tests automatisés : unicité des clés (`listing_id`, `host_id`, `review_id`),
contraintes `not_null`, intégrité référentielle entre les avis et les logements,
et valeurs autorisées pour les types de logement et les sentiments.

---

## Répartition des tâches

| Membre | Périmètre |
|--------|-----------|
| **Eric** | Setup (repo, dbt, DuckDB), couches Bronze & Silver `hosts` / `listings`, tests, documentation des modèles |
| **mky** | Bronze & Silver `reviews`, intégration pleine lune (seed), table de faits enrichie + couche Gold (indicateurs logements / hôtes / avis / pleine lune), tests associés |
| **Sofiane** | Application Streamlit (4 visualisations + filtres dynamiques), génération de la documentation dbt + lineage, README, QA finale |
