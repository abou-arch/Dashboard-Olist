import { CalendarCheck, Clock, Hourglass, PackageCheck, TriangleAlert, Truck } from "lucide-react";
import { useMemo } from "react";

import { Chart } from "../components/Chart";
import { DataDetails, DataTable } from "../components/DataTable";
import { Kpi } from "../components/Kpi";
import { Card, Grid, Page, comparisonLabel, type Loaded } from "../components/Page";
import type { DeliveriesData } from "../lib/api";
import { barChart, barHeight, histogramChart, stackedChart, tooltipHtml, trendChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import { absoluteDelta, pointDelta } from "../lib/delta";
import * as fmt from "../lib/format";
import { useTokens } from "../lib/theme";

export function Deliveries() {
  const { filters } = useFilters();
  const state = usePageData<DeliveriesData>("deliveries", filters);
  return (
    <Page title="Livraisons" intro="Délais et retards, commandes livrées uniquement" state={state}>
      {(data) => <Content data={data} />}
    </Page>
  );
}

const days = (v: number | null, decimals = 1) => fmt.orDash(v, (x) => fmt.days(x, decimals));
const optional = (format: (v: number) => string) => (v: unknown) => (v == null ? "–" : format(Number(v)));

function Content({ data }: { data: Loaded<DeliveriesData> }) {
  const t = useTokens();
  const { kpis, previous_kpis: prev, monthly, stages } = data;
  const note = comparisonLabel(data) ?? "Pas de comparaison";
  const last12 = monthly.slice(-12);

  const histogram = useMemo(
    () =>
      histogramChart(
        data.histogram.map((b) => ({ label: b.label, value: b.orders })),
        (i) => {
          const bin = data.histogram[i];
          return tooltipHtml(`Livrées en ${bin.label} jour${bin.days > 1 ? "s" : ""}`, [`${fmt.number(bin.orders)} commandes`]);
        },
        t,
      ),
    [data.histogram, t],
  );
  const byDelay = useMemo(
    () =>
      barChart(
        data.review_by_delay.map((b) => ({
          label: b.bucket,
          value: b.review_score,
          text: b.review_score == null ? "" : fmt.number(b.review_score, 2),
          tooltip: [
            `Note moyenne : ${fmt.orDash(b.review_score, fmt.score)}`,
            `Notes de 1 ou 2 : ${fmt.orDash(b.low_scores, (v) => fmt.percent(v, 0))}`,
            `Commandes notées : ${fmt.number(b.orders)}`,
          ],
        })),
        t,
      ),
    [data.review_by_delay, t],
  );
  const lateTrend = useMemo(
    () =>
      trendChart(
        {
          months: monthly.map((m) => m.month),
          values: monthly.map((m) => m.late_rate),
          yFormat: (v) => fmt.percent(v, 0),
          tooltip: (i) =>
            tooltipHtml(fmt.monthLabel(monthly[i].month), [
              `En retard : ${fmt.percent(monthly[i].late_rate)}`,
              `Commandes livrées : ${fmt.number(monthly[i].delivered)}`,
            ]),
        },
        t,
      ),
    [monthly, t],
  );
  const stageChart = useMemo(
    () =>
      stackedChart(
        stages.map((s) => s.month),
        (["approval", "handling", "transit"] as const).map((key) => ({
          name: data.stage_labels[key],
          values: stages.map((s) => s[key]),
        })),
        "j",
        t,
      ),
    [stages, data.stage_labels, t],
  );
  const byState = useMemo(
    () =>
      barChart(
        data.by_state.map((s) => ({
          label: s.customer_state,
          value: s.delivery_days,
          text: fmt.days(s.delivery_days),
          tooltip: [`Délai moyen : ${fmt.days(s.delivery_days)}`, `En retard : ${fmt.percent(s.late_rate)}`, `Commandes livrées : ${fmt.number(s.delivered)}`],
        })),
        t,
      ),
    [data.by_state, t],
  );
  const { very_late: veryLate, early } = data.low_score_rates;

  return (
    <>
      <Grid cols="3">
        <Kpi label="Délai de livraison moyen" icon={Clock} value={days(kpis.average_delivery_days)}
          delta={absoluteDelta(kpis.average_delivery_days, prev?.average_delivery_days, " j", 1, "inverse")} note={note}
          trend={last12.map((m) => m.delivery_days)} help={`De l'achat à la réception. Médiane : ${days(kpis.median_delivery_days)}.`} />
        <Kpi label="Livraisons en retard" icon={TriangleAlert} value={fmt.orDash(kpis.late_rate, (v) => fmt.percent(v))}
          delta={pointDelta(kpis.late_rate, prev?.late_rate, "inverse")} note={note}
          trend={last12.map((m) => m.late_rate)} help="Livrées après la date estimée annoncée au client." />
        <Kpi label="Retard moyen quand il y a retard" icon={Hourglass} value={days(kpis.average_delay_when_late)}
          delta={absoluteDelta(kpis.average_delay_when_late, prev?.average_delay_when_late, " j", 1, "inverse")} note={note} />
        <Kpi label="Avance médiane sur la date estimée" icon={CalendarCheck} value={days(kpis.median_margin_days, 0)}
          delta={absoluteDelta(kpis.median_margin_days, prev?.median_margin_days, " j", 0, "off")} note={note}
          help="La moitié des commandes arrive au moins ce nombre de jours avant la date annoncée : les estimations sont prudentes." />
        <Kpi label="Préparation par le vendeur" icon={PackageCheck} value={days(kpis.average_handling_days)}
          delta={absoluteDelta(kpis.average_handling_days, prev?.average_handling_days, " j", 1, "inverse")} note={note}
          help="Délai moyen entre la validation du paiement et la remise au transporteur." />
        <Kpi label="Part du port dans le CA" icon={Truck} value={fmt.orDash(kpis.freight_share, (v) => fmt.percent(v))}
          delta={pointDelta(kpis.freight_share, prev?.freight_share, "inverse")} note={note} />
      </Grid>

      <Grid cols="2">
        <Card
          title="Distribution des délais"
          subtitle="Jours entre l'achat et la livraison"
          aside={
            kpis.median_delivery_days != null && (
              <div className="badge">
                <span>Médiane</span>
                <strong>{fmt.number(kpis.median_delivery_days, 0)} jours</strong>
              </div>
            )
          }
        >
          <Chart option={histogram} height={barHeight(7)} label="Nombre de commandes livrées par délai" />
        </Card>
        <Card title="La note chute dès le premier jour de retard" subtitle="Note moyenne selon l'écart à la date estimée">
          <Chart option={byDelay} height={barHeight(data.review_by_delay.length)} label="Note moyenne selon l'écart à la date de livraison estimée" />
          {veryLate != null && early != null && (
            <p className="caption">
              {fmt.percent(veryLate, 0)} des commandes livrées avec 4 jours de retard ou plus reçoivent une note de 1 ou 2, contre{" "}
              {fmt.percent(early, 0)} des commandes livrées en avance.
            </p>
          )}
        </Card>
      </Grid>

      <Grid cols="2">
        <Card title="Taux de retard mensuel" subtitle="Par mois d'achat">
          <Chart option={lateTrend} height={280} label="Taux de retard par mois d'achat" />
        </Card>
        <Card title="Délai moyen par étape" subtitle="Les commandes aux dates incohérentes (≈ 1,5 %) sont écartées">
          <Chart option={stageChart} height={280} label="Délai moyen de chaque étape de livraison par mois" />
        </Card>
      </Grid>

      <Grid cols="2">
        <Card title="Délai moyen par État" subtitle="État du client">
          <Chart option={byState} height={barHeight(data.by_state.length)} label="Délai de livraison moyen par État du client" />
        </Card>
        <Card title="Indicateurs par État">
          <DataTable
            caption="Indicateurs de livraison par État"
            rows={data.by_state}
            columns={[
              { key: "customer_state", label: "État" },
              { key: "delivery_days", label: "Délai", align: "right", format: (v) => fmt.days(Number(v)) },
              { key: "late_rate", label: "En retard", align: "right", format: (v) => fmt.percent(Number(v)) },
              { key: "freight_value", label: "Port moyen", align: "right", format: (v) => fmt.currency(Number(v), 2) },
              { key: "review_score", label: "Note", align: "right", format: optional((v) => fmt.number(v, 2)) },
              { key: "delivered", label: "Livrées", align: "right", format: (v) => fmt.number(Number(v)) },
            ]}
          />
        </Card>
      </Grid>

      <Card className="spaced">
        <DataDetails
          summary="Voir les données mensuelles en tableau"
          caption="Retards et délais par mois"
          rows={monthly.map((m) => ({ ...stages.find((s) => s.month === m.month), ...m }))}
          columns={[
            { key: "month", label: "Mois", format: (v) => fmt.shortMonth(String(v)) },
            { key: "late_rate", label: "En retard", align: "right", format: (v) => fmt.percent(Number(v)) },
            { key: "delivery_days", label: "Délai moyen", align: "right", format: (v) => fmt.days(Number(v)) },
            { key: "approval", label: data.stage_labels.approval, align: "right", format: optional((v) => fmt.days(v)) },
            { key: "handling", label: data.stage_labels.handling, align: "right", format: optional((v) => fmt.days(v)) },
            { key: "transit", label: data.stage_labels.transit, align: "right", format: optional((v) => fmt.days(v)) },
            { key: "delivered", label: "Livrées", align: "right", format: (v) => fmt.number(Number(v)) },
          ]}
        />
      </Card>
    </>
  );
}
