"""Page « Satisfaction » : notes des clients, leurs causes et les catégories concernées."""

import pandas as pd
import streamlit as st

from olist_dashboard import charts, metrics, ui
from olist_dashboard import formatting as fmt
from olist_dashboard.ui import absolute_delta, point_delta, relative_delta


def score(value: float | None) -> str:
    return f"{fmt.number(value, 2)} / 5" if value is not None and not pd.isna(value) else "–"


def share(value: float | None) -> str:
    return fmt.percent(value) if value is not None else "–"


def score_bars(df: pd.DataFrame, label_col: str, p: charts.Palette):
    """Barres de note moyenne, avec la part d'insatisfaits au survol."""
    df = df.assign(value_label=df["review_score"].map(lambda v: "" if pd.isna(v) else fmt.number(v, 2)))
    return charts.horizontal_bar_chart(
        df, label_col, "review_score", p,
        hovertemplate="<b>%{y}</b><br>Note moyenne : %{x:.2f} / 5"
        "<br>Insatisfaits (1-2 ★) : %{customdata[0]:.0%}<br>Commandes notées : %{customdata[1]:,}",
        customdata_cols=("dissatisfied_share", "orders"),
    )


st.title("Satisfaction")
st.caption("Avis laissés par les clients après leur commande, notés de 1 à 5 étoiles.")

tables = ui.load_data()
orders, items = tables["orders"], tables["items"]
selection = ui.filter_bar(orders)
current = selection.orders
kpis = metrics.compute_satisfaction_kpis(current)
prev = (
    metrics.compute_satisfaction_kpis(selection.previous_orders)
    if selection.previous_orders is not None
    else None
)
note = selection.delta_note
if kpis.reviewed == 0:
    st.warning("Aucun avis pour ces filtres.")
    st.stop()

# --- KPI ---------------------------------------------------------------------
monthly = metrics.monthly_satisfaction(current)

row1 = st.columns(3)
row1[0].metric(
    "Note moyenne",
    score(kpis.average_review),
    delta=absolute_delta(kpis.average_review, prev and prev.average_review),
    delta_description=note,
    chart_data=monthly["review_score"].tolist()[-12:],
    chart_type="line",
    border=True,
)
row1[1].metric(
    "Clients satisfaits",
    share(kpis.satisfied_share),
    delta=point_delta(kpis.satisfied_share, prev and prev.satisfied_share),
    delta_description=note,
    border=True,
    help="Part des commandes notées 4 ou 5 étoiles.",
)
row1[2].metric(
    "Clients insatisfaits",
    share(kpis.dissatisfied_share),
    delta=point_delta(kpis.dissatisfied_share, prev and prev.dissatisfied_share),
    delta_color="inverse",
    delta_description=note,
    chart_data=monthly["dissatisfied_share"].tolist()[-12:],
    chart_type="line",
    border=True,
    help="Part des commandes notées 1 ou 2 étoiles.",
)

row2 = st.columns(3)
row2[0].metric(
    "Commandes notées",
    fmt.number(kpis.reviewed),
    delta=relative_delta(kpis.reviewed, prev and prev.reviewed),
    delta_color="off",
    delta_description=note,
    border=True,
    help=f"{share(kpis.response_rate)} des commandes de la période ont reçu un avis.",
)
row2[1].metric(
    "Avis avec commentaire",
    share(kpis.comment_rate),
    delta=point_delta(kpis.comment_rate, prev and prev.comment_rate),
    delta_color="off",
    delta_description=note,
    border=True,
    help="Part des commandes notées dont l'avis contient un message écrit.",
)
row2[2].metric(
    "Insatisfaits qui commentent",
    share(kpis.dissatisfied_comment_rate),
    delta=point_delta(kpis.dissatisfied_comment_rate, prev and prev.dissatisfied_comment_rate),
    delta_color="off",
    delta_description=note,
    border=True,
    help="Part des avis à 1 ou 2 étoiles qui contiennent un message écrit : "
    "les clients mécontents s'expriment bien plus que les autres.",
)
ui.no_comparison_caption(selection)

palette = ui.palette()

# --- Répartition et évolution -----------------------------------------------
left, right = st.columns(2, gap="large")
with left:
    st.subheader("Répartition des notes")
    distribution = metrics.score_distribution(current)
    distribution["value_label"] = distribution["share"].map(lambda v: fmt.percent(v, 0))
    ui.show_chart(
        charts.horizontal_bar_chart(
            distribution, "label", "share", palette,
            hovertemplate="<b>%{y}</b><br>%{x:.1%} des commandes notées"
            "<br>Commandes : %{customdata[0]:,}",
            customdata_cols=("orders",),
        )
    )
    st.caption("Une commande notée plusieurs fois compte pour la moyenne de ses avis, arrondie.")
with right:
    st.subheader("Note moyenne mensuelle")
    ui.show_chart(
        charts.monthly_trend_chart(
            monthly, "review_score", palette,
            hovertemplate="<b>%{customdata[0]}</b><br>Note moyenne : %{y:.2f} / 5"
            "<br>Insatisfaits : %{customdata[1]:.1%}<br>Commandes notées : %{customdata[2]:,}",
            customdata_cols=("dissatisfied_share", "reviewed"),
            yaxis=dict(tickformat=".1f"),
            zero_based=False,
        )
    )
    st.caption(
        "Par mois d'achat. L'axe ne part pas de zéro. "
        "À comparer avec le taux de retard mensuel de la page Logistique."
    )

# --- Facteurs ----------------------------------------------------------------
st.subheader("Ce qui fait baisser la note")
left, right = st.columns(2, gap="large")
with left:
    st.markdown("**Selon la livraison**")
    ui.show_chart(score_bars(metrics.review_by_delivery(current), "group", palette))
    st.caption(
        "« Non livrée » : commande annulée, indisponible ou pas encore livrée. "
        "Le détail par jour de retard est sur la page Logistique."
    )
with right:
    st.markdown("**Selon le nombre d'articles**")
    ui.show_chart(score_bars(metrics.review_by_items(current), "group", palette))
    st.caption(
        "Une commande de plusieurs articles peut venir de plusieurs vendeurs et arriver "
        "en plusieurs colis."
    )

# --- Catégories --------------------------------------------------------------
current_items = items[items["order_id"].isin(current["order_id"])]
categories = metrics.review_by_category(current, current_items)
threshold = metrics.min_reviews_for_ranking(kpis.reviewed)
ranked = categories[categories["orders"] >= threshold]

st.subheader("Notes par catégorie")
if len(ranked) < 2:
    st.info("Pas assez d'avis pour classer les catégories avec ces filtres.")
else:
    n = min(10, len(ranked) // 2)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(f"**Les {n} moins bien notées**")
        ui.show_chart(score_bars(ranked.head(n), "category", palette))
    with right:
        st.markdown(f"**Les {n} mieux notées**")
        ui.show_chart(score_bars(ranked.tail(n).iloc[::-1], "category", palette))
    st.caption(
        f"Catégories ayant au moins {fmt.number(threshold)} commandes notées "
        f"({len(ranked)} sur {len(categories)}). "
        "Une commande compte dans chaque catégorie de produits qu'elle contient."
    )

with st.expander("Voir toutes les catégories en tableau"):
    st.dataframe(
        categories.assign(dissatisfied_share=categories["dissatisfied_share"] * 100),
        column_config={
            "category": "Catégorie",
            "review_score": st.column_config.NumberColumn("Note moyenne", format="%.2f"),
            "dissatisfied_share": st.column_config.NumberColumn("Insatisfaits (%)", format="%.1f"),
            "orders": st.column_config.NumberColumn("Commandes notées"),
        },
        hide_index=True,
        width="stretch",
    )

with st.expander("Voir les données mensuelles en tableau"):
    st.dataframe(
        monthly.assign(
            month=monthly["month"].dt.strftime("%m/%Y"),
            dissatisfied_share=monthly["dissatisfied_share"] * 100,
        ),
        column_config={
            "month": "Mois",
            "review_score": st.column_config.NumberColumn("Note moyenne", format="%.2f"),
            "dissatisfied_share": st.column_config.NumberColumn("Insatisfaits (%)", format="%.1f"),
            "reviewed": st.column_config.NumberColumn("Commandes notées"),
        },
        hide_index=True,
        width="stretch",
    )
