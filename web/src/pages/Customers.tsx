import { Repeat, ShoppingCart, Users, Wallet } from "lucide-react";
import { useMemo } from "react";

import { Chart } from "../components/Chart";
import { Kpi } from "../components/Kpi";
import { Card, Grid, Page, comparisonLabel, type Loaded } from "../components/Page";
import type { CustomersData } from "../lib/api";
import { barChart, barHeight, heatmapChart, tooltipHtml, trendChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import { absoluteDelta, pointDelta, relativeDelta } from "../lib/delta";
import * as fmt from "../lib/format";
import { useTokens } from "../lib/theme";

export function Customers() {
  const { filters } = useFilters();
  const state = usePageData<CustomersData>("customers", filters);
  return (
    <Page title="Clients" intro="Qui achète, à quelle fréquence et à quel moment" state={state}>
      {(data) => <Content data={data} />}
    </Page>
  );
}

function Content({ data }: { data: Loaded<CustomersData> }) {
  const t = useTokens();
  const { kpis, previous_kpis: prev, monthly } = data;
  const note = comparisonLabel(data) ?? "Pas de comparaison";

  const customers = useMemo(
    () =>
      trendChart(
        {
          months: monthly.map((m) => m.month),
          values: monthly.map((m) => m.customers),
          yFormat: (v) => fmt.compactTick(v),
          tooltip: (i) =>
            tooltipHtml(fmt.monthLabel(monthly[i].month), [
              `Clients : ${fmt.number(monthly[i].customers)}`,
              `Commandes : ${fmt.number(monthly[i].orders)}`,
            ]),
        },
        t,
      ),
    [monthly, t],
  );
  const loyalty = useMemo(
    () =>
      barChart(
        data.loyalty.map((l) => ({
          label: l.group,
          value: l.share,
          text: fmt.percent(l.share),
          tooltip: [`${fmt.percent(l.share)} des clients`, `Clients : ${fmt.number(l.customers)}`],
        })),
        t,
      ),
    [data.loyalty, t],
  );
  const heatmap = useMemo(
    () => heatmapChart(data.heatmap.days, data.heatmap.hours.map((h) => `${h}h`), data.heatmap.values, "commandes", t),
    [data.heatmap, t],
  );

  return (
    <>
      <Grid cols="4">
        <Kpi label="Clients" icon={Users} value={fmt.number(kpis.customers)}
          delta={relativeDelta(kpis.customers, prev?.customers)} note={note}
          trend={monthly.slice(-12).map((m) => m.customers)}
          help="Clients distincts ayant passé au moins une commande sur la période." />
        <Kpi label="Clients revenus" icon={Repeat} value={fmt.orDash(kpis.repeat_rate, (v) => fmt.percent(v))}
          delta={pointDelta(kpis.repeat_rate, prev?.repeat_rate)} note={note}
          help="Part des clients ayant passé au moins deux commandes sur la période." />
        <Kpi label="CA par client" icon={Wallet} value={fmt.orDash(kpis.revenue_per_customer, (v) => fmt.currency(v, 2))}
          delta={relativeDelta(kpis.revenue_per_customer, prev?.revenue_per_customer)} note={note}
          help="Chiffre d'affaires de la période / nombre de clients." />
        <Kpi label="Commandes par client" icon={ShoppingCart} value={fmt.orDash(kpis.orders_per_customer, (v) => fmt.number(v, 2))}
          delta={absoluteDelta(kpis.orders_per_customer, prev?.orders_per_customer)} note={note} />
      </Grid>

      <Grid cols="main">
        <Card title="Clients par mois" subtitle="Clients distincts ayant commandé dans le mois">
          <Chart option={customers} height={280} label="Nombre de clients par mois" />
        </Card>
        <Card title="Fidélité" subtitle="Clients selon leur nombre de commandes">
          <Chart option={loyalty} height={barHeight(data.loyalty.length)} label="Part des clients selon leur nombre de commandes" />
          <p className="caption">
            Presque tous les clients n'achètent qu'une fois sur la période : la croissance repose sur l'acquisition.
          </p>
        </Card>
      </Grid>

      <Card className="spaced" title="Quand les clients achètent" subtitle="Commandes par jour de la semaine et heure (heure de Brasília)">
        <Chart option={heatmap} height={300} label="Nombre de commandes par jour de la semaine et heure" />
      </Card>
    </>
  );
}
