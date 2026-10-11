# Dashboard Olist

Tableau de bord interactif sur le
[jeu de données e-commerce brésilien d'Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) :
environ 100 000 commandes passées entre 2016 et 2018.

Deux interfaces affichent les mêmes chiffres, calculés par le même code Python
(`olist_dashboard/`) :

- **Application web** (React + API FastAPI), à déployer en ligne ;
- **Application Streamlit**, pratique pour explorer en local.

## Pages de l'application web

Thème sombre et doré, menu latéral, sélecteur de période et d'États en haut de page.

| Page | Contenu |
|---|---|
| Tableau de bord | CA, commandes, clients uniques, note moyenne ; évolution des ventes (CA, commandes ou panier moyen) ; ventes par région (carte des États) ; catégories les plus vendues ; statut des commandes ; distribution des délais de livraison |
| Ventes | CA, commandes, panier moyen, part du port, paiement par carte, mensualités ; CA et panier moyen mensuels ; moyens de paiement ; panier selon les mensualités |
| Clients | Clients, clients revenus, CA et commandes par client ; clients par mois ; fidélité ; jours et heures d'achat |
| Produits | Catégories, prix moyen, vendeurs actifs, concentration des ventes ; top 10 des catégories ; courbe de concentration ; CA et note par catégorie ; plus gros vendeurs et vendeurs à surveiller |
| Géographie | Villes clientes, premier État ; carte des États et des villes ; indicateurs par État ; top 15 des villes ; CA par État du vendeur |
| Satisfaction | Note moyenne, satisfaits et insatisfaits, avis commentés ; répartition des notes ; note mensuelle ; note selon la livraison et le nombre d'articles ; catégories les moins et les mieux notées |
| Livraisons | Délai moyen, retards, avance sur la date estimée, préparation vendeur ; distribution des délais ; note selon le retard ; taux de retard mensuel ; délai par étape ; délai par État |

Les filtres (période d'achat, États du client) figurent dans l'adresse et suivent
la navigation d'une page à l'autre. L'application Streamlit propose les mêmes
analyses, réparties en 5 pages.

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
  src/pages/               les 7 pages React
  src/components/          tuiles, cartes, graphiques, carte du Brésil, filtres, tableaux
  src/lib/                 appels à l'API, graphiques ECharts, mise en forme, couleurs
  src/styles.css           thème sombre et doré (couleurs validées pour le daltonisme)
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

## Licences

- Données : Olist, « Brazilian E-Commerce Public Dataset », publié sur Kaggle sous
  licence [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) :
  usage non commercial, avec attribution.
- Carte des États : [@svg-maps/brazil](https://github.com/VictorCazanave/svg-maps),
  licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Icônes : [Lucide](https://lucide.dev) (ISC) ; police : Manrope (SIL OFL 1.1).
