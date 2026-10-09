"""Chargement des CSV bruts et construction des tables analytiques.

Deux tables alimentent le dashboard :

- ``orders`` : une ligne par commande (client, statut, dates, montants, note,
  délai de livraison, retard) ;
- ``items`` : une ligne par article commandé (produit, vendeur, catégorie,
  prix, frais de port), enrichie de la date et du statut de sa commande.

Les fonctions ``build_*`` sont pures (DataFrames en entrée et en sortie) pour
être testables sans les fichiers réels.
"""

from pathlib import Path

import pandas as pd

from olist_dashboard.config import (
    MISSING_CATEGORY_TRANSLATIONS,
    PROCESSED_DIR,
    RAW_DIR,
    RAW_FILES,
    UNKNOWN_CATEGORY,
)

ORDER_DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def load_raw(raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Lit les CSV Olist utiles au dashboard."""
    missing = [name for name in RAW_FILES.values() if not (raw_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Fichiers introuvables dans {raw_dir} : {', '.join(missing)}. "
            "Voir le README pour télécharger le jeu de données."
        )

    def read(key: str, **kwargs) -> pd.DataFrame:
        # utf-8-sig : le fichier de traduction commence par un BOM.
        return pd.read_csv(raw_dir / RAW_FILES[key], encoding="utf-8-sig", **kwargs)

    zip_dtype = {"customer_zip_code_prefix": "string"}
    return {
        "orders": read("orders", parse_dates=ORDER_DATE_COLUMNS),
        "items": read("items", parse_dates=["shipping_limit_date"]),
        "customers": read("customers", dtype=zip_dtype),
        "products": read("products"),
        "reviews": read("reviews", parse_dates=["review_creation_date", "review_answer_timestamp"]),
        "translation": read("translation"),
    }


def format_category(name: str) -> str:
    """``health_beauty`` -> ``Health beauty``."""
    return name.replace("_", " ").strip().capitalize()


def build_categories(products: pd.DataFrame, translation: pd.DataFrame) -> pd.Series:
    """Libellé lisible (anglais) de la catégorie de chaque produit, indexé par product_id."""
    mapping = dict(zip(translation["product_category_name"], translation["product_category_name_english"]))
    mapping.update(MISSING_CATEGORY_TRANSLATIONS)
    english = products["product_category_name"].map(mapping)
    labels = english.map(format_category, na_action="ignore").fillna(UNKNOWN_CATEGORY)
    return pd.Series(labels.to_numpy(), index=products["product_id"], name="category")


def build_orders(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    customers: pd.DataFrame,
    reviews: pd.DataFrame,
) -> pd.DataFrame:
    """Table au grain commande."""
    amounts = items.groupby("order_id").agg(
        items_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
        n_items=("order_item_id", "count"),
    )
    # Une commande peut avoir plusieurs avis : on garde la note moyenne.
    scores = reviews.groupby("order_id")["review_score"].mean().rename("review_score")
    clients = customers.set_index("customer_id")[
        ["customer_unique_id", "customer_city", "customer_state"]
    ]

    df = (
        orders.join(clients, on="customer_id")
        .join(amounts, on="order_id")
        .join(scores, on="order_id")
    )
    df[["items_value", "freight_value"]] = df[["items_value", "freight_value"]].fillna(0.0)
    df["n_items"] = df["n_items"].fillna(0).astype("int64")
    df["revenue"] = df["items_value"] + df["freight_value"]

    delivered = df["order_delivered_customer_date"]
    df["delivery_days"] = (delivered - df["order_purchase_timestamp"]).dt.total_seconds() / 86_400
    # La date estimée est une date sans heure : on compare au jour près.
    late = delivered.dt.normalize() > df["order_estimated_delivery_date"].dt.normalize()
    df["is_late"] = late.astype("boolean").where(delivered.notna())

    df = df.rename(columns={"order_purchase_timestamp": "purchase_date"})
    columns = [
        "order_id",
        "customer_unique_id",
        "customer_city",
        "customer_state",
        "order_status",
        "purchase_date",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
        "n_items",
        "items_value",
        "freight_value",
        "revenue",
        "review_score",
        "delivery_days",
        "is_late",
    ]
    return df[columns].sort_values("purchase_date", ignore_index=True)


def build_items(items: pd.DataFrame, orders: pd.DataFrame, categories: pd.Series) -> pd.DataFrame:
    """Table au grain article, avec le contexte de la commande."""
    context = orders.set_index("order_id")[["purchase_date", "order_status", "customer_state"]]
    df = items.join(context, on="order_id").join(categories, on="product_id")
    df["category"] = df["category"].fillna(UNKNOWN_CATEGORY)
    columns = [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "category",
        "price",
        "freight_value",
        "purchase_date",
        "order_status",
        "customer_state",
    ]
    return df[columns].sort_values(["purchase_date", "order_id", "order_item_id"], ignore_index=True)


def build_tables(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    orders = build_orders(raw["orders"], raw["items"], raw["customers"], raw["reviews"])
    categories = build_categories(raw["products"], raw["translation"])
    items = build_items(raw["items"], orders, categories)
    return {"orders": orders, "items": items}


def write_processed(tables: dict[str, pd.DataFrame], out_dir: Path = PROCESSED_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(out_dir / f"{name}.parquet", index=False)


def load_tables(
    processed_dir: Path = PROCESSED_DIR, raw_dir: Path = RAW_DIR
) -> dict[str, pd.DataFrame]:
    """Charge les tables Parquet, en les (re)construisant depuis les CSV si besoin."""
    paths = {name: processed_dir / f"{name}.parquet" for name in ("orders", "items")}
    if not all(path.exists() for path in paths.values()):
        write_processed(build_tables(load_raw(raw_dir)), processed_dir)
    return {name: pd.read_parquet(path) for name, path in paths.items()}
