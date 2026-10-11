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
import pyarrow.parquet as pq

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
        "sellers": read("sellers", dtype={"seller_zip_code_prefix": "string"}),
        "reviews": read("reviews", parse_dates=["review_creation_date", "review_answer_timestamp"]),
        "translation": read("translation"),
        "payments": read("payments"),
        "geolocation": read(
            "geolocation",
            usecols=["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"],
            dtype={"geolocation_zip_code_prefix": "string"},
        ),
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


# Colonnes des tables produites (et attendues dans les fichiers Parquet).
ORDER_COLUMNS = [
    "order_id",
    "customer_unique_id",
    "customer_city",
    "customer_state",
    "customer_lat",
    "customer_lng",
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
    "payment_type",
    "payment_installments",
    "review_score",
    "has_comment",
    "delivery_days",
    "delay_days",
    "is_late",
]
ITEM_COLUMNS = [
    "order_id",
    "order_item_id",
    "product_id",
    "seller_id",
    "seller_state",
    "category",
    "price",
    "freight_value",
    "purchase_date",
    "order_status",
    "customer_state",
]
TABLE_COLUMNS = {"orders": ORDER_COLUMNS, "items": ITEM_COLUMNS}


def build_payments(payments: pd.DataFrame) -> pd.DataFrame:
    """Moyen de paiement principal et nombre de mensualités de chaque commande.

    Une commande payée en plusieurs fois (≈ 3 %, souvent carte + bon d'achat)
    prend le moyen de paiement du plus gros montant.
    """
    main = payments.sort_values("payment_value", ascending=False).drop_duplicates("order_id")
    out = main.set_index("order_id")[["payment_type"]]
    out["payment_installments"] = payments.groupby("order_id")["payment_installments"].max()
    return out


# Rectangle englobant le Brésil : quelques coordonnées du fichier sont aberrantes.
BRAZIL_LAT = (-34.0, 6.0)
BRAZIL_LNG = (-74.0, -34.0)


def build_zip_coordinates(geolocation: pd.DataFrame) -> pd.DataFrame:
    """Latitude et longitude moyennes de chaque préfixe de code postal (5 chiffres)."""
    geo = geolocation[
        geolocation["geolocation_lat"].between(*BRAZIL_LAT)
        & geolocation["geolocation_lng"].between(*BRAZIL_LNG)
    ]
    prefix = geo["geolocation_zip_code_prefix"].str.zfill(5)
    out = geo.groupby(prefix)[["geolocation_lat", "geolocation_lng"]].mean()
    out.columns = ["customer_lat", "customer_lng"]
    return out


def build_orders(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    customers: pd.DataFrame,
    reviews: pd.DataFrame,
    payments: pd.DataFrame,
    geolocation: pd.DataFrame,
) -> pd.DataFrame:
    """Table au grain commande."""
    amounts = items.groupby("order_id").agg(
        items_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
        n_items=("order_item_id", "count"),
    )
    # Une commande peut avoir plusieurs avis : on garde la note moyenne, et on
    # considère qu'elle est commentée si l'un des avis contient un message.
    reviews = reviews.assign(
        has_comment=reviews["review_comment_message"].fillna("").str.strip().ne("")
    )
    scores = reviews.groupby("order_id").agg(
        review_score=("review_score", "mean"), has_comment=("has_comment", "any")
    )
    # Les codes postaux à 4 chiffres ont perdu leur zéro initial dans le CSV.
    clients = customers.assign(
        zip_prefix=customers["customer_zip_code_prefix"].astype("string").str.zfill(5)
    ).join(build_zip_coordinates(geolocation), on="zip_prefix")
    clients = clients.set_index("customer_id")[
        ["customer_unique_id", "customer_city", "customer_state", "customer_lat", "customer_lng"]
    ]

    df = (
        orders.join(clients, on="customer_id")
        .join(amounts, on="order_id")
        .join(scores, on="order_id")
        .join(build_payments(payments), on="order_id")
    )
    df[["items_value", "freight_value"]] = df[["items_value", "freight_value"]].fillna(0.0)
    df["n_items"] = df["n_items"].fillna(0).astype("int64")
    df["has_comment"] = df["has_comment"].astype("boolean")
    df["revenue"] = df["items_value"] + df["freight_value"]

    delivered = df["order_delivered_customer_date"]
    df["delivery_days"] = (delivered - df["order_purchase_timestamp"]).dt.total_seconds() / 86_400
    # La date estimée est une date sans heure : on compare au jour près.
    # delay_days > 0 : livrée en retard ; < 0 : livrée en avance.
    delay = delivered.dt.normalize() - df["order_estimated_delivery_date"].dt.normalize()
    df["delay_days"] = delay.dt.days.astype("float64")
    df["is_late"] = (df["delay_days"] > 0).astype("boolean").where(delivered.notna())

    df = df.rename(columns={"order_purchase_timestamp": "purchase_date"})
    return df[ORDER_COLUMNS].sort_values("purchase_date", ignore_index=True)


def build_items(
    items: pd.DataFrame, orders: pd.DataFrame, categories: pd.Series, sellers: pd.DataFrame
) -> pd.DataFrame:
    """Table au grain article, avec le contexte de la commande et du vendeur."""
    context = orders.set_index("order_id")[["purchase_date", "order_status", "customer_state"]]
    seller_states = sellers.set_index("seller_id")["seller_state"]
    df = (
        items.join(context, on="order_id")
        .join(categories, on="product_id")
        .join(seller_states, on="seller_id")
    )
    df["category"] = df["category"].fillna(UNKNOWN_CATEGORY)
    return df[ITEM_COLUMNS].sort_values(
        ["purchase_date", "order_id", "order_item_id"], ignore_index=True
    )


def build_tables(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    orders = build_orders(
        raw["orders"], raw["items"], raw["customers"], raw["reviews"],
        raw["payments"], raw["geolocation"],
    )
    categories = build_categories(raw["products"], raw["translation"])
    items = build_items(raw["items"], orders, categories, raw["sellers"])
    return {"orders": orders, "items": items}


def write_processed(tables: dict[str, pd.DataFrame], out_dir: Path = PROCESSED_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(out_dir / f"{name}.parquet", index=False, compression="zstd")


def processed_tables_exist(processed_dir: Path = PROCESSED_DIR) -> bool:
    """Vrai si les tables Parquet existent et ont les colonnes attendues par cette version."""
    for name, columns in TABLE_COLUMNS.items():
        path = processed_dir / f"{name}.parquet"
        if not path.exists() or pq.read_schema(path).names != columns:
            return False
    return True


def load_tables(
    processed_dir: Path = PROCESSED_DIR, raw_dir: Path = RAW_DIR
) -> dict[str, pd.DataFrame]:
    """Charge les tables Parquet, en les (re)construisant depuis les CSV si besoin."""
    if not processed_tables_exist(processed_dir):
        write_processed(build_tables(load_raw(raw_dir)), processed_dir)
    return {name: pd.read_parquet(processed_dir / f"{name}.parquet") for name in TABLE_COLUMNS}
