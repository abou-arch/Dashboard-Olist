"""Page « Logistique » : délais, retards, étapes de livraison et effet sur la note."""

import pandas as pd
import streamlit as st

from olist_dashboard import charts, metrics, ui
from olist_dashboard import formatting as fmt
from olist_dashboard.ui import absolute_delta, point_delta, relative_delta


def days(value: float | None, decimals: int = 1) -> str:
    return f"{fmt.number(value, decimals)} j" if value is not None else "–"


st.title("Logistique")
st.caption("Délais et retards de livraison, commandes livrées uniquement.")

orders = ui.load_data()["orders"]
selection = ui.filter_bar(orders)
current = selection.orders
kpis = metrics.compute_logistics_kpis(current)
prev = (
    metrics.compute_logistics_kpis(selection.previous_orders)
    if selection.previous_orders is not None
    else None
)
note = ui.delta_note(selection)
if kpis.delivered == 0:
    st.warning("Aucune commande livrée pour ces filtres.")
    st.stop()

# --- KPI ---------------------------------------------------------------------
monthly = metrics.monthly_delivery(current)

row1 = st.columns(3)
row1[0].metric(
    "Délai de livraison moyen",
    days(kpis.average_delivery_days),
    delta=absolute_delta(kpis.average_delivery_days, prev and prev.average_delivery_days, " j", 1),
    delta_color="inverse",
    delta_description=note,
    chart_data=monthly["delivery_days"].tolist()[-12:],
    chart_type="line",
    border=True,
    help=f"De l'achat à la réception. Médiane : {days(kpis.median_delivery_days)}.",
)
row1[1].metric(
    "Livraisons en retard",
    fmt.percent(kpis.late_rate) if kpis.late_rate is not None else "–",
    delta=point_delta(kpis.late_rate, prev and prev.late_rate),
    delta_color="inverse",
    delta_description=note,
    chart_data=monthly["late_rate"].tolist()[-12:],
    chart_type="line",
    border=True,
    help="Part des commandes livrées après la date estimée annoncée au client.",
)
row1[2].metric(
    "Retard moyen des commandes en retard",
    days(kpis.average_delay_when_late),
    delta=absolute_delta(
        kpis.average_delay_when_late, prev and prev.average_delay_when_late, " j", 1
    ),
    delta_color="inverse",
    delta_description=note,
    border=True,
    help="Nombre moyen de jours après la date estimée, pour les seules commandes en retard.",
)

row2 = st.columns(3)
row2[0].metric(
    "Avance médiane sur la date estimée",
    days(kpis.median_margin_days, 0),
    delta=absolute_delta(kpis.median_margin_days, prev and prev.median_margin_days, " j", 0),
    delta_color="off",
    delta_description=note,
    border=True,
    help="La moitié des commandes arrive au moins ce nombre de jours avant la date "
    "annoncée : les estimations d'Olist sont très prudentes.",
)
row2[1].metric(
    "Préparation par le vendeur",
    days(kpis.average_handling_days),
    delta=absolute_delta(kpis.average_handling_days, prev and prev.average_handling_days, " j", 1),
    delta_color="inverse",
    delta_description=note,
    border=True,
    help="Délai moyen entre la validation du paiement et la remise au transporteur.",
)
row2[2].metric(
    "Part du port dans le CA",
    fmt.percent(kpis.freight_share) if kpis.freight_share is not None else "–",
    delta=point_delta(kpis.freight_share, prev and prev.freight_share),
    delta_color="inverse",
    delta_description=note,
    border=True,
    help="Frais de port / (prix des articles + frais de port), hors commandes annulées.",
)
ui.no_comparison_caption(selection)

palette = ui.palette()

# --- Retard et satisfaction --------------------------------------------------
st.subheader("La note client chute dès le premier jour de retard")
by_delay = metrics.review_by_delay(current)
by_delay["value_label"] = by_delay["review_score"].map(
    lambda v: "" if pd.isna(v) else fmt.number(v, 2)
)
ui.show_chart(
    charts.horizontal_bar_chart(
        by_delay, "bucket", "review_score", palette,
        hovertemplate="<b>%{y}</b><br>Note moyenne : %{x:.2f} / 5"
        "<br>Notes de 1 ou 2 : %{customdata[0]:.0%}<br>Commandes notées : %{customdata[1]:,}",
        customdata_cols=("low_scores", "orders"),
    )
)
caption = "Note moyenne sur 5, selon l'écart entre la livraison et la date estimée."
very_late = metrics.low_score_rate(current, 4, float("inf"))
early = metrics.low_score_rate(current, -float("inf"), -1)
if very_late is not None and early is not None:
    caption += (
        f" {fmt.percent(very_late, 0)} des commandes livrées avec 4 jours de retard ou plus "
        f"reçoivent une note de 1 ou 2, contre {fmt.percent(early, 0)} des commandes livrées en avance."
    )
st.caption(caption)

# --- Évolution ---------------------------------------------------------------
left, right = st.columns(2, gap="large")
with left:
    st.subheader("Taux de retard mensuel")
    ui.show_chart(
        charts.monthly_trend_chart(
            monthly, "late_rate", palette,
            hovertemplate="<b>%{customdata[0]}</b><br>En retard : %{y:.1%}"
            "<br>Commandes livrées : %{customdata[1]:,}",
            customdata_cols=("delivered",),
            yaxis=dict(tickformat=".0%"),
        )
    )
    st.caption("Par mois d'achat.")
with right:
    st.subheader("Délai moyen par étape")
    stages = metrics.monthly_delivery_stages(current)
    ui.show_chart(charts.monthly_stacked_chart(stages, metrics.STAGES, palette, unit="j"))
    st.caption(
        "Par mois d'achat. Les commandes aux dates incohérentes (environ 1,5 %) sont écartées."
    )

# --- États -------------------------------------------------------------------
st.subheader("Délai de livraison par État")
by_state = metrics.logistics_by_state(current)
by_state["value_label"] = by_state["delivery_days"].map(days)
left, right = st.columns(2, gap="large")
with left:
    ui.show_chart(
        charts.horizontal_bar_chart(
            by_state, "customer_state", "delivery_days", palette,
            hovertemplate="<b>%{y}</b><br>Délai moyen : %{x:.1f} j"
            "<br>En retard : %{customdata[0]:.1%}<br>Commandes livrées : %{customdata[1]:,}",
            customdata_cols=("late_rate", "delivered"),
        )
    )
with right:
    st.dataframe(
        by_state.drop(columns="value_label").assign(late_rate=by_state["late_rate"] * 100),
        column_config={
            "customer_state": "État",
            "delivery_days": st.column_config.NumberColumn("Délai moyen (j)", format="%.1f"),
            "late_rate": st.column_config.NumberColumn("En retard (%)", format="%.1f"),
            "freight_value": st.column_config.NumberColumn("Port moyen (R$)", format="%.2f"),
            "review_score": st.column_config.NumberColumn("Note moyenne", format="%.2f"),
            "delivered": st.column_config.NumberColumn("Livrées"),
        },
        hide_index=True,
        width="stretch",
        # Hauteur de toutes les lignes + en-tête : pas de défilement interne.
        height=35 * (len(by_state) + 1) + 3,
    )

# --- Données -----------------------------------------------------------------
with st.expander("Voir les données mensuelles en tableau"):
    table = monthly.merge(stages, on="month", how="left")
    st.dataframe(
        table.assign(month=table["month"].dt.strftime("%m/%Y"), late_rate=table["late_rate"] * 100),
        column_config={
            "month": "Mois",
            "late_rate": st.column_config.NumberColumn("En retard (%)", format="%.1f"),
            "delivery_days": st.column_config.NumberColumn("Délai moyen (j)", format="%.1f"),
            "delivered": st.column_config.NumberColumn("Livrées"),
            **{
                stage: st.column_config.NumberColumn(f"{label} (j)", format="%.1f")
                for stage, label in metrics.STAGES.items()
            },
        },
        hide_index=True,
        width="stretch",
    )
