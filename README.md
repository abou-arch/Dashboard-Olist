# Dashboard Olist

Tableau de bord interactif (Streamlit + Plotly) sur le
[jeu de données e-commerce brésilien d'Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) :
environ 100 000 commandes passées entre 2016 et 2018.

## Pages

| Page | Contenu |
|---|---|
| Vue d'ensemble | CA, commandes, panier moyen, note moyenne, taux de retard, délai de livraison, comparés à la période précédente ; CA mensuel ; top 10 des catégories et des États |
| Logistique | Délai de livraison, taux et durée des retards, avance sur la date estimée, préparation vendeur, part du port ; note client selon le retard ; taux de retard mensuel ; délai par étape ; délai et retard par État |
| Satisfaction | Note moyenne, clients satisfaits et insatisfaits, avis commentés ; répartition des notes ; note mensuelle ; note selon la livraison et le nombre d'articles ; catégories les moins et les mieux notées |
| Vendeurs et catégories | Vendeurs actifs, CA médian, concentration des ventes, petits vendeurs, prix moyen ; courbe de concentration ; CA par État du vendeur ; CA et note par catégorie ; plus gros vendeurs et vendeurs à surveiller |

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
views/satisfaction.py      page « Satisfaction »
views/sellers.py           page « Vendeurs et catégories »
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
  compte pour la moyenne de ses notes ; pour la répartition par étoile, cette
  moyenne est arrondie (4,5 → 5).
- **Clients satisfaits / insatisfaits** : commandes notées 4-5 / 1-2 étoiles.
- **Avis avec commentaire** : l'un des avis de la commande contient un message écrit.
- **Note par catégorie** : une commande compte dans chaque catégorie de produits
  qu'elle contient ; seules les catégories ayant au moins 0,3 % des avis (et au
  moins 20) sont classées.
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
- **CA d'un vendeur ou d'une catégorie** : prix + port de ses articles vendus.
  Sa note et son taux de retard sont ceux des commandes où il apparaît ; une
  commande de plusieurs vendeurs (environ 1 %) compte pour chacun.
- **Vendeurs à surveiller** : les moins bien notés parmi ceux qui ont au moins
  30 commandes sur la période.
- **Période représentative** : de janvier 2017 à août 2018. Avant et après, le jeu de
  données ne contient que quelques centaines de commandes ; c'est la période par
  défaut, et aucune comparaison n'est affichée si la période précédente en sort.
- Les catégories de produits utilisent les libellés anglais fournis par Olist.
