"""Page « Vendeurs et catégories » : concentration des ventes, vendeurs et catégories."""

import pandas as pd
import streamlit as st

from olist_dashboard import charts, metrics, ui
from olist_dashboard import formatting as fmt
from olist_dashboard.ui import point_delta, relative_delta

# Nombre de commandes minimum pour juger la note et les retards d'un vendeur.
WATCH_MIN_ORDERS = 30


def short_id(seller_id: str) -> str:
    return f"{seller_id[:8]}…"


def seller_table(df: pd.DataFrame) -> None:
    columns = ["seller_id", "seller_state", "revenue", "orders", "average_price", "review_score", "late_rate"]
    st.dataframe(
        df.assign(seller_id=df["seller_id"].map(short_id), late_rate=df["late_rate"] * 100)[columns],
        column_config={
            "seller_id": st.column_config.TextColumn("Vendeur", help="Début de l'identifiant Olist"),
            "seller_state": "État",
            "revenue": st.column_config.NumberColumn("CA (R$)", format="%.0f"),
            "orders": st.column_config.NumberColumn("Commandes"),
            "average_price": st.column_config.NumberColumn("Prix moyen (R$)", format="%.2f"),
            "review_score": st.column_config.NumberColumn("Note moyenne", format="%.2f"),
            "late_rate": st.column_config.NumberColumn("En retard (%)", format="%.1f"),
        },
        hide_index=True,
        width="stretch",
    )


st.title("Vendeurs et catégories")
st.caption("Qui vend quoi sur la place de marché. Montants en réais (R$), hors commandes annulées.")

tables = ui.load_data()
orders, items = tables["orders"], tables["items"]
selection = ui.filter_bar(orders)
current = selection.orders
current_items = items[items["order_id"].isin(current["order_id"])]
kpis = metrics.compute_seller_kpis(current, current_items)
prev = None
if selection.previous_orders is not None:
    prev_items = items[items["order_id"].isin(selection.previous_orders["order_id"])]
    prev = metrics.compute_seller_kpis(selection.previous_orders, prev_items)
note = selection.delta_note
if kpis.active_sellers == 0:
    st.warning("Aucune vente pour ces filtres.")
    st.stop()

# --- KPI ---------------------------------------------------------------------
row1 = st.columns(3)
row1[0].metric(
    "Vendeurs actifs",
    fmt.number(kpis.active_sellers),
    delta=relative_delta(kpis.active_sellers, prev and prev.active_sellers),
    delta_description=note,
    border=True,
    help="Vendeurs ayant réalisé au moins une vente sur la période.",
)
row1[1].metric(
    "CA médian par vendeur",
    fmt.currency(kpis.median_revenue) if kpis.median_revenue is not None else "–",
    delta=relative_delta(kpis.median_revenue, prev and prev.median_revenue),
    delta_description=note,
    border=True,
    help="La moitié des vendeurs réalise moins que ce chiffre d'affaires sur la période.",
)
row1[2].metric(
    "Part du CA des 10 % premiers vendeurs",
    fmt.percent(kpis.top10_share, 0) if kpis.top10_share is not None else "–",
    delta=point_delta(kpis.top10_share, prev and prev.top10_share),
    delta_color="off",
    delta_description=note,
    border=True,
    help="Plus ce chiffre est élevé, plus les ventes reposent sur peu de vendeurs.",
)

row2 = st.columns(3)
row2[0].metric(
    f"Vendeurs à moins de {metrics.SMALL_SELLER_ORDERS} commandes",
    fmt.percent(kpis.small_seller_share, 0) if kpis.small_seller_share is not None else "–",
    delta=point_delta(kpis.small_seller_share, prev and prev.small_seller_share),
    delta_color="off",
    delta_description=note,
    border=True,
    help="Part des vendeurs actifs qui ont reçu peu de commandes sur la période.",
)
row2[1].metric(
    "Catégories vendues",
    fmt.number(kpis.categories),
    delta=relative_delta(kpis.categories, prev and prev.categories),
    delta_color="off",
    delta_description=note,
    border=True,
)
row2[2].metric(
    "Prix moyen d'un article",
    fmt.currency(kpis.average_item_price, 2) if kpis.average_item_price is not None else "–",
    delta=relative_delta(kpis.average_item_price, prev and prev.average_item_price),
    delta_color="off",
    delta_description=note,
    border=True,
    help="Prix de vente moyen d'un article, hors frais de port.",
)
ui.no_comparison_caption(selection)

palette = ui.palette()
sellers = metrics.seller_stats(current, current_items)

# --- Concentration -----------------------------------------------------------
left, right = st.columns(2, gap="large")
with left:
    st.subheader("Concentration des ventes")
    ui.show_chart(
        charts.concentration_chart(
            metrics.concentration_curve(sellers),
            palette,
            highlight=(0.10, kpis.top10_share) if kpis.top10_share is not None else None,
        )
    )
    st.caption("Vendeurs classés du plus gros CA au plus petit.")
with right:
    st.subheader("CA par État du vendeur")
    by_state = metrics.revenue_by_seller_state(current_items)
    by_state["value_label"] = by_state["revenue"].map(fmt.compact_currency)
    ui.show_chart(
        charts.horizontal_bar_chart(
            by_state, "seller_state", "revenue", palette,
            hovertemplate="<b>%{y}</b><br>CA : R$ %{x:,.0f}<br>Part du CA : %{customdata[0]:.1%}"
            "<br>Vendeurs : %{customdata[1]:,}",
            customdata_cols=("share", "sellers"),
        )
    )
    st.caption(
        f"Ces 10 États font {fmt.percent(by_state['share'].sum(), 0)} du CA. "
        "Les filtres d'État portent sur le client, pas sur le vendeur."
    )

# --- Catégories --------------------------------------------------------------
st.subheader("Catégories : chiffre d'affaires et satisfaction")
categories = metrics.category_stats(current, current_items)
reviewed_total = int(categories["reviews"].sum())
threshold = metrics.min_reviews_for_ranking(reviewed_total)
plotted = categories[categories["reviews"] >= threshold]
if len(plotted) < 2:
    st.info("Pas assez d'avis pour comparer les catégories avec ces filtres.")
else:
    average = metrics.compute_kpis(current).average_review
    ui.show_chart(
        charts.scatter_chart(
            plotted, "revenue", "review_score", "category", palette,
            hovertemplate="<b>%{customdata[0]}</b><br>CA : R$ %{x:,.0f}<br>Note moyenne : %{y:.2f} / 5"
            "<br>Commandes : %{customdata[1]:,}<br>Vendeurs : %{customdata[2]:,}",
            customdata_cols=("orders", "sellers"),
            labeled=8,
            y_reference=(average, f"note moyenne {fmt.number(average, 2)}") if average else None,
            x_axis=dict(tickprefix="R$ ", tickformat="~s", title="Chiffre d'affaires", rangemode="tozero"),
            y_axis=dict(tickformat=".1f", title="Note moyenne"),
        )
    )
    st.caption(
        f"{len(plotted)} catégories ayant au moins {fmt.number(threshold)} commandes notées ; "
        "les 8 plus gros CA sont nommées. En bas à droite : les catégories qui pèsent lourd "
        "mais déçoivent."
    )

with st.expander("Voir toutes les catégories en tableau"):
    st.dataframe(
        categories.assign(share=categories["share"] * 100, late_rate=categories["late_rate"] * 100)[
            ["category", "revenue", "share", "orders", "sellers", "average_price", "review_score", "late_rate"]
        ],
        column_config={
            "category": "Catégorie",
            "revenue": st.column_config.NumberColumn("CA (R$)", format="%.0f"),
            "share": st.column_config.NumberColumn("Part du CA (%)", format="%.1f"),
            "orders": st.column_config.NumberColumn("Commandes"),
            "sellers": st.column_config.NumberColumn("Vendeurs"),
            "average_price": st.column_config.NumberColumn("Prix moyen (R$)", format="%.2f"),
            "review_score": st.column_config.NumberColumn("Note moyenne", format="%.2f"),
            "late_rate": st.column_config.NumberColumn("En retard (%)", format="%.1f"),
        },
        hide_index=True,
        width="stretch",
    )

# --- Vendeurs ----------------------------------------------------------------
st.subheader("Vendeurs")
top_tab, watch_tab = st.tabs(["Plus gros chiffres d'affaires", "À surveiller"])
with top_tab:
    seller_table(sellers.head(10))
with watch_tab:
    watched = sellers[sellers["orders"] >= WATCH_MIN_ORDERS].dropna(subset=["review_score"])
    if watched.empty:
        st.info(f"Aucun vendeur n'a {WATCH_MIN_ORDERS} commandes ou plus avec ces filtres.")
    else:
        seller_table(watched.sort_values("review_score").head(10))
        st.caption(
            f"Les 10 vendeurs les moins bien notés parmi ceux qui ont au moins {WATCH_MIN_ORDERS} "
            f"commandes ({fmt.number(len(watched))} vendeurs). La note et le retard sont ceux "
            "de la commande entière, même si elle contient des articles d'autres vendeurs (≈ 1 %)."
        )
