import { useMemo } from "react";

import { Chart } from "../components/Chart";
import { DataDetails } from "../components/DataTable";
import { Kpi, KpiGrid } from "../components/Kpi";
import { Notice, NoComparison, Page, Section, deltaNote, type Loaded } from "../components/Page";
import type { SatisfactionData, ScoreGroup } from "../lib/api";
import { barChart, barHeight, tooltipHtml, trendChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import { absoluteDelta, pointDelta, relativeDelta } from "../lib/delta";
import * as fmt from "../lib/format";
import { useTokens, type Tokens } from "../lib/theme";

export function Satisfaction() {
  const { filters } = useFilters();
  const state = usePageData<SatisfactionData>("satisfaction", filters);
  return (
    <Page title="Satisfaction" intro="Avis laissés par les clients après leur commande, notés de 1 à 5 étoiles." state={state}>
      {(data) => <Content data={data} />}
    </Page>
  );
}

const share = (v: number | null) => fmt.orDash(v, (x) => fmt.percent(x));

/** Barres de note moyenne, avec la part d'insatisfaits au survol. */
function scoreBars<T extends ScoreGroup>(rows: T[], label: (row: T) => string, t: Tokens) {
  return barChart(
    rows.map((r) => ({
      label: label(r),
      value: r.review_score,
      text: r.review_score == null ? "" : fmt.number(r.review_score, 2),
      tooltip: [
        `Note moyenne : ${fmt.orDash(r.review_score, fmt.score)}`,
        `Insatisfaits (1-2 ★) : ${fmt.orDash(r.dissatisfied_share, (v) => fmt.percent(v, 0))}`,
        `Commandes notées : ${fmt.number(r.orders)}`,
      ],
    })),
    t,
  );
}

function Content({ data }: { data: Loaded<SatisfactionData> }) {
  const t = useTokens();
  const { kpis, previous_kpis: prev, monthly } = data;
  const note = deltaNote(data);
  const last12 = monthly.slice(-12);

  const distribution = useMemo(
    () =>
      barChart(
        data.distribution.map((d) => ({
          label: d.label,
          value: d.share,
          text: fmt.percent(d.share, 0),
          tooltip: [`${fmt.percent(d.share)} des commandes notées`, `Commandes : ${fmt.number(d.orders)}`],
        })),
        t,
      ),
    [data.distribution, t],
  );
  const trend = useMemo(
    () =>
      trendChart(
        {
          months: monthly.map((m) => m.month),
          values: monthly.map((m) => m.review_score),
          yFormat: (v) => fmt.number(v, 1),
          zeroBased: false,
          tooltip: (i) =>
            tooltipHtml(fmt.monthLabel(monthly[i].month), [
              `Note moyenne : ${fmt.score(monthly[i].review_score)}`,
              `Insatisfaits : ${fmt.percent(monthly[i].dissatisfied_share)}`,
              `Commandes notées : ${fmt.number(monthly[i].reviewed)}`,
            ]),
        },
        t,
      ),
    [monthly, t],
  );
  const byDelivery = useMemo(() => scoreBars(data.by_delivery, (r) => r.group, t), [data.by_delivery, t]);
  const byItems = useMemo(() => scoreBars(data.by_items, (r) => r.group, t), [data.by_items, t]);

  const ranked = useMemo(
    () => data.categories.filter((c) => c.orders >= data.category_threshold),
    [data.categories, data.category_threshold],
  );
  const n = Math.min(10, Math.floor(ranked.length / 2));
  const worst = useMemo(() => scoreBars(ranked.slice(0, n), (r) => r.category, t), [ranked, n, t]);
  const best = useMemo(() => scoreBars(ranked.slice(-n).reverse(), (r) => r.category, t), [ranked, n, t]);

  return (
    <>
      <KpiGrid>
        <Kpi
          label="Note moyenne"
          value={fmt.orDash(kpis.average_review, fmt.score)}
          delta={absoluteDelta(kpis.average_review, prev?.average_review)}
          deltaNote={note}
          trend={last12.map((m) => m.review_score)}
        />
        <Kpi
          label="Clients satisfaits"
          value={share(kpis.satisfied_share)}
          delta={pointDelta(kpis.satisfied_share, prev?.satisfied_share)}
          deltaNote={note}
          help="Part des commandes notées 4 ou 5 étoiles."
        />
        <Kpi
          label="Clients insatisfaits"
          value={share(kpis.dissatisfied_share)}
          delta={pointDelta(kpis.dissatisfied_share, prev?.dissatisfied_share, "inverse")}
          deltaNote={note}
          trend={last12.map((m) => m.dissatisfied_share)}
          help="Part des commandes notées 1 ou 2 étoiles."
        />
        <Kpi
          label="Commandes notées"
          value={fmt.number(kpis.reviewed)}
          delta={relativeDelta(kpis.reviewed, prev?.reviewed, "off")}
          deltaNote={note}
          help={`${share(kpis.response_rate)} des commandes de la période ont reçu un avis.`}
        />
        <Kpi
          label="Avis avec commentaire"
          value={share(kpis.comment_rate)}
          delta={pointDelta(kpis.comment_rate, prev?.comment_rate, "off")}
          deltaNote={note}
          help="Part des commandes notées dont l'avis contient un message écrit."
        />
        <Kpi
          label="Insatisfaits qui commentent"
          value={share(kpis.dissatisfied_comment_rate)}
          delta={pointDelta(kpis.dissatisfied_comment_rate, prev?.dissatisfied_comment_rate, "off")}
          deltaNote={note}
          help="Part des avis à 1 ou 2 étoiles qui contiennent un message écrit : les clients mécontents s'expriment bien plus que les autres."
        />
      </KpiGrid>
      <NoComparison data={data} />

      <div className="grid-2 section">
        <div>
          <h2>Répartition des notes</h2>
          <Chart option={distribution} height={barHeight(data.distribution.length)} label="Part des commandes par nombre d'étoiles" />
          <p className="caption">Une commande notée plusieurs fois compte pour la moyenne de ses avis, arrondie.</p>
        </div>
        <div>
          <h2>Note moyenne mensuelle</h2>
          <Chart option={trend} label="Note moyenne par mois d'achat" />
          <p className="caption">
            Par mois d'achat. L'axe ne part pas de zéro. À comparer avec le taux de retard mensuel de la page Logistique.
          </p>
        </div>
      </div>

      <Section title="Ce qui fait baisser la note">
        <div className="grid-2">
          <div>
            <h3>Selon la livraison</h3>
            <Chart option={byDelivery} height={barHeight(data.by_delivery.length)} label="Note moyenne selon la livraison" />
            <p className="caption">
              « Non livrée » : commande annulée, indisponible ou pas encore livrée. Le détail par jour de retard est sur la page Logistique.
            </p>
          </div>
          <div>
            <h3>Selon le nombre d'articles</h3>
            <Chart option={byItems} height={barHeight(data.by_items.length)} label="Note moyenne selon le nombre d'articles" />
            <p className="caption">
              Une commande de plusieurs articles peut venir de plusieurs vendeurs et arriver en plusieurs colis.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Notes par catégorie">
        {n < 1 ? (
          <Notice>Pas assez d'avis pour classer les catégories avec ces filtres.</Notice>
        ) : (
          <>
            <div className="grid-2">
              <div>
                <h3>Les {n} moins bien notées</h3>
                <Chart option={worst} height={barHeight(n)} label="Catégories les moins bien notées" />
              </div>
              <div>
                <h3>Les {n} mieux notées</h3>
                <Chart option={best} height={barHeight(n)} label="Catégories les mieux notées" />
              </div>
            </div>
            <p className="caption">
              Catégories ayant au moins {fmt.number(data.category_threshold)} commandes notées ({ranked.length} sur{" "}
              {data.categories.length}). Une commande compte dans chaque catégorie de produits qu'elle contient.
            </p>
          </>
        )}
        <DataDetails
          summary="Voir toutes les catégories en tableau"
          caption="Note moyenne par catégorie"
          rows={data.categories}
          columns={[
            { key: "category", label: "Catégorie" },
            { key: "review_score", label: "Note moyenne", align: "right", format: (v) => (v == null ? "–" : fmt.number(Number(v), 2)) },
            { key: "dissatisfied_share", label: "Insatisfaits", align: "right", format: (v) => (v == null ? "–" : fmt.percent(Number(v))) },
            { key: "orders", label: "Commandes notées", align: "right", format: (v) => fmt.number(Number(v)) },
          ]}
        />
        <DataDetails
          summary="Voir les données mensuelles en tableau"
          caption="Note et insatisfaction par mois"
          rows={monthly}
          columns={[
            { key: "month", label: "Mois", format: (v) => fmt.shortMonth(String(v)) },
            { key: "review_score", label: "Note moyenne", align: "right", format: (v) => fmt.number(Number(v), 2) },
            { key: "dissatisfied_share", label: "Insatisfaits", align: "right", format: (v) => fmt.percent(Number(v)) },
            { key: "reviewed", label: "Commandes notées", align: "right", format: (v) => fmt.number(Number(v)) },
          ]}
        />
      </Section>
    </>
  );
}
