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
    # Couleurs catégorielles, dans un ordre fixe (validé daltonisme, 3 premières).
    categorical: tuple[str, ...]


LIGHT = Palette(
    accent="#2a78d6",
    accent_wash="rgba(42, 120, 214, 0.10)",
    surface="#fcfcfb",
    text_primary="#0b0b0b",
    text_secondary="#52514e",
    muted="#898781",
    grid="#e1e0d9",
    baseline="#c3c2b7",
    categorical=("#2a78d6", "#eb6834", "#1baf7a"),
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
    categorical=("#3987e5", "#d95926", "#199e70"),
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


def _monthly_xaxis(fig: go.Figure, p: Palette) -> None:
    fig.update_xaxes(
        showgrid=False, dtick="M3", tickformat="%m/%Y", ticks="",
        showspikes=True, spikemode="across", spikesnap="data",
        spikethickness=1, spikedash="solid", spikecolor=p.baseline,
    )
    fig.update_layout(hovermode="x", hoverdistance=-1, spikedistance=-1)


def monthly_trend_chart(
    df: pd.DataFrame,
    value_col: str,
    p: Palette,
    hovertemplate: str,
    customdata_cols: tuple[str, ...] = (),
    yaxis: dict | None = None,
) -> go.Figure:
    """Évolution mensuelle d'une seule série, en aire légère.

    ``hovertemplate`` peut citer le mois via ``%{customdata[0]}`` et les
    colonnes ``customdata_cols`` via ``%{customdata[1]}``, ``%{customdata[2]}``…
    """
    customdata = df[list(customdata_cols)].assign(_label=df["month"].map(month_label))
    customdata = customdata[["_label", *customdata_cols]].to_numpy()
    fig = go.Figure(
        go.Scatter(
            x=df["month"],
            y=df[value_col],
            customdata=customdata,
            mode="lines+markers",
            line=dict(color=p.accent, width=2),
            marker=dict(size=8, color=p.accent, line=dict(width=2, color=p.surface)),
            fill="tozeroy",
            fillcolor=p.accent_wash,
            hovertemplate=hovertemplate + "<extra></extra>",
        )
    )
    _base_layout(fig, p, height=320)
    _monthly_xaxis(fig, p)
    fig.update_yaxes(rangemode="tozero", **(yaxis or {}))
    return fig


def monthly_stacked_chart(
    df: pd.DataFrame, series: dict[str, str], p: Palette, unit: str
) -> go.Figure:
    """Colonnes empilées par mois ; ``series`` associe colonne -> libellé (3 au plus)."""
    if len(series) > len(p.categorical):
        raise ValueError(f"{len(series)} séries pour {len(p.categorical)} couleurs.")
    labels = df["month"].map(month_label)
    fig = go.Figure()
    for (col, name), color in zip(series.items(), p.categorical):
        fig.add_bar(
            x=df["month"],
            y=df[col],
            name=name,
            # Le contour couleur du fond crée l'espace de 2 px entre les segments.
            marker=dict(color=color, line=dict(color=p.surface, width=2)),
            customdata=labels,
            hovertemplate=f"{name} : %{{y:.1f}} {unit}<extra></extra>",
        )
    _base_layout(fig, p, height=340)
    _monthly_xaxis(fig, p)
    fig.update_layout(
        barmode="stack",
        bargap=0.35,
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h", x=0, y=1.02, xanchor="left", yanchor="bottom",
            traceorder="normal", font=dict(color=p.text_secondary), title=None,
        ),
        margin=dict(t=40),
    )
    fig.update_xaxes(hoverformat="%m/%Y")
    fig.update_yaxes(ticksuffix=f" {unit}")
    return fig


def horizontal_bar_chart(
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    p: Palette,
    hovertemplate: str,
    customdata_cols: tuple[str, ...] = (),
) -> go.Figure:
    """Barres horizontales d'une seule couleur, valeur au bout de chaque barre.

    Les barres suivent l'ordre de ``df`` (première ligne en haut) : triez
    avant pour un classement, gardez l'ordre naturel pour des tranches.

    ``df`` doit contenir une colonne ``value_label`` ; ``hovertemplate`` cite
    ``customdata_cols`` via ``%{customdata[0]}``, ``%{customdata[1]}``…
    """
    df = df.iloc[::-1]  # Plotly dessine de bas en haut : le premier en haut.
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
            customdata=df[list(customdata_cols)].to_numpy() if customdata_cols else None,
            hovertemplate=hovertemplate + "<extra></extra>",
        )
    )
    _base_layout(fig, p, height=max(240, 30 * len(df)))
    fig.update_xaxes(showgrid=False, showticklabels=False, linecolor="rgba(0,0,0,0)")
    fig.update_yaxes(showgrid=False, linecolor=p.baseline, tickfont=dict(color=p.text_secondary))
    # Place à droite (axe + marge) pour que les étiquettes de valeur ne soient pas coupées.
    fig.update_xaxes(range=[0, df[value_col].max() * 1.15] if len(df) else None)
    fig.update_layout(bargap=0.3, margin=dict(r=72))
    return fig

