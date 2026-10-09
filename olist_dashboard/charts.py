"""Figures Plotly du dashboard, avec une charte commune clair/sombre."""

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
             "juil.", "août", "sept.", "oct.", "nov.", "déc."]


@dataclass(frozen=True)
class Palette:
    accent: str
    accent_wash: str
    surface: str
    text_primary: str
    text_secondary: str
    muted: str
    grid: str
    baseline: str


LIGHT = Palette(
    accent="#2a78d6",
    accent_wash="rgba(42, 120, 214, 0.10)",
    surface="#fcfcfb",
    text_primary="#0b0b0b",
    text_secondary="#52514e",
    muted="#898781",
    grid="#e1e0d9",
    baseline="#c3c2b7",
)
DARK = Palette(
    accent="#3987e5",
    accent_wash="rgba(57, 135, 229, 0.10)",
    surface="#1a1a19",
    text_primary="#f0efec",
    text_secondary="#c3c2b7",
    muted="#898781",
    grid="#2c2c2a",
    baseline="#383835",
)


def palette_for(theme_type: str | None) -> Palette:
    return DARK if theme_type == "dark" else LIGHT


def month_label(ts: pd.Timestamp) -> str:
    return f"{MONTHS_FR[ts.month - 1]} {ts.year}"


def _base_layout(fig: go.Figure, p: Palette, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=16, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=p.text_secondary),
        separators=", ",
        showlegend=False,
        hoverlabel=dict(
            bgcolor=p.surface, bordercolor=p.grid, font=dict(family=FONT, color=p.text_primary)
        ),
    )
    axis = dict(
        gridcolor=p.grid, gridwidth=1, linecolor=p.baseline, zeroline=False,
        tickfont=dict(color=p.muted), title=None, fixedrange=True, automargin=True,
    )
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig


def monthly_revenue_chart(monthly: pd.DataFrame, p: Palette) -> go.Figure:
    """Évolution mensuelle du CA : une seule série, en aire légère."""
    labels = monthly["month"].map(month_label)
    fig = go.Figure(
        go.Scatter(
            x=monthly["month"],
            y=monthly["revenue"],
            customdata=list(zip(labels, monthly["orders"])),
            mode="lines+markers",
            line=dict(color=p.accent, width=2, shape="linear"),
            marker=dict(size=8, color=p.accent, line=dict(width=2, color=p.surface)),
            fill="tozeroy",
            fillcolor=p.accent_wash,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>CA : R$ %{y:,.0f}"
                "<br>Commandes : %{customdata[1]:,}<extra></extra>"
            ),
        )
    )
    _base_layout(fig, p, height=320)
    fig.update_xaxes(
        showgrid=False, dtick="M3", tickformat="%m/%Y", ticks="",
        showspikes=True, spikemode="across", spikesnap="data",
        spikethickness=1, spikedash="solid", spikecolor=p.baseline,
    )
    fig.update_yaxes(tickprefix="R$ ", tickformat="~s", rangemode="tozero")
    fig.update_layout(hovermode="x", hoverdistance=-1, spikedistance=-1)
    return fig


def ranked_bar_chart(
    df: pd.DataFrame, label_col: str, value_col: str, p: Palette,
    extra_cols: tuple[str, ...] = (), hover_extra: str = "",
) -> go.Figure:
    """Barres horizontales triées, une seule couleur, valeur au bout de chaque barre.

    ``hover_extra`` peut citer ``extra_cols`` via ``%{customdata[1]}``, ``%{customdata[2]}``…
    """
    df = df.iloc[::-1]  # Plotly dessine de bas en haut : le plus grand en haut.
    fig = go.Figure(
        go.Bar(
            x=df[value_col],
            y=df[label_col],
            orientation="h",
            marker=dict(color=p.accent, cornerradius=4),
            width=0.6,
            text=df["value_label"],
            textposition="outside",
            textfont=dict(color=p.text_secondary),
            cliponaxis=False,
            customdata=df[["share", *extra_cols]].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>CA : R$ %{x:,.0f}<br>Part du CA : %{customdata[0]:.1%}"
                + hover_extra + "<extra></extra>"
            ),
        )
    )
    _base_layout(fig, p, height=max(240, 34 * len(df)))
    fig.update_xaxes(showgrid=False, showticklabels=False, linecolor="rgba(0,0,0,0)")
    fig.update_yaxes(showgrid=False, linecolor=p.baseline, tickfont=dict(color=p.text_secondary))
    # Place à droite (axe + marge) pour que les étiquettes de valeur ne soient pas coupées.
    fig.update_xaxes(range=[0, df[value_col].max() * 1.15] if len(df) else None)
    fig.update_layout(bargap=0.3, margin=dict(r=72))
    return fig
