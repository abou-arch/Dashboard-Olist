"""Page « Vue d'ensemble » : KPI, évolution du CA, catégories et États."""

import streamlit as st

from olist_dashboard import charts, metrics, ui
from olist_dashboard import formatting as fmt
from olist_dashboard.ui import absolute_delta, point_delta, relative_delta

st.title("Vue d'ensemble")
st.caption("Olist, place de marché e-commerce brésilienne. Montants en réais (R$).")

tables = ui.load_data()
orders, items = tables["orders"], tables["items"]
selection = ui.filter_bar(orders)
current = selection.orders
current_items = items[items["order_id"].isin(current["order_id"])]
kpis = metrics.compute_kpis(current)
prev = (
    metrics.compute_kpis(selection.previous_orders)
    if selection.previous_orders is not None
    else None
)
delta_note = ui.delta_note(selection)

# --- KPI ---------------------------------------------------------------------
monthly = metrics.monthly_sales(current)
spark_revenue = monthly["revenue"].tolist()[-12:]
spark_orders = monthly["orders"].tolist()[-12:]
spark_basket = (monthly["revenue"] / monthly["orders"]).tolist()[-12:]

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
ui.no_comparison_caption(selection)

# --- Graphiques --------------------------------------------------------------
palette = ui.palette()

st.subheader("Chiffre d'affaires mensuel")
ui.show_chart(
    charts.monthly_trend_chart(
        monthly, "revenue", palette,
        hovertemplate="<b>%{customdata[0]}</b><br>CA : R$ %{y:,.0f}"
        "<br>Commandes : %{customdata[1]:,}",
        customdata_cols=("orders",),
        yaxis=dict(tickprefix="R$ ", tickformat="~s"),
    )
)

left, right = st.columns(2, gap="large")

with left:
    st.subheader("Top 10 catégories")
    categories = metrics.revenue_by_category(current_items)
    categories["value_label"] = categories["revenue"].map(fmt.compact_currency)
    ui.show_chart(
        charts.horizontal_bar_chart(
            categories, "category", "revenue", palette,
            hovertemplate="<b>%{y}</b><br>CA : R$ %{x:,.0f}<br>Part du CA : %{customdata[0]:.1%}",
            customdata_cols=("share",),
        )
    )
    st.caption(f"Ces 10 catégories font {fmt.percent(categories['share'].sum(), 0)} du CA.")

with right:
    st.subheader("Top 10 États")
    by_state = metrics.revenue_by_state(current)
    by_state["value_label"] = by_state["revenue"].map(fmt.compact_currency)
    ui.show_chart(
        charts.horizontal_bar_chart(
            by_state, "customer_state", "revenue", palette,
            hovertemplate="<b>%{y}</b><br>CA : R$ %{x:,.0f}<br>Part du CA : %{customdata[0]:.1%}"
            "<br>Commandes : %{customdata[1]:,}",
            customdata_cols=("share", "orders"),
        )
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
            "customers": st.column_config.NumberColumn("Clients"),
        },
        hide_index=True,
        width="stretch",
    )
