# Dashboard Olist

Tableau de bord interactif sur le
[jeu de données e-commerce brésilien d'Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) :
environ 100 000 commandes passées entre 2016 et 2018.

Deux interfaces affichent les mêmes chiffres, calculés par le même code Python
(`olist_dashboard/`) :

- **Application web** (React + API FastAPI), à déployer en ligne ;
- **Application Streamlit**, pratique pour explorer en local.

## Pages

| Page | Contenu |
|---|---|
| Vue d'ensemble | CA, commandes, panier moyen, note moyenne, taux de retard, délai de livraison, comparés à la période précédente ; CA mensuel ; top 10 des catégories et des États |
| Logistique | Délai de livraison, taux et durée des retards, avance sur la date estimée, préparation vendeur, part du port ; note client selon le retard ; taux de retard mensuel ; délai par étape ; délai et retard par État |
| Satisfaction | Note moyenne, clients satisfaits et insatisfaits, avis commentés ; répartition des notes ; note mensuelle ; note selon la livraison et le nombre d'articles ; catégories les moins et les mieux notées |
| Vendeurs et catégories | Vendeurs actifs, CA médian, concentration des ventes, petits vendeurs, prix moyen ; courbe de concentration ; CA par État du vendeur ; CA et note par catégorie ; plus gros vendeurs et vendeurs à surveiller |
| Clients | Clients, clients revenus, CA par client, paiement par carte, mensualités ; clients selon le nombre de commandes ; moyens de paiement ; panier selon les mensualités ; jours et heures d'achat ; carte et top 15 des villes |

Filtres : période d'achat et États du client, conservés d'une page à l'autre.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cd web && npm install && cd ..     # application web uniquement (Node.js 20 ou +)
```

### Données

Les tables préparées (`data/processed/*.parquet`, 13 Mo) sont versionnées :
les applications fonctionnent dès le clone. Les CSV bruts (120 Mo) ne le sont pas ;
pour reconstruire les tables, téléchargez l'archive depuis
[Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), placez les
fichiers `.csv` dans `data/raw/`, puis :

```bash
python scripts/build_dataset.py
```

Si les colonnes des tables ne correspondent plus au code (après une mise à jour),
les applications les reconstruisent au lancement à partir de `data/raw/`.

## Application web

### En développement

Deux terminaux :

```bash
uvicorn api.main:app --reload       # API sur http://localhost:8000
cd web && npm run dev                # site sur http://localhost:5173
```

Le site relaie les appels `/api` vers l'API. Documentation interactive de l'API :
http://localhost:8000/api/docs.

### En production

```bash
cd web && npm run build && cd ..     # compile le site dans web/dist/
uvicorn api.main:app --port 8000     # API + site sur http://localhost:8000
```

Les filtres figurent dans l'adresse (`/logistique?du=2018-01-01&au=2018-06-30&etats=SP,RJ`) :
une vue se partage par un simple lien.

### Mise en ligne

Le `Dockerfile` construit une image unique (site compilé + API) :

```bash
docker build -t dashboard-olist .
docker run -p 8000:8000 dashboard-olist
```

Sur [Render](https://render.com) (offre gratuite) : *New* > *Blueprint*, choisissez
ce dépôt ; `render.yaml` décrit le service. L'application se redéploie à chaque
push sur la branche principale. L'offre gratuite met le service en veille après
15 minutes sans visite : la première page suivante met environ une minute à
s'afficher. L'API utilise environ 350 Mo de mémoire (limite gratuite : 512 Mo).

Toute plateforme qui exécute une image Docker convient (Railway, Fly.io, Google
Cloud Run…) : l'application écoute sur le port indiqué par la variable `PORT`.

## Application Streamlit

```bash
streamlit run app.py
```

## Tests

```bash
pytest                               # calculs, données et API
cd web && npm test                   # mise en forme et écarts (front)
```

## Structure

```
api/
  main.py                  application FastAPI : routes /api et service du site
  pages.py                 données de chaque page (JSON)
web/
  src/pages/               pages React
  src/components/          tuiles, graphiques, filtres, tableaux
  src/lib/                 appels à l'API, graphiques ECharts, mise en forme, thème
olist_dashboard/
  config.py                chemins et règles métier
  data.py                  CSV bruts -> tables orders / items (Parquet)
  selection.py             période, États et période de comparaison
  metrics.py               filtres et indicateurs
  charts.py                figures Plotly (Streamlit)
  ui.py                    éléments communs aux pages Streamlit
  formatting.py            nombres à la française
app.py                     point d'entrée Streamlit (navigation)
views/overview.py          page « Vue d'ensemble »
views/logistics.py         page « Logistique »
views/satisfaction.py      page « Satisfaction »
views/sellers.py           page « Vendeurs et catégories »
views/customers.py         page « Clients »
scripts/build_dataset.py   construction des tables Parquet
tests/                     tests unitaires (pytest)
Dockerfile, render.yaml    image de production et déploiement sur Render
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
- **Client** : identifiant unique (`customer_unique_id`) ; un client revenu
  a passé au moins deux commandes sur la période choisie.
- **Moyen de paiement** : celui du plus gros montant de la commande (environ 3 %
  des commandes combinent plusieurs moyens, souvent carte + bon d'achat).
- **Carte** : position moyenne des codes postaux des clients (fichier de
  géolocalisation Olist), sans fond de carte, donc sans connexion internet requise.
- **Période représentative** : de janvier 2017 à août 2018. Avant et après, le jeu de
  données ne contient que quelques centaines de commandes ; c'est la période par
  défaut, et aucune comparaison n'est affichée si la période précédente en sort.
- Les catégories de produits utilisent les libellés anglais fournis par Olist.

## Licence des données

Olist, « Brazilian E-Commerce Public Dataset », publié sur Kaggle sous licence
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) :
usage non commercial, avec attribution.
