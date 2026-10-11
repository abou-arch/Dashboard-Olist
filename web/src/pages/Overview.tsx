import { useMemo } from "react";

import { Chart } from "../components/Chart";
import { DataDetails } from "../components/DataTable";
import { Kpi, KpiGrid } from "../components/Kpi";
import { NoComparison, Page, Section, deltaNote, type Loaded } from "../components/Page";
import type { OverviewData } from "../lib/api";
import { barChart, barHeight, tooltipHtml, trendChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import { absoluteDelta, pointDelta, relativeDelta } from "../lib/delta";
import * as fmt from "../lib/format";
import { useTokens } from "../lib/theme";

export function Overview() {
  const { filters } = useFilters();
  const state = usePageData<OverviewData>("overview", filters);
  return (
    <Page title="Vue d'ensemble" intro="Olist, place de marché e-commerce brésilienne. Montants en réais (R$)." state={state}>
      {(data) => <Content data={data} />}
    </Page>
  );
}

function Content({ data }: { data: Loaded<OverviewData> }) {
  const t = useTokens();
  const { kpis, previous_kpis: prev, monthly } = data;
  const note = deltaNote(data);
  const last12 = monthly.slice(-12);

  const trend = useMemo(
    () =>
      trendChart(
        {
          months: monthly.map((m) => m.month),
          values: monthly.map((m) => m.revenue),
          yFormat: (v) => `R$ ${fmt.compactTick(v)}`,
          tooltip: (i) =>
            tooltipHtml(fmt.monthLabel(monthly[i].month), [
              `CA : ${fmt.currency(monthly[i].revenue)}`,
              `Commandes : ${fmt.number(monthly[i].orders)}`,
            ]),
        },
        t,
      ),
    [monthly, t],
  );
  const categories = useMemo(
    () =>
      barChart(
        data.categories.map((c) => ({
          label: c.category,
          value: c.revenue,
          text: fmt.compactCurrency(c.revenue),
          tooltip: [`CA : ${fmt.currency(c.revenue)}`, `Part du CA : ${fmt.percent(c.share)}`],
        })),
        t,
      ),
    [data.categories, t],
  );
  const states = useMemo(
    () =>
      barChart(
        data.by_state.map((s) => ({
          label: s.customer_state,
          value: s.revenue,
          text: fmt.compactCurrency(s.revenue),
          tooltip: [
            `CA : ${fmt.currency(s.revenue)}`,
            `Part du CA : ${fmt.percent(s.share)}`,
            `Commandes : ${fmt.number(s.orders)}`,
          ],
        })),
        t,
      ),
    [data.by_state, t],
  );
  const share = (rows: { share: number }[]) => fmt.percent(rows.reduce((sum, r) => sum + r.share, 0), 0);

  return (
    <>
      <KpiGrid>
        <Kpi
          label="Chiffre d'affaires"
          value={fmt.compactCurrency(kpis.revenue)}
          delta={relativeDelta(kpis.revenue, prev?.revenue)}
          deltaNote={note}
          trend={last12.map((m) => m.revenue)}
          help="Prix des articles + frais de port, hors commandes annulées ou indisponibles."
        />
        <Kpi
          label="Commandes"
          value={fmt.number(kpis.orders)}
          delta={relativeDelta(kpis.orders, prev?.orders)}
          deltaNote={note}
          trend={last12.map((m) => m.orders)}
          help={`${fmt.number(kpis.customers)} clients distincts.`}
        />
        <Kpi
          label="Panier moyen"
          value={fmt.orDash(kpis.average_basket, (v) => fmt.currency(v, 2))}
          delta={relativeDelta(kpis.average_basket, prev?.average_basket)}
          deltaNote={note}
          trend={last12.map((m) => m.revenue / m.orders)}
          help="Chiffre d'affaires / nombre de commandes."
        />
        <Kpi
          label="Note moyenne"
          value={fmt.orDash(kpis.average_review, fmt.score)}
          delta={absoluteDelta(kpis.average_review, prev?.average_review)}
          deltaNote={note}
          help="Moyenne des avis clients (1 à 5)."
        />
        <Kpi
          label="Livraisons en retard"
          value={fmt.orDash(kpis.late_rate, (v) => fmt.percent(v))}
          delta={pointDelta(kpis.late_rate, prev?.late_rate, "inverse")}
          deltaNote={note}
          help="Part des commandes livrées après la date estimée annoncée au client."
        />
        <Kpi
          label="Délai de livraison moyen"
          value={fmt.orDash(kpis.average_delivery_days, (v) => fmt.days(v))}
          delta={absoluteDelta(kpis.average_delivery_days, prev?.average_delivery_days, " j", 1, "inverse")}
          deltaNote={note}
          help="De l'achat à la réception par le client, commandes livrées uniquement."
        />
      </KpiGrid>
      <NoComparison data={data} />

      <Section title="Chiffre d'affaires mensuel">
        <Chart option={trend} label="Évolution mensuelle du chiffre d'affaires" />
        <DataDetails
          summary="Voir les données en tableau"
          caption="Chiffre d'affaires et commandes par mois"
          rows={monthly}
          columns={[
            { key: "month", label: "Mois", format: (v) => fmt.shortMonth(String(v)) },
            { key: "revenue", label: "CA (R$)", align: "right", format: (v) => fmt.number(Number(v), 2) },
            { key: "orders", label: "Commandes", align: "right", format: (v) => fmt.number(Number(v)) },
          ]}
        />
      </Section>

      <div className="grid-2 section">
        <div>
          <h2>Top 10 catégories</h2>
          <Chart option={categories} height={barHeight(data.categories.length)} label="Chiffre d'affaires des 10 premières catégories" />
          <p className="caption">Ces 10 catégories font {share(data.categories)} du CA.</p>
        </div>
        <div>
          <h2>Top 10 États</h2>
          <Chart option={states} height={barHeight(data.by_state.length)} label="Chiffre d'affaires des 10 premiers États" />
          <p className="caption">Ces 10 États font {share(data.by_state)} du CA.</p>
        </div>
      </div>
    </>
  );
}
