"""Page « Vue d'ensemble » : KPI, évolution du CA, catégories et États."""

import pandas as pd
import streamlit as st

from olist_dashboard import charts, metrics
from olist_dashboard import formatting as fmt
from olist_dashboard.config import RELIABLE_END, RELIABLE_START
from olist_dashboard.data import load_tables


@st.cache_data(show_spinner="Chargement des données…")
def get_tables() -> dict[str, pd.DataFrame]:
    return load_tables()


def relative_delta(current: float | None, previous: float | None) -> str | None:
    if current is None or not previous:
        return None
    return fmt.percent(current / previous - 1, signed=True)


def point_delta(current: float | None, previous: float | None) -> str | None:
    if current is None or previous is None:
        return None
    return f"{fmt.number((current - previous) * 100, 1, signed=True)} pt"


def absolute_delta(current: float | None, previous: float | None, unit: str = "") -> str | None:
    if current is None or previous is None:
        return None
    return f"{fmt.number(current - previous, 2, signed=True)}{unit}"


tables = get_tables()
orders, items = tables["orders"], tables["items"]

st.title("Vue d'ensemble")
st.caption("Olist, place de marché e-commerce brésilienne. Montants en réais (R$).")

# --- Filtres -----------------------------------------------------------------
min_day = orders["purchase_date"].min().date()
max_day = orders["purchase_date"].max().date()
all_states = sorted(orders["customer_state"].dropna().unique())

col_period, col_states = st.columns([1, 2])
with col_period:
    period = st.date_input(
        "Période d'achat",
        value=(RELIABLE_START.date(), RELIABLE_END.date()),
        min_value=min_day,
        max_value=max_day,
        format="DD/MM/YYYY",
        help="Par défaut, janvier 2017 à août 2018 : les mois en dehors de cette "
        "plage ne comptent que quelques centaines de commandes.",
    )
with col_states:
    states = st.multiselect(
        "États du client", all_states, placeholder="Tous les États"
    )

if not isinstance(period, tuple) or len(period) != 2:
    st.info("Choisissez une date de fin pour la période.")
    st.stop()

start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
current = metrics.filter_orders(orders, start, end, states)
if current.empty:
    st.warning("Aucune commande pour ces filtres.")
    st.stop()
current_items = items[items["order_id"].isin(current["order_id"])]

# La comparaison n'a de sens que si la période précédente est couverte par
# des données représentatives.
prev_start, prev_end = metrics.previous_period(start, end)
has_previous = prev_start >= RELIABLE_START
kpis = metrics.compute_kpis(current)
prev = (
    metrics.compute_kpis(metrics.filter_orders(orders, prev_start, prev_end, states))
    if has_previous
    else None
)

# --- KPI ---------------------------------------------------------------------
monthly = metrics.monthly_sales(current)
spark_revenue = monthly["revenue"].tolist()[-12:]
spark_orders = monthly["orders"].tolist()[-12:]
spark_basket = (monthly["revenue"] / monthly["orders"]).tolist()[-12:]
delta_note = (
    f"vs {prev_start:%d/%m/%Y} – {prev_end:%d/%m/%Y}" if has_previous else None
)

row1 = st.columns(3)
row1[0].metric(
    "Chiffre d'affaires",
    fmt.compact_currency(kpis.revenue),
    delta=relative_delta(kpis.revenue, prev and prev.revenue),
    delta_description=delta_note,
    chart_data=spark_revenue,
    chart_type="area",
    border=True,
    help="Prix des articles + frais de port, hors commandes annulées ou indisponibles.",
)
row1[1].metric(
    "Commandes",
    fmt.number(kpis.orders),
    delta=relative_delta(kpis.orders, prev and prev.orders),
    delta_description=delta_note,
    chart_data=spark_orders,
    chart_type="bar",
    border=True,
    help=f"{fmt.number(kpis.customers)} clients distincts.",
)
row1[2].metric(
    "Panier moyen",
    fmt.currency(kpis.average_basket, 2) if kpis.average_basket else "–",
    delta=relative_delta(kpis.average_basket, prev and prev.average_basket),
    delta_description=delta_note,
    chart_data=spark_basket,
    chart_type="line",
    border=True,
    help="Chiffre d'affaires / nombre de commandes.",
)

row2 = st.columns(3)
row2[0].metric(
    "Note moyenne",
    f"{fmt.number(kpis.average_review, 2)} / 5" if kpis.average_review else "–",
    delta=absolute_delta(kpis.average_review, prev and prev.average_review),
    delta_description=delta_note,
    border=True,
    help="Moyenne des avis clients (1 à 5).",
)
row2[1].metric(
    "Livraisons en retard",
    fmt.percent(kpis.late_rate) if kpis.late_rate is not None else "–",
    delta=point_delta(kpis.late_rate, prev and prev.late_rate),
    delta_color="inverse",
    delta_description=delta_note,
    border=True,
    help="Part des commandes livrées après la date estimée annoncée au client.",
)
row2[2].metric(
    "Délai de livraison moyen",
    f"{fmt.number(kpis.average_delivery_days, 1)} j" if kpis.average_delivery_days else "–",
    delta=absolute_delta(kpis.average_delivery_days, prev and prev.average_delivery_days, " j"),
    delta_color="inverse",
    delta_description=delta_note,
    border=True,
    help="De l'achat à la réception par le client, commandes livrées uniquement.",
)
if not has_previous:
    st.caption(
        "Pas de comparaison : la période précédente sortirait de la plage de données représentative (dès janvier 2017)."
    )

# --- Graphiques --------------------------------------------------------------
palette = charts.palette_for(st.context.theme.type)

st.subheader("Chiffre d'affaires mensuel")
st.plotly_chart(
    charts.monthly_revenue_chart(monthly, palette),
    width="stretch",
    config={"displayModeBar": False},
    theme=None,
)

left, right = st.columns(2, gap="large")

with left:
    st.subheader("Top 10 catégories")
    categories = metrics.revenue_by_category(current_items)
    categories["value_label"] = categories["revenue"].map(fmt.compact_currency)
    st.plotly_chart(
        charts.ranked_bar_chart(categories, "category", "revenue", palette),
        width="stretch",
        config={"displayModeBar": False},
        theme=None,
    )
    st.caption(f"Ces 10 catégories font {fmt.percent(categories['share'].sum(), 0)} du CA.")

with right:
    st.subheader("Top 10 États")
    by_state = metrics.revenue_by_state(current)
    by_state["value_label"] = by_state["revenue"].map(fmt.compact_currency)
    st.plotly_chart(
        charts.ranked_bar_chart(
            by_state, "customer_state", "revenue", palette,
            extra_cols=("orders",),
            hover_extra="<br>Commandes : %{customdata[1]:,}",
        ),
        width="stretch",
        config={"displayModeBar": False},
        theme=None,
    )
    st.caption(f"Ces 10 États font {fmt.percent(by_state['share'].sum(), 0)} du CA.")

# --- Données -----------------------------------------------------------------
with st.expander("Voir les données en tableau"):
    st.dataframe(
        monthly.assign(month=monthly["month"].dt.strftime("%m/%Y")),
        column_config={
            "month": "Mois",
            "revenue": st.column_config.NumberColumn("CA (R$)", format="%.2f"),
            "orders": st.column_config.NumberColumn("Commandes"),
        },
        hide_index=True,
        width="stretch",
    )
