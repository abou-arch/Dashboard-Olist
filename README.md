# Dashboard Olist

Tableau de bord interactif (Streamlit + Plotly) sur le
[jeu de données e-commerce brésilien d'Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) :
environ 100 000 commandes passées entre 2016 et 2018.

## Pages

| Page | Contenu |
|---|---|
| Vue d'ensemble | CA, commandes, panier moyen, note moyenne, taux de retard, délai de livraison, comparés à la période précédente ; CA mensuel ; top 10 des catégories et des États |
| Logistique | Délai de livraison, taux et durée des retards, avance sur la date estimée, préparation vendeur, part du port ; note client selon le retard ; taux de retard mensuel ; délai par étape ; délai et retard par État |

Filtres : période d'achat et États du client, conservés d'une page à l'autre.

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
Si ces fichiers sont absents, ou si leurs colonnes ne correspondent plus au code
(après une mise à jour), l'application les reconstruit au lancement.

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
views/logistics.py         page « Logistique »
olist_dashboard/
  config.py                chemins et règles métier
  data.py                  CSV bruts -> tables orders / items (Parquet)
  metrics.py               filtres et indicateurs
  charts.py                figures Plotly (clair / sombre)
  ui.py                    éléments communs aux pages (données, filtres, écarts)
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
- **Écart à la date estimée** : jour de livraison moins jour estimé ; positif en
  cas de retard, négatif en cas d'avance.
- **Étapes de livraison** : validation (achat → paiement validé), préparation
  vendeur (validation → remise au transporteur), transport (remise → réception).
  Les commandes aux dates manquantes ou dans le désordre (environ 1,5 % des
  livraisons) sont écartées de ce calcul.
- **Part du port** : frais de port / chiffre d'affaires, hors commandes annulées.
- **Période représentative** : de janvier 2017 à août 2018. Avant et après, le jeu de
  données ne contient que quelques centaines de commandes ; c'est la période par
  défaut, et aucune comparaison n'est affichée si la période précédente en sort.
- Les catégories de produits utilisent les libellés anglais fournis par Olist.
