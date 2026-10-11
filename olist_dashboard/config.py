"""Chemins et règles métier partagés par tout le projet."""

from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

RAW_FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

# Commandes qui n'ont généré aucune vente : exclues du chiffre d'affaires.
EXCLUDED_STATUSES = frozenset({"canceled", "unavailable"})

# Avant janvier 2017 et après août 2018, le jeu de données ne contient que
# quelques centaines de commandes : ces mois ne sont pas représentatifs.
RELIABLE_START = pd.Timestamp("2017-01-01")
RELIABLE_END = pd.Timestamp("2018-08-31")

# Catégories présentes dans les produits mais absentes du fichier de traduction.
MISSING_CATEGORY_TRANSLATIONS = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_preparers",
}
UNKNOWN_CATEGORY = "Non renseignée"
