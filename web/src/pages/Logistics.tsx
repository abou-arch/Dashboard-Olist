import { useMemo } from "react";

import { Chart } from "../components/Chart";
import { DataDetails, DataTable } from "../components/DataTable";
import { Kpi, KpiGrid } from "../components/Kpi";
import { NoComparison, Page, Section, deltaNote, type Loaded } from "../components/Page";
import type { LogisticsData } from "../lib/api";
import { barChart, barHeight, stackedChart, tooltipHtml, trendChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import { absoluteDelta, pointDelta } from "../lib/delta";
import * as fmt from "../lib/format";
import { useTokens } from "../lib/theme";

export function Logistics() {
  const { filters } = useFilters();
  const state = usePageData<LogisticsData>("logistics", filters);
  return (
    <Page title="Logistique" intro="Délais et retards de livraison, commandes livrées uniquement." state={state}>
      {(data) => <Content data={data} />}
    </Page>
  );
}

const days = (v: number | null, decimals = 1) => fmt.orDash(v, (x) => fmt.days(x, decimals));
const share = (v: number | null) => fmt.orDash(v, (x) => fmt.percent(x));

function Content({ data }: { data: Loaded<LogisticsData> }) {
  const t = useTokens();
  const { kpis, previous_kpis: prev, monthly, stages } = data;
  const note = deltaNote(data);
  const last12 = monthly.slice(-12);

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
          tooltip: [
            `Délai moyen : ${fmt.days(s.delivery_days)}`,
            `En retard : ${fmt.percent(s.late_rate)}`,
            `Commandes livrées : ${fmt.number(s.delivered)}`,
          ],
        })),
        t,
      ),
    [data.by_state, t],
  );

  const { very_late: veryLate, early } = data.low_score_rates;

  return (
    <>
      <KpiGrid>
        <Kpi
          label="Délai de livraison moyen"
          value={days(kpis.average_delivery_days)}
          delta={absoluteDelta(kpis.average_delivery_days, prev?.average_delivery_days, " j", 1, "inverse")}
          deltaNote={note}
          trend={last12.map((m) => m.delivery_days)}
          help={`De l'achat à la réception. Médiane : ${days(kpis.median_delivery_days)}.`}
        />
        <Kpi
          label="Livraisons en retard"
          value={share(kpis.late_rate)}
          delta={pointDelta(kpis.late_rate, prev?.late_rate, "inverse")}
          deltaNote={note}
          trend={last12.map((m) => m.late_rate)}
          help="Part des commandes livrées après la date estimée annoncée au client."
        />
        <Kpi
          label="Retard moyen des commandes en retard"
          value={days(kpis.average_delay_when_late)}
          delta={absoluteDelta(kpis.average_delay_when_late, prev?.average_delay_when_late, " j", 1, "inverse")}
          deltaNote={note}
          help="Nombre moyen de jours après la date estimée, pour les seules commandes en retard."
        />
        <Kpi
          label="Avance médiane sur la date estimée"
          value={days(kpis.median_margin_days, 0)}
          delta={absoluteDelta(kpis.median_margin_days, prev?.median_margin_days, " j", 0, "off")}
          deltaNote={note}
          help="La moitié des commandes arrive au moins ce nombre de jours avant la date annoncée : les estimations d'Olist sont très prudentes."
        />
        <Kpi
          label="Préparation par le vendeur"
          value={days(kpis.average_handling_days)}
          delta={absoluteDelta(kpis.average_handling_days, prev?.average_handling_days, " j", 1, "inverse")}
          deltaNote={note}
          help="Délai moyen entre la validation du paiement et la remise au transporteur."
        />
        <Kpi
          label="Part du port dans le CA"
          value={share(kpis.freight_share)}
          delta={pointDelta(kpis.freight_share, prev?.freight_share, "inverse")}
          deltaNote={note}
          help="Frais de port / (prix des articles + frais de port), hors commandes annulées."
        />
      </KpiGrid>
      <NoComparison data={data} />

      <Section title="La note client chute dès le premier jour de retard">
        <Chart option={byDelay} height={barHeight(data.review_by_delay.length)} label="Note moyenne selon l'écart à la date de livraison estimée" />
        <p className="caption">
          Note moyenne sur 5, selon l'écart entre la livraison et la date estimée.
          {veryLate != null && early != null &&
            ` ${fmt.percent(veryLate, 0)} des commandes livrées avec 4 jours de retard ou plus reçoivent une note de 1 ou 2, contre ${fmt.percent(early, 0)} des commandes livrées en avance.`}
        </p>
      </Section>

      <div className="grid-2 section">
        <div>
          <h2>Taux de retard mensuel</h2>
          <Chart option={lateTrend} label="Taux de retard par mois d'achat" />
          <p className="caption">Par mois d'achat.</p>
        </div>
        <div>
          <h2>Délai moyen par étape</h2>
          <Chart option={stageChart} label="Délai moyen de chaque étape de livraison par mois" />
          <p className="caption">Par mois d'achat. Les commandes aux dates incohérentes (environ 1,5 %) sont écartées.</p>
        </div>
      </div>

      <Section title="Délai de livraison par État">
        <div className="grid-2">
          <Chart option={byState} height={barHeight(data.by_state.length)} label="Délai de livraison moyen par État du client" />
          <div className="table-card">
            <DataTable
              caption="Indicateurs de livraison par État"
              rows={data.by_state}
              columns={[
                { key: "customer_state", label: "État" },
                { key: "delivery_days", label: "Délai (j)", align: "right", format: (v) => fmt.number(Number(v), 1) },
                { key: "late_rate", label: "En retard", align: "right", format: (v) => fmt.percent(Number(v)) },
                { key: "freight_value", label: "Port moyen", align: "right", format: (v) => fmt.currency(Number(v), 2) },
                { key: "review_score", label: "Note", align: "right", format: (v) => (v == null ? "–" : fmt.number(Number(v), 2)) },
                { key: "delivered", label: "Livrées", align: "right", format: (v) => fmt.number(Number(v)) },
              ]}
            />
          </div>
        </div>
      </Section>

      <DataDetails
        summary="Voir les données mensuelles en tableau"
        caption="Retards et délais par mois"
        rows={monthly.map((m) => ({ ...stages.find((s) => s.month === m.month), ...m }))}
        columns={[
          { key: "month", label: "Mois", format: (v) => fmt.shortMonth(String(v)) },
          { key: "late_rate", label: "En retard", align: "right", format: (v) => fmt.percent(Number(v)) },
          { key: "delivery_days", label: "Délai moyen (j)", align: "right", format: (v) => fmt.number(Number(v), 1) },
          { key: "approval", label: `${data.stage_labels.approval} (j)`, align: "right", format: (v) => (v == null ? "–" : fmt.number(Number(v), 1)) },
          { key: "handling", label: `${data.stage_labels.handling} (j)`, align: "right", format: (v) => (v == null ? "–" : fmt.number(Number(v), 1)) },
          { key: "transit", label: `${data.stage_labels.transit} (j)`, align: "right", format: (v) => (v == null ? "–" : fmt.number(Number(v), 1)) },
          { key: "delivered", label: "Livrées", align: "right", format: (v) => fmt.number(Number(v)) },
        ]}
      />
    </>
  );
}
