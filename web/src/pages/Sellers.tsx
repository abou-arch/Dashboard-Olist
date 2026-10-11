import { useMemo, useState } from "react";

import { Chart } from "../components/Chart";
import { DataDetails, DataTable, type Column } from "../components/DataTable";
import { Kpi, KpiGrid } from "../components/Kpi";
import { Notice, NoComparison, Page, Section, deltaNote, type Loaded } from "../components/Page";
import type { Seller, SellersData } from "../lib/api";
import { barChart, barHeight, concentrationChart, scatterChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import { pointDelta, relativeDelta } from "../lib/delta";
import * as fmt from "../lib/format";
import { useTokens } from "../lib/theme";

export function Sellers() {
  const { filters } = useFilters();
  const state = usePageData<SellersData>("sellers", filters);
  return (
    <Page
      title="Vendeurs et catégories"
      intro="Qui vend quoi sur la place de marché. Montants en réais (R$), hors commandes annulées."
      state={state}
    >
      {(data) => <Content data={data} />}
    </Page>
  );
}

const optional = (format: (v: number) => string) => (v: unknown) => (v == null ? "–" : format(Number(v)));

const SELLER_COLUMNS: Column<Seller>[] = [
  { key: "seller_id", label: "Vendeur", format: (v) => `${String(v).slice(0, 8)}…` },
  { key: "seller_state", label: "État" },
  { key: "revenue", label: "CA", align: "right", format: (v) => fmt.currency(Number(v)) },
  { key: "orders", label: "Commandes", align: "right", format: (v) => fmt.number(Number(v)) },
  { key: "average_price", label: "Prix moyen", align: "right", format: (v) => fmt.currency(Number(v), 2) },
  { key: "review_score", label: "Note", align: "right", format: optional((v) => fmt.number(v, 2)) },
  { key: "late_rate", label: "En retard", align: "right", format: optional((v) => fmt.percent(v)) },
];

function Content({ data }: { data: Loaded<SellersData> }) {
  const t = useTokens();
  const [tab, setTab] = useState<"top" | "watch">("top");
  const { kpis, previous_kpis: prev } = data;
  const note = deltaNote(data);

  const concentration = useMemo(
    () =>
      concentrationChart(
        data.concentration,
        kpis.top10_share == null
          ? null
          : { x: 0.1, y: kpis.top10_share, label: `10 % des vendeurs → ${fmt.percent(kpis.top10_share, 0)} du CA` },
        t,
      ),
    [data.concentration, kpis.top10_share, t],
  );
  const byState = useMemo(
    () =>
      barChart(
        data.by_seller_state.map((s) => ({
          label: s.seller_state,
          value: s.revenue,
          text: fmt.compactCurrency(s.revenue),
          tooltip: [
            `CA : ${fmt.currency(s.revenue)}`,
            `Part du CA : ${fmt.percent(s.share)}`,
            `Vendeurs : ${fmt.number(s.sellers)}`,
          ],
        })),
        t,
      ),
    [data.by_seller_state, t],
  );
  const plotted = useMemo(
    () => data.categories.filter((c) => c.reviews >= data.category_threshold && c.review_score != null),
    [data.categories, data.category_threshold],
  );
  const scatter = useMemo(
    () =>
      scatterChart(
        {
          points: plotted.map((c) => ({
            x: c.revenue,
            y: c.review_score!,
            name: c.category,
            tooltip: [
              `CA : ${fmt.currency(c.revenue)}`,
              `Note moyenne : ${fmt.score(c.review_score!)}`,
              `Commandes : ${fmt.number(c.orders)}`,
              `Vendeurs : ${fmt.number(c.sellers)}`,
            ],
          })),
          labeled: 8,
          reference:
            data.average_review == null
              ? null
              : { value: data.average_review, label: `note moyenne ${fmt.number(data.average_review, 2)}` },
          xName: "Chiffre d'affaires",
          yName: "Note moyenne",
          xFormat: (v) => `R$ ${fmt.compactTick(v)}`,
          yFormat: (v) => fmt.number(v, 1),
        },
        t,
      ),
    [plotted, data.average_review, t],
  );
  const stateShare = fmt.percent(data.by_seller_state.reduce((sum, s) => sum + s.share, 0), 0);

  return (
    <>
      <KpiGrid>
        <Kpi
          label="Vendeurs actifs"
          value={fmt.number(kpis.active_sellers)}
          delta={relativeDelta(kpis.active_sellers, prev?.active_sellers)}
          deltaNote={note}
          help="Vendeurs ayant réalisé au moins une vente sur la période."
        />
        <Kpi
          label="CA médian par vendeur"
          value={fmt.orDash(kpis.median_revenue, (v) => fmt.currency(v))}
          delta={relativeDelta(kpis.median_revenue, prev?.median_revenue)}
          deltaNote={note}
          help="La moitié des vendeurs réalise moins que ce chiffre d'affaires sur la période."
        />
        <Kpi
          label="Part du CA des 10 % premiers vendeurs"
          value={fmt.orDash(kpis.top10_share, (v) => fmt.percent(v, 0))}
          delta={pointDelta(kpis.top10_share, prev?.top10_share, "off")}
          deltaNote={note}
          help="Plus ce chiffre est élevé, plus les ventes reposent sur peu de vendeurs."
        />
        <Kpi
          label={`Vendeurs à moins de ${data.small_seller_orders} commandes`}
          value={fmt.orDash(kpis.small_seller_share, (v) => fmt.percent(v, 0))}
          delta={pointDelta(kpis.small_seller_share, prev?.small_seller_share, "off")}
          deltaNote={note}
          help="Part des vendeurs actifs qui ont reçu peu de commandes sur la période."
        />
        <Kpi
          label="Catégories vendues"
          value={fmt.number(kpis.categories)}
          delta={relativeDelta(kpis.categories, prev?.categories, "off")}
          deltaNote={note}
        />
        <Kpi
          label="Prix moyen d'un article"
          value={fmt.orDash(kpis.average_item_price, (v) => fmt.currency(v, 2))}
          delta={relativeDelta(kpis.average_item_price, prev?.average_item_price, "off")}
          deltaNote={note}
          help="Prix de vente moyen d'un article, hors frais de port."
        />
      </KpiGrid>
      <NoComparison data={data} />

      <div className="grid-2 section">
        <div>
          <h2>Concentration des ventes</h2>
          <Chart option={concentration} label="Part cumulée du chiffre d'affaires selon la part des vendeurs" />
          <p className="caption">Vendeurs classés du plus gros CA au plus petit.</p>
        </div>
        <div>
          <h2>CA par État du vendeur</h2>
          <Chart option={byState} height={barHeight(data.by_seller_state.length)} label="Chiffre d'affaires par État du vendeur" />
          <p className="caption">
            Ces {data.by_seller_state.length} États font {stateShare} du CA. Les filtres d'État portent sur le client, pas sur le vendeur.
          </p>
        </div>
      </div>

      <Section title="Catégories : chiffre d'affaires et satisfaction">
        {plotted.length < 2 ? (
          <Notice>Pas assez d'avis pour comparer les catégories avec ces filtres.</Notice>
        ) : (
          <>
            <Chart option={scatter} height={440} label="Chiffre d'affaires et note moyenne de chaque catégorie" />
            <p className="caption">
              {plotted.length} catégories ayant au moins {fmt.number(data.category_threshold)} commandes notées ; les 8 plus gros CA
              sont nommées. En bas à droite : les catégories qui pèsent lourd mais déçoivent.
            </p>
          </>
        )}
        <DataDetails
          summary="Voir toutes les catégories en tableau"
          caption="Indicateurs par catégorie"
          rows={data.categories}
          columns={[
            { key: "category", label: "Catégorie" },
            { key: "revenue", label: "CA", align: "right", format: (v) => fmt.currency(Number(v)) },
            { key: "share", label: "Part du CA", align: "right", format: (v) => fmt.percent(Number(v)) },
            { key: "orders", label: "Commandes", align: "right", format: (v) => fmt.number(Number(v)) },
            { key: "sellers", label: "Vendeurs", align: "right", format: (v) => fmt.number(Number(v)) },
            { key: "average_price", label: "Prix moyen", align: "right", format: (v) => fmt.currency(Number(v), 2) },
            { key: "review_score", label: "Note", align: "right", format: optional((v) => fmt.number(v, 2)) },
            { key: "late_rate", label: "En retard", align: "right", format: optional((v) => fmt.percent(v)) },
          ]}
        />
      </Section>

      <Section title="Vendeurs">
        <div className="tabs" role="tablist">
          <button type="button" role="tab" aria-selected={tab === "top"} onClick={() => setTab("top")}>
            Plus gros chiffres d'affaires
          </button>
          <button type="button" role="tab" aria-selected={tab === "watch"} onClick={() => setTab("watch")}>
            À surveiller
          </button>
        </div>
        {tab === "top" ? (
          <div className="table-card">
            <DataTable caption="Les 10 vendeurs au plus gros chiffre d'affaires" rows={data.top_sellers} columns={SELLER_COLUMNS} />
          </div>
        ) : data.watched_sellers.length === 0 ? (
          <Notice>Aucun vendeur n'a {data.watch_min_orders} commandes ou plus avec ces filtres.</Notice>
        ) : (
          <>
            <div className="table-card">
              <DataTable caption="Les 10 vendeurs les moins bien notés" rows={data.watched_sellers} columns={SELLER_COLUMNS} />
            </div>
            <p className="caption">
              Les 10 vendeurs les moins bien notés parmi ceux qui ont au moins {data.watch_min_orders} commandes (
              {fmt.number(data.watched_count)} vendeurs). La note et le retard sont ceux de la commande entière, même si elle contient
              des articles d'autres vendeurs (≈ 1 %).
            </p>
          </>
        )}
        <p className="caption">Les données d'Olist ne donnent pas le nom des vendeurs : seul le début de leur identifiant est affiché.</p>
      </Section>
    </>
  );
}
