# Dashboard Olist

Tableau de bord interactif (Streamlit + Plotly) sur le
[jeu de données e-commerce brésilien d'Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) :
environ 100 000 commandes passées entre 2016 et 2018.

## Pages

| Page | Contenu |
|---|---|
| Vue d'ensemble | CA, commandes, panier moyen, note moyenne, taux de retard, délai de livraison, comparés à la période précédente ; CA mensuel ; top 10 des catégories et des États |

Filtres : période d'achat et États du client.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Données

Les CSV ne sont pas versionnés. Téléchargez l'archive depuis
[Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) et placez les
fichiers `.csv` dans `data/raw/`, puis construisez les tables du dashboard :

```bash
python scripts/build_dataset.py
```

Le script écrit `data/processed/orders.parquet` et `data/processed/items.parquet`.
Si ces fichiers sont absents, l'application les construit au premier lancement.
Relancez le script après toute modification de `olist_dashboard/data.py`.

## Lancement

```bash
streamlit run app.py
```

## Tests

```bash
pytest
```

## Structure

```
app.py                     point d'entrée Streamlit (navigation)
views/overview.py          page « Vue d'ensemble »
olist_dashboard/
  config.py                chemins et règles métier
  data.py                  CSV bruts -> tables orders / items (Parquet)
  metrics.py               filtres et indicateurs
  charts.py                figures Plotly (clair / sombre)
  formatting.py            nombres à la française
scripts/build_dataset.py   construction des tables Parquet
tests/                     tests unitaires (pytest)
```

## Définitions

- **Chiffre d'affaires** : prix des articles + frais de port. Les commandes annulées
  (`canceled`) ou indisponibles (`unavailable`) sont exclues.
- **Panier moyen** : chiffre d'affaires / nombre de commandes.
- **Note moyenne** : moyenne des avis (1 à 5). Une commande notée plusieurs fois
  compte pour la moyenne de ses notes.
- **Livraison en retard** : commande livrée après le jour de livraison estimé
  communiqué au client (comparaison au jour près).
- **Délai de livraison** : de l'achat à la réception, commandes livrées uniquement.
- **Période représentative** : de janvier 2017 à août 2018. Avant et après, le jeu de
  données ne contient que quelques centaines de commandes ; c'est la période par
  défaut, et aucune comparaison n'est affichée si la période précédente en sort.
- Les catégories de produits utilisent les libellés anglais fournis par Olist.
