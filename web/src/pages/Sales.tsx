import { CalendarRange, CreditCard, DollarSign, ShoppingBasket, ShoppingCart, Truck } from "lucide-react";
import { useMemo } from "react";

import { Chart } from "../components/Chart";
import { DataDetails } from "../components/DataTable";
import { Kpi } from "../components/Kpi";
import { Card, Grid, Page, comparisonLabel, type Loaded } from "../components/Page";
import type { SalesData } from "../lib/api";
import { barChart, barHeight, tooltipHtml, trendChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import { absoluteDelta, pointDelta, relativeDelta } from "../lib/delta";
import * as fmt from "../lib/format";
import { useTokens } from "../lib/theme";

export function Sales() {
  const { filters } = useFilters();
  const state = usePageData<SalesData>("sales", filters);
  return (
    <Page title="Ventes" intro="Chiffre d'affaires, panier moyen et moyens de paiement" state={state}>
      {(data) => <Content data={data} />}
    </Page>
  );
}

function Content({ data }: { data: Loaded<SalesData> }) {
  const t = useTokens();
  const { kpis, previous_kpis: prev, monthly } = data;
  const note = comparisonLabel(data) ?? "Pas de comparaison";
  const last12 = monthly.slice(-12);

  const monthTooltip = (i: number) =>
    tooltipHtml(fmt.monthLabel(monthly[i].month), [
      `Chiffre d'affaires : ${fmt.currency(monthly[i].revenue)}`,
      `Commandes : ${fmt.number(monthly[i].orders)}`,
      `Panier moyen : ${fmt.currency(monthly[i].revenue / monthly[i].orders, 2)}`,
    ]);
  const revenue = useMemo(
    () =>
      trendChart(
        { months: monthly.map((m) => m.month), values: monthly.map((m) => m.revenue), yFormat: (v) => `R$ ${fmt.compactTick(v)}`, tooltip: monthTooltip },
        t,
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [monthly, t],
  );
  const basket = useMemo(
    () =>
      trendChart(
        {
          months: monthly.map((m) => m.month),
          values: monthly.map((m) => m.revenue / m.orders),
          yFormat: (v) => `R$ ${fmt.number(v)}`,
          tooltip: monthTooltip,
          zeroBased: false,
        },
        t,
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [monthly, t],
  );
  const payments = useMemo(
    () =>
      barChart(
        data.payments.map((p) => ({
          label: p.label,
          value: p.share,
          text: fmt.percent(p.share),
          tooltip: [`${fmt.percent(p.share)} des commandes`, `Commandes : ${fmt.number(p.orders)}`, `Panier moyen : ${fmt.currency(p.basket, 2)}`],
        })),
        t,
      ),
    [data.payments, t],
  );
  const installments = useMemo(
    () =>
      barChart(
        data.installments.map((i) => ({
          label: i.group,
          value: i.basket,
          text: fmt.orDash(i.basket, (v) => fmt.currency(v)),
          tooltip: [
            `Panier moyen : ${fmt.orDash(i.basket, (v) => fmt.currency(v, 2))}`,
            `Part des paiements par carte : ${fmt.percent(i.share)}`,
            `Commandes : ${fmt.number(i.orders)}`,
          ],
        })),
        t,
      ),
    [data.installments, t],
  );

  return (
    <>
      <Grid cols="3">
        <Kpi label="Chiffre d'affaires" icon={DollarSign} value={fmt.compactCurrency(kpis.revenue)}
          delta={relativeDelta(kpis.revenue, prev?.revenue)} note={note} trend={last12.map((m) => m.revenue)}
          help="Prix des articles + frais de port, hors commandes annulées ou indisponibles." />
        <Kpi label="Commandes" icon={ShoppingCart} value={fmt.number(kpis.orders)}
          delta={relativeDelta(kpis.orders, prev?.orders)} note={note} trend={last12.map((m) => m.orders)} />
        <Kpi label="Panier moyen" icon={ShoppingBasket} value={fmt.orDash(kpis.average_basket, (v) => fmt.currency(v, 2))}
          delta={relativeDelta(kpis.average_basket, prev?.average_basket)} note={note}
          trend={last12.map((m) => m.revenue / m.orders)} help="Chiffre d'affaires / nombre de commandes." />
        <Kpi label="Part du port dans le CA" icon={Truck} value={fmt.orDash(kpis.freight_share, (v) => fmt.percent(v))}
          delta={pointDelta(kpis.freight_share, prev?.freight_share, "inverse")} note={note}
          help="Frais de port / (prix des articles + frais de port)." />
        <Kpi label="Paiement par carte de crédit" icon={CreditCard} value={fmt.orDash(kpis.credit_card_share, (v) => fmt.percent(v))}
          delta={pointDelta(kpis.credit_card_share, prev?.credit_card_share, "off")} note={note}
          help="Part des commandes payées principalement par carte de crédit." />
        <Kpi label="Mensualités moyennes (carte)" icon={CalendarRange} value={fmt.orDash(kpis.average_installments, (v) => fmt.number(v, 1))}
          delta={absoluteDelta(kpis.average_installments, prev?.average_installments, "", 1, "off")} note={note}
          help="Nombre moyen de mensualités des commandes payées par carte de crédit." />
      </Grid>

      <Grid cols="2">
        <Card title="Chiffre d'affaires mensuel" subtitle="Par mois d'achat">
          <Chart option={revenue} height={280} label="Chiffre d'affaires par mois" />
        </Card>
        <Card title="Panier moyen mensuel" subtitle="Par mois d'achat ; l'axe ne part pas de zéro">
          <Chart option={basket} height={280} label="Panier moyen par mois" />
        </Card>
      </Grid>

      <Grid cols="2">
        <Card title="Moyens de paiement" subtitle="Part des commandes, selon le moyen principal">
          <Chart option={payments} height={barHeight(data.payments.length)} label="Part des commandes par moyen de paiement" />
          <p className="caption">Le boleto est un bordereau bancaire payé en espèces ou en ligne.</p>
        </Card>
        <Card title="Panier moyen selon les mensualités" subtitle="Commandes payées par carte de crédit">
          <Chart option={installments} height={barHeight(data.installments.length)} label="Panier moyen selon le nombre de mensualités" />
          <p className="caption">Plus le panier est gros, plus le paiement est étalé.</p>
        </Card>
      </Grid>

      <Card className="spaced">
        <DataDetails
          summary="Voir les données mensuelles en tableau"
          caption="Ventes par mois"
          rows={monthly}
          columns={[
            { key: "month", label: "Mois", format: (v) => fmt.shortMonth(String(v)) },
            { key: "revenue", label: "Chiffre d'affaires", align: "right", format: (v) => fmt.currency(Number(v)) },
            { key: "orders", label: "Commandes", align: "right", format: (v) => fmt.number(Number(v)) },
            { key: "customers", label: "Clients", align: "right", format: (v) => fmt.number(Number(v)) },
          ]}
        />
      </Card>
    </>
  );
}
