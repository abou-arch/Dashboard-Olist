import { ChartPie, Package, Store, Tag, Users, Wallet } from "lucide-react";
import { useMemo, useState } from "react";

import { Chart } from "../components/Chart";
import { DataDetails, DataTable, type Column } from "../components/DataTable";
import { Kpi } from "../components/Kpi";
import { Card, Grid, Notice, Page, comparisonLabel, type Loaded } from "../components/Page";
import type { ProductsData, Seller } from "../lib/api";
import { barChart, barHeight, concentrationChart, scatterChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import { pointDelta, relativeDelta } from "../lib/delta";
import * as fmt from "../lib/format";
import { useTokens } from "../lib/theme";

export function Products() {
  const { filters } = useFilters();
  const state = usePageData<ProductsData>("products", filters);
  return (
    <Page title="Produits" intro="Catégories et vendeurs de la place de marché" state={state}>
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

function Content({ data }: { data: Loaded<ProductsData> }) {
  const t = useTokens();
  const [tab, setTab] = useState<"top" | "watch">("top");
  const { kpis, previous_kpis: prev } = data;
  const note = comparisonLabel(data) ?? "Pas de comparaison";

  const topCategories = useMemo(
    () =>
      barChart(
        data.categories.slice(0, 10).map((c) => ({
          label: c.category,
          value: c.revenue,
          text: fmt.compactCurrency(c.revenue),
          tooltip: [`CA : ${fmt.currency(c.revenue)}`, `Part du CA : ${fmt.percent(c.share)}`, `Vendeurs : ${fmt.number(c.sellers)}`],
        })),
        t,
      ),
    [data.categories, t],
  );
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

  return (
    <>
      <Grid cols="3">
        <Kpi label="Catégories vendues" icon={Package} value={fmt.number(kpis.categories)}
          delta={relativeDelta(kpis.categories, prev?.categories, "off")} note={note} />
        <Kpi label="Prix moyen d'un article" icon={Tag} value={fmt.orDash(kpis.average_item_price, (v) => fmt.currency(v, 2))}
          delta={relativeDelta(kpis.average_item_price, prev?.average_item_price, "off")} note={note}
          help="Prix de vente moyen d'un article, hors frais de port." />
        <Kpi label="Vendeurs actifs" icon={Store} value={fmt.number(kpis.active_sellers)}
          delta={relativeDelta(kpis.active_sellers, prev?.active_sellers)} note={note}
          help="Vendeurs ayant réalisé au moins une vente sur la période." />
        <Kpi label="CA médian par vendeur" icon={Wallet} value={fmt.orDash(kpis.median_revenue, (v) => fmt.currency(v))}
          delta={relativeDelta(kpis.median_revenue, prev?.median_revenue)} note={note}
          help="La moitié des vendeurs réalise moins que ce chiffre d'affaires sur la période." />
        <Kpi label="CA des 10 % premiers vendeurs" icon={ChartPie} value={fmt.orDash(kpis.top10_share, (v) => fmt.percent(v, 0))}
          delta={pointDelta(kpis.top10_share, prev?.top10_share, "off")} note={note}
          help="Plus ce chiffre est élevé, plus les ventes reposent sur peu de vendeurs." />
        <Kpi label={`Vendeurs à moins de ${data.small_seller_orders} commandes`} icon={Users}
          value={fmt.orDash(kpis.small_seller_share, (v) => fmt.percent(v, 0))}
          delta={pointDelta(kpis.small_seller_share, prev?.small_seller_share, "off")} note={note} />
      </Grid>

      <Grid cols="2">
        <Card title="Top 10 des catégories" subtitle="Chiffre d'affaires sur la période">
          <Chart option={topCategories} height={barHeight(Math.min(10, data.categories.length))} label="Chiffre d'affaires des 10 premières catégories" />
        </Card>
        <Card title="Concentration des ventes" subtitle="Vendeurs classés du plus gros CA au plus petit">
          <Chart option={concentration} height={300} label="Part cumulée du chiffre d'affaires selon la part des vendeurs" />
        </Card>
      </Grid>

      <Card className="spaced" title="Chiffre d'affaires et satisfaction par catégorie"
        subtitle="En bas à droite : les catégories qui pèsent lourd mais déçoivent">
        {plotted.length < 2 ? (
          <Notice>Pas assez d'avis pour comparer les catégories avec ces filtres.</Notice>
        ) : (
          <>
            <Chart option={scatter} height={440} label="Chiffre d'affaires et note moyenne de chaque catégorie" />
            <p className="caption">
              {plotted.length} catégories ayant au moins {fmt.number(data.category_threshold)} commandes notées ; les 8 plus gros CA sont nommées.
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
      </Card>

      <Card className="spaced" title="Vendeurs" subtitle="Les données d'Olist ne donnent pas leur nom : seul le début de l'identifiant est affiché">
        <div className="tabs" role="tablist">
          <button type="button" role="tab" aria-selected={tab === "top"} onClick={() => setTab("top")}>
            Plus gros chiffres d'affaires
          </button>
          <button type="button" role="tab" aria-selected={tab === "watch"} onClick={() => setTab("watch")}>
            À surveiller
          </button>
        </div>
        {tab === "top" ? (
          <DataTable caption="Les 10 vendeurs au plus gros chiffre d'affaires" rows={data.top_sellers} columns={SELLER_COLUMNS} />
        ) : data.watched_sellers.length === 0 ? (
          <Notice>Aucun vendeur n'a {data.watch_min_orders} commandes ou plus avec ces filtres.</Notice>
        ) : (
          <>
            <DataTable caption="Les 10 vendeurs les moins bien notés" rows={data.watched_sellers} columns={SELLER_COLUMNS} />
            <p className="caption">
              Les 10 moins bien notés parmi les {fmt.number(data.watched_count)} vendeurs qui ont au moins {data.watch_min_orders} commandes.
              La note et le retard sont ceux de la commande entière, même si elle contient des articles d'autres vendeurs (≈ 1 %).
            </p>
          </>
        )}
      </Card>
    </>
  );
}
