"""Éléments Streamlit communs à toutes les pages : données, filtres, écarts, graphiques."""

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from olist_dashboard import charts, metrics
from olist_dashboard import formatting as fmt
from olist_dashboard.config import RELIABLE_END, RELIABLE_START
from olist_dashboard.data import load_tables, processed_tables_exist


@st.cache_data(show_spinner=False)
def _get_tables() -> dict[str, pd.DataFrame]:
    return load_tables()


def load_data() -> dict[str, pd.DataFrame]:
    """Tables du dashboard ; arrête la page avec un message clair si les CSV manquent."""
    spinner_text = (
        "Chargement des données…"
        if processed_tables_exist()
        else "Premier lancement : construction des tables à partir des CSV de data/raw/ "
        "(cela peut prendre jusqu'à une minute)…"
    )
    try:
        with st.spinner(spinner_text):
            return _get_tables()
    except FileNotFoundError as error:
        st.error(str(error), icon=":material/folder_off:")
        st.stop()


@dataclass(frozen=True)
class Selection:
    start: pd.Timestamp
    end: pd.Timestamp
    states: list[str]
    orders: pd.DataFrame
    # Même sélection sur la période précédente, si elle reste dans la plage représentative.
    previous_orders: pd.DataFrame | None
    delta_note: str | None


def _keep(key: str) -> None:
    # Les widgets sont effacés quand on change de page : on garde leur valeur à part.
    st.session_state[key] = st.session_state[f"_{key}"]


def filter_bar(orders: pd.DataFrame) -> Selection:
    """Filtres période et États, conservés d'une page à l'autre."""
    st.session_state.setdefault("period", (RELIABLE_START.date(), RELIABLE_END.date()))
    st.session_state.setdefault("states", [])
    st.session_state["_period"] = st.session_state["period"]
    st.session_state["_states"] = st.session_state["states"]

    col_period, col_states = st.columns([1, 2])
    with col_period:
        period = st.date_input(
            "Période d'achat",
            min_value=orders["purchase_date"].min().date(),
            max_value=orders["purchase_date"].max().date(),
            format="DD/MM/YYYY",
            key="_period",
            on_change=_keep,
            args=("period",),
            help="Par défaut, janvier 2017 à août 2018 : les mois en dehors de cette "
            "plage ne comptent que quelques centaines de commandes.",
        )
    with col_states:
        states = st.multiselect(
            "États du client",
            sorted(orders["customer_state"].dropna().unique()),
            placeholder="Tous les États",
            key="_states",
            on_change=_keep,
            args=("states",),
        )

    if not isinstance(period, tuple) or len(period) != 2:
        st.info("Choisissez une date de fin pour la période.")
        st.stop()

    start, end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
    current = metrics.filter_orders(orders, start, end, states)
    if current.empty:
        st.warning("Aucune commande pour ces filtres.")
        st.stop()

    prev_start, prev_end = metrics.previous_period(start, end)
    has_previous = prev_start >= RELIABLE_START
    return Selection(
        start=start,
        end=end,
        states=states,
        orders=current,
        previous_orders=(
            metrics.filter_orders(orders, prev_start, prev_end, states) if has_previous else None
        ),
        delta_note=f"vs {prev_start:%d/%m/%Y} – {prev_end:%d/%m/%Y}" if has_previous else None,
    )


def no_comparison_caption(selection: Selection) -> None:
    if selection.previous_orders is None:
        st.caption(
            "Pas de comparaison : la période précédente sortirait de la plage de données "
            "représentative (dès janvier 2017)."
        )


def relative_delta(current: float | None, previous: float | None) -> str | None:
    if current is None or not previous:
        return None
    return fmt.percent(current / previous - 1, signed=True)


def point_delta(current: float | None, previous: float | None) -> str | None:
    if current is None or previous is None:
        return None
    return f"{fmt.number((current - previous) * 100, 1, signed=True)} pt"


def absolute_delta(
    current: float | None, previous: float | None, unit: str = "", decimals: int = 2
) -> str | None:
    if current is None or previous is None:
        return None
    return f"{fmt.number(current - previous, decimals, signed=True)}{unit}"


def palette() -> charts.Palette:
    return charts.palette_for(st.context.theme.type)


def show_chart(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, theme=None)
