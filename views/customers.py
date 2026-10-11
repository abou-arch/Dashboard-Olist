"""Page « Clients » : fidélité, paiements, moments d'achat et géographie des ventes."""

import pandas as pd
import streamlit as st

from olist_dashboard import charts, metrics, ui
from olist_dashboard import formatting as fmt
from olist_dashboard.ui import absolute_delta, point_delta, relative_delta

# Nombre de villes affichées sur la carte (les plus gros CA).
MAP_CITIES = 300

st.title("Clients")
st.caption("Qui achète, comment et quand. Montants en réais (R$), hors commandes annulées.")

orders = ui.load_data()["orders"]
selection = ui.filter_bar(orders)
current = selection.orders
kpis = metrics.compute_customer_kpis(current)
prev = (
    metrics.compute_customer_kpis(selection.previous_orders)
    if selection.previous_orders is not None
    else None
)
note = selection.delta_note
if kpis.customers == 0:
    st.warning("Aucune vente pour ces filtres.")
    st.stop()

# --- KPI ---------------------------------------------------------------------
row1 = st.columns(3)
row1[0].metric(
    "Clients",
    fmt.number(kpis.customers),
    delta=relative_delta(kpis.customers, prev and prev.customers),
    delta_description=note,
    border=True,
    help="Clients distincts ayant passé au moins une commande sur la période.",
)
row1[1].metric(
    "Clients revenus",
    fmt.percent(kpis.repeat_rate) if kpis.repeat_rate is not None else "–",
    delta=point_delta(kpis.repeat_rate, prev and prev.repeat_rate),
    delta_description=note,
    border=True,
    help="Part des clients ayant passé au moins deux commandes sur la période.",
)
row1[2].metric(
    "CA par client",
    fmt.currency(kpis.revenue_per_customer, 2) if kpis.revenue_per_customer is not None else "–",
    delta=relative_delta(kpis.revenue_per_customer, prev and prev.revenue_per_customer),
    delta_description=note,
    border=True,
    help="Chiffre d'affaires de la période / nombre de clients.",
)

row2 = st.columns(3)
row2[0].metric(
    "Paiement par carte de crédit",
    fmt.percent(kpis.credit_card_share) if kpis.credit_card_share is not None else "–",
    delta=point_delta(kpis.credit_card_share, prev and prev.credit_card_share),
    delta_color="off",
    delta_description=note,
    border=True,
    help="Part des commandes payées principalement par carte de crédit.",
)
row2[1].metric(
    "Mensualités moyennes (carte)",
    fmt.number(kpis.average_installments, 1) if kpis.average_installments is not None else "–",
    delta=absolute_delta(kpis.average_installments, prev and prev.average_installments, "", 1),
    delta_color="off",
    delta_description=note,
    border=True,
    help="Nombre moyen de mensualités des commandes payées par carte de crédit.",
)
row2[2].metric(
    "Commandes par client",
    fmt.number(kpis.orders_per_customer, 2) if kpis.orders_per_customer is not None else "–",
    delta=absolute_delta(kpis.orders_per_customer, prev and prev.orders_per_customer),
    delta_description=note,
    border=True,
)
ui.no_comparison_caption(selection)

palette = ui.palette()

# --- Fidélité et paiement ----------------------------------------------------
left, right = st.columns(2, gap="large")
with left:
    st.subheader("Clients selon leur nombre de commandes")
    loyalty = metrics.customers_by_order_count(current)
    loyalty["value_label"] = loyalty["share"].map(lambda v: fmt.percent(v, 1))
    ui.show_chart(
        charts.horizontal_bar_chart(
            loyalty, "group", "share", palette,
            hovertemplate="<b>%{y}</b><br>%{x:.1%} des clients<br>Clients : %{customdata[0]:,}",
            customdata_cols=("customers",),
        )
    )
    st.caption(
        "Sur la période choisie. Presque tous les clients n'achètent qu'une fois : "
        "la croissance repose sur l'acquisition."
    )
with right:
    st.subheader("Moyens de paiement")
    payments = metrics.payment_mix(current)
    payments["value_label"] = payments["share"].map(lambda v: fmt.percent(v, 1))
    ui.show_chart(
        charts.horizontal_bar_chart(
            payments, "label", "share", palette,
            hovertemplate="<b>%{y}</b><br>%{x:.1%} des commandes<br>Commandes : %{customdata[0]:,}"
            "<br>Panier moyen : R$ %{customdata[1]:,.2f}",
            customdata_cols=("orders", "basket"),
        )
    )
    st.caption(
        "Moyen de paiement principal (le plus gros montant) de chaque commande. "
        "Le boleto est un bordereau bancaire payé en espèces ou en ligne."
    )

left, right = st.columns(2, gap="large")
with left:
    st.subheader("Panier moyen selon les mensualités")
    installments = metrics.installments_distribution(current)
    installments["value_label"] = installments["basket"].map(
        lambda v: "" if pd.isna(v) else fmt.currency(v)
    )
    ui.show_chart(
        charts.horizontal_bar_chart(
            installments, "group", "basket", palette,
            hovertemplate="<b>Payée en %{y}</b><br>Panier moyen : R$ %{x:,.2f}"
            "<br>Part des paiements par carte : %{customdata[0]:.1%}<br>Commandes : %{customdata[1]:,}",
            customdata_cols=("share", "orders"),
        )
    )
    st.caption("Commandes payées par carte de crédit : plus le panier est gros, plus il est étalé.")
with right:
    st.subheader("Quand les clients achètent")
    ui.show_chart(charts.heatmap_chart(metrics.purchase_heatmap(current), palette, "commandes"))
    st.caption("Nombre de commandes par jour de la semaine et heure d'achat (heure de Brasília).")

# --- Géographie --------------------------------------------------------------
st.subheader("Où sont les clients")
cities = metrics.revenue_by_city(current)
left, right = st.columns([3, 2], gap="large")
with left:
    ui.show_chart(
        charts.city_map_chart(
            cities, "revenue", palette, highlighted=MAP_CITIES,
            hovertemplate="<b>%{customdata[0]}</b><br>CA : R$ %{customdata[1]:,.0f}"
            "<br>Clients : %{customdata[2]:,}",
            customdata_cols=("city", "revenue", "customers"),
        )
    )
    st.caption(
        f"En bleu, les {min(MAP_CITIES, len(cities))} villes au plus gros CA (surface proportionnelle "
        f"au CA) ; en gris, les {fmt.number(len(cities))} villes où vivent des clients."
    )
with right:
    top = cities.head(15)
    st.dataframe(
        top[["city", "revenue", "customers"]],
        column_config={
            "city": "Ville",
            "revenue": st.column_config.NumberColumn("CA (R$)", format="%.0f"),
            "customers": st.column_config.NumberColumn("Clients"),
        },
        hide_index=True,
        width="stretch",
        height=35 * (len(top) + 1) + 3,
    )
    st.caption(
        f"Les 15 premières villes font {fmt.percent(top['share'].sum(), 0)} du CA."
    )
