# Airbnb Analytics Platform — Documentation Technique Data Engineering

Ce document rassemble l'intégralité des livrables techniques, configurations, infrastructures et scripts de modélisation SQL développés par Kossi Eric Donyoh (Membre A) pour la plateforme analytique d'Airbnb.

---

## 1. Architecture Technique de la Solution

La plateforme implémente une approche moderne de type ELT (Extract, Load, Transform) localisé, s'appuyant sur l'écosystème suivant :

* DuckDB : Utilisé comme entrepôt de données (Data Warehouse) local à haute performance analytique (OLAP), évitant la lourdeur d'une infrastructure cloud pour ce volume de données.
* dbt (Data Build Tool) : Utilisé pour l'orchestration, le versioning des transformations SQL et l'application des concepts de modélisation en couches logiques.

Structure de l'architecture :

* [ Fichiers Bruts .csv ] (situés dans le dossier data/)
* En suite (Couche Bronze : Vues d'ingestion dans models/bronze/) ---► Pointage direct sans réplication
* En suite (Couche Silver : Transtypage & Nettoyage dans models/silver/) ---► Tables physiques propres et indexées
* En suite (Couche Gold : Data Marts - Partie A dans models/gold/dim_listings_hosts.sql) ---► Modèle dimensionnel consolidé

---

## 2. Périmètre de Responsabilité (Membre A)

Conformément à la planification équitable du binôme, mon périmètre englobe l'ensemble des fondations de la plateforme, de l'ingestion brute jusqu'au premier niveau de modélisation métier :

1. Infrastructure & Setup : Initialisation du projet dbt, isolation de l'environnement virtuel et configuration de la connexion DuckDB.
2. Couche Bronze : Déclaration du manifeste de sourcing externe DuckDB et création des passes-plats SQL.
3. Couche Silver : Écriture des algorithmes de nettoyage (conversion monétaire via Regex, reformatage des indicateurs booléens).
4. Couche Gold (Partie Dimensionnelle) : Jointure et dénormalisation des entités Logements et Hôtes pour fournir une structure prête à l'analyse.

---

## 3. Initialisation de l'Environnement Virtuel (.venv)

Pour isoler les dépendances et garantir la parfaite reproductibilité du pipeline d'ingénierie, exécutez la séquence suivante dans le terminal :

# 1. Création de l'environnement virtuel Python

python3 -m venv .venv

# 2. Activation de l'environnement

# Sur Mac / Linux :

source .venv/bin/activate

# Sur Windows (PowerShell) :

.venv\Scripts\Activate.ps1

# Sur Windows (cmd) :

.venv\Scripts\activate

# 3. Mise à niveau de pip et installation des packages requis pour la partie Data Engineering

pip install --upgrade pip
pip install dbt-core==1.8.2 dbt-duckdb==1.8.1 duckdb==1.0.0

---

## 4. Fichiers de Configuration & Codes Sources (Partie DE)

### Fichier .gitignore

.venv/
**pycache**/
target/
dbt_packages/
*.duckdb
.DS_Store

### Fichier profiles.yml

airbnb_project:
outputs:
dev:
type: duckdb
path: airbnb_analytics.duckdb
threads: 4
target: dev

### Fichier dbt_project.yml

name: 'airbnb_project'
version: '1.0.0'
config-version: 2

profile: 'airbnb_project'

model-paths: ["models"]
seed-paths: ["seeds"]
test-paths: ["tests"]
target-path: "target"
clean-targets:

* "target"
* "dbt_packages"

models:
airbnb_project:
bronze:
materialized: view      # Les sources restent des vues pour optimiser l'espace
silver:
materialized: table     # Performance accrue pour les nettoyages intermédiaires
gold:
materialized: table     # Tables finales indexées prêtes pour la BI

---

### 4.1 Couche Bronze (Ingestion Externe)

#### Fichier models/bronze/_bronze__sources.yml

version: 2

sources:

* name: raw_airbnb
schema: main
meta:
# Utilisation du chemin relatif explicite pour la portabilité du projet


external_location: "./data/{name}.csv"
tables:
* name: listings
* name: hosts



#### Fichier models/bronze/src_listings.sql

select * from {{ source('raw_airbnb', 'listings') }}

#### Fichier models/bronze/src_hosts.sql

select * from {{ source('raw_airbnb', 'hosts') }}

---

### 4.2 Couche Silver (Staging & Transtypage)

#### Fichier models/silver/stg_listings.sql

with source as (
select * from {{ ref('src_listings') }}
)

select
cast(id as bigint) as listing_id,
listing_url,
name as listing_name,
room_type,
cast(minimum_nights as integer) as min_nights,
cast(host_id as bigint) as host_id,

```
-- Extraction et nettoyage de la chaîne prix (ex: $1,250.00 -> 1250.00)
cast(regexp_replace(price, '[$,]', '', 'g') as decimal(10,2)) as price_usd,

cast(created_at as timestamp) as created_at_ts,
cast(updated_at as timestamp) as updated_at_ts

```

from source

#### Fichier models/silver/stg_hosts.sql

with source as (
select * from {{ ref('src_hosts') }}
)

select
cast(id as bigint) as host_id,
name as host_name,

```
-- Transtypage du flag de type texte 't'/'f' en véritable type booléen
case 
    when is_superhost = 't' then true 
    when is_superhost = 'f' then false 
    else null 
end as is_superhost,

cast(created_at as timestamp) as created_at_ts,
cast(updated_at as timestamp) as updated_at_ts

```

from source

---

### 4.3 Couche Gold (Modélisation Dimensionnelle)

#### Fichier models/gold/dim_listings_hosts.sql

with listings as (
select * from {{ ref('stg_listings') }}
),
hosts as (
select * from {{ ref('stg_hosts') }}
)

-- Création de la dimension consolidée dénormalisée pour le dashboard de restitution
select
l.listing_id,
l.listing_name,
l.room_type,
l.min_nights,
l.price_usd,
h.host_id,
h.host_name,
h.is_superhost
from listings l
left join hosts h on l.host_id = h.host_id

---

## 5. Séquence d'Orchestration & Validation

Pour tester, compiler et déployer l'intégralité de ma section d'infrastructure de données, exécutez la commande suivante dans le terminal (avec l'environnement .venv actif) :

# Nettoyage et compilation du pipeline

dbt clean && dbt compile

# Matérialisation des vues Bronze, des tables Silver et de la dimension Gold dans DuckDB

dbt run