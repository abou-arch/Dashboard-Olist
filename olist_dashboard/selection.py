"""Sélection commune à toutes les interfaces : période, États et période de comparaison."""

from dataclasses import dataclass

import pandas as pd

from olist_dashboard import metrics
from olist_dashboard.config import RELIABLE_START


@dataclass(frozen=True)
class Selection:
    start: pd.Timestamp
    end: pd.Timestamp
    states: list[str]
    orders: pd.DataFrame
    # Même sélection sur la période précédente, si elle reste dans la plage représentative.
    previous_orders: pd.DataFrame | None
    previous_start: pd.Timestamp | None
    previous_end: pd.Timestamp | None

    def items(self, items: pd.DataFrame) -> pd.DataFrame:
        """Articles des commandes sélectionnées."""
        return items[items["order_id"].isin(self.orders["order_id"])]

    def previous_items(self, items: pd.DataFrame) -> pd.DataFrame | None:
        if self.previous_orders is None:
            return None
        return items[items["order_id"].isin(self.previous_orders["order_id"])]


def select(
    orders: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, states: list[str] | None = None
) -> Selection:
    """Commandes de la période et des États choisis, et celles de la période précédente.

    La comparaison n'a de sens que si la période précédente est couverte par des
    données représentatives (dès janvier 2017) ; sinon elle est omise.
    """
    start, end = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    states = list(states or [])
    prev_start, prev_end = metrics.previous_period(start, end)
    has_previous = prev_start >= RELIABLE_START
    return Selection(
        start=start,
        end=end,
        states=states,
        orders=metrics.filter_orders(orders, start, end, states),
        previous_orders=(
            metrics.filter_orders(orders, prev_start, prev_end, states) if has_previous else None
        ),
        previous_start=prev_start if has_previous else None,
        previous_end=prev_end if has_previous else None,
    )
