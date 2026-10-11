import { ArrowRight, DollarSign, ShoppingCart, Star, User } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useLocation } from "react-router";

import { BrazilMap, STATE_NAMES } from "../components/BrazilMap";
import { Chart } from "../components/Chart";
import { Kpi } from "../components/Kpi";
import { Card, Grid, Page, comparisonLabel, type Loaded } from "../components/Page";
import type { DashboardData } from "../lib/api";
import { donutChart, histogramChart, tooltipHtml, trendChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import { absoluteDelta, relativeDelta } from "../lib/delta";
import * as fmt from "../lib/format";
import { useTokens } from "../lib/theme";

export function Dashboard() {
  const { filters } = useFilters();
  const state = usePageData<DashboardData>("dashboard", filters);
  return (
    <Page title="Tableau de bord" intro="Vue d'ensemble des performances de la plateforme Olist" state={state}>
      {(data) => <Content data={data} />}
    </Page>
  );
}

type Measure = "revenue" | "orders" | "basket";
const MEASURES: { key: Measure; label: string }[] = [
  { key: "revenue", label: "Chiffre d'affaires" },
  { key: "orders", label: "Commandes" },
  { key: "basket", label: "Panier moyen" },
];

/** Initiales d'une catégorie (« Bed bath table » -> « BB »), en guise de vignette. */
const initials = (name: string) =>
  name.split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("");

function Content({ data }: { data: Loaded<DashboardData> }) {
  const t = useTokens();
  const { search } = useLocation();
  const [measure, setMeasure] = useState<Measure>("revenue");
  const { kpis, previous_kpis: prev, monthly } = data;
  const note = comparisonLabel(data) ?? "Pas de comparaison";
  const last12 = monthly.slice(-12);

  const trend = useMemo(() => {
    const value = (m: (typeof monthly)[number]) =>
      measure === "revenue" ? m.revenue : measure === "orders" ? m.orders : m.revenue / m.orders;
    return trendChart(
      {
        months: monthly.map((m) => m.month),
        values: monthly.map(value),
        yFormat: (v) => (measure === "orders" ? fmt.compactTick(v) : `R$ ${fmt.compactTick(v)}`),
        tooltip: (i) =>
          tooltipHtml(fmt.monthLabel(monthly[i].month), [
            `Chiffre d'affaires : ${fmt.currency(monthly[i].revenue)}`,
            `Commandes : ${fmt.number(monthly[i].orders)}`,
            `Panier moyen : ${fmt.currency(monthly[i].revenue / monthly[i].orders, 2)}`,
          ]),
      },
      t,
    );
  }, [monthly, measure, t]);

  const regionValues = useMemo(
    () => Object.fromEntries(data.by_state.map((s) => [s.customer_state, s.revenue])),
    [data.by_state],
  );
  const topStates = data.by_state.slice(0, 5);
  const otherShare = data.by_state.slice(5).reduce((sum, s) => sum + s.share, 0);
  const maxShare = Math.max(otherShare, ...topStates.map((s) => s.share));

  const statusColors: Record<string, string> = {
    "Livrées": t.status.delivered,
    "En transit": t.status.transit,
    "En préparation": t.status.pending,
    "Annulées": t.status.canceled,
  };
  const totalOrders = data.statuses.reduce((sum, s) => sum + s.orders, 0);
  const donut = useMemo(
    () =>
      donutChart(
        data.statuses.map((s) => ({ name: s.status, value: s.orders, color: statusColors[s.status] })),
        { value: fmt.number(totalOrders), label: "commandes" },
        t,
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data.statuses, totalOrders, t],
  );

  const histogram = useMemo(
    () =>
      histogramChart(
        data.delivery_histogram.map((b) => ({ label: b.label, value: b.orders })),
        (i) => {
          const bin = data.delivery_histogram[i];
          const days = bin.label.endsWith("+") ? `${bin.label} jours` : `${bin.label} jour${bin.days > 1 ? "s" : ""}`;
          return tooltipHtml(`Livrées en ${days}`, [`${fmt.number(bin.orders)} commandes`]);
        },
        t,
      ),
    [data.delivery_histogram, t],
  );

  return (
    <>
      <Grid cols="4">
        <Kpi
          label="Chiffre d'affaires"
          icon={DollarSign}
          value={fmt.compactCurrency(kpis.revenue)}
          delta={relativeDelta(kpis.revenue, prev?.revenue)}
          note={note}
          trend={last12.map((m) => m.revenue)}
          help="Prix des articles + frais de port, hors commandes annulées ou indisponibles."
        />
        <Kpi
          label="Nombre de commandes"
          icon={ShoppingCart}
          value={fmt.number(kpis.orders)}
          delta={relativeDelta(kpis.orders, prev?.orders)}
          note={note}
          trend={last12.map((m) => m.orders)}
          help="Commandes passées sur la période, hors annulées ou indisponibles."
        />
        <Kpi
          label="Clients uniques"
          icon={User}
          value={fmt.number(kpis.customers)}
          delta={relativeDelta(kpis.customers, prev?.customers)}
          note={note}
          trend={last12.map((m) => m.customers)}
          help="Clients distincts ayant passé au moins une commande sur la période."
        />
        <Kpi
          label="Note moyenne des avis"
          icon={Star}
          value={
            kpis.average_review == null ? "–" : (
              <>
                {fmt.number(kpis.average_review, 2)} <small>/ 5</small>
              </>
            )
          }
          delta={absoluteDelta(kpis.average_review, prev?.average_review)}
          note={`Basé sur ${fmt.number(kpis.reviews)} avis`}
          trend={data.monthly_reviews.slice(-12).map((m) => m.review_score)}
          trendKind="bars"
          help="Moyenne des notes laissées par les clients (1 à 5 étoiles), par mois sur la courbe."
        />
      </Grid>

      <Grid cols="main">
        <Card
          title="Évolution des ventes"
          subtitle="Par mois d'achat"
          aside={
            <div className="segmented" role="group" aria-label="Mesure affichée">
              {MEASURES.map((m) => (
                <button key={m.key} type="button" aria-pressed={measure === m.key} onClick={() => setMeasure(m.key)}>
                  {m.label}
                </button>
              ))}
            </div>
          }
        >
          <Chart option={trend} height={300} label="Évolution mensuelle des ventes" />
        </Card>

        <Card title="Ventes par région" subtitle="Répartition du chiffre d'affaires au Brésil">
          <div className="region">
            <BrazilMap
              values={regionValues}
              t={t}
              label="Carte du chiffre d'affaires par État"
              tooltip={(state) => {
                const row = data.by_state.find((s) => s.customer_state === state);
                return row
                  ? [`CA : ${fmt.currency(row.revenue)}`, `Part : ${fmt.percent(row.share)}`, `Commandes : ${fmt.number(row.orders)}`]
                  : ["Aucune vente"];
              }}
            />
            <ul className="meter-list" aria-label="Part du chiffre d'affaires par État">
              {[
                ...topStates.map((s) => ({ name: STATE_NAMES[s.customer_state] ?? s.customer_state, share: s.share })),
                { name: "Autres", share: otherShare },
              ].map((row) => (
                <li key={row.name}>
                  <span>{row.name}</span>
                  <span className="meter" aria-hidden="true">
                    <span style={{ width: `${(row.share / (maxShare || 1)) * 100}%` }} />
                  </span>
                  <span className="value">{fmt.percent(row.share)}</span>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </Grid>

      <Grid cols="even-3">
        <Card
          title="Catégories les plus vendues"
          aside={
            <Link className="link-button" to={{ pathname: "/produits", search }}>
              Voir tout <ArrowRight size={14} aria-hidden="true" />
            </Link>
          }
        >
          <div className="table-wrap">
            <table>
              <caption className="sr-only">Les 5 catégories au plus gros chiffre d'affaires</caption>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Catégorie</th>
                  <th data-align="right">Ventes</th>
                  <th data-align="right">Part</th>
                </tr>
              </thead>
              <tbody>
                {data.categories.map((c, i) => (
                  <tr key={c.category}>
                    <td className="rank">{i + 1}</td>
                    <td className="wrap">
                      <span className="thumb" aria-hidden="true">{initials(c.category)}</span>
                      {c.category}
                    </td>
                    <td data-align="right">{fmt.compactCurrency(c.revenue)}</td>
                    <td data-align="right">{fmt.percent(c.share)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Statut des commandes">
          <div className="donut-layout">
            <Chart option={donut} height={220} label="Répartition des commandes par statut" />
            <ul className="status-list">
              {data.statuses.map((s) => (
                <li key={s.status}>
                  <span>
                    <span className="dot" style={{ background: statusColors[s.status] }} aria-hidden="true" />
                    {s.status}
                  </span>
                  <strong>{fmt.percent(s.share)}</strong>
                </li>
              ))}
            </ul>
          </div>
          <p className="caption">Toutes les commandes passées sur la période, annulées comprises.</p>
        </Card>

        <Card
          title="Délai de livraison"
          subtitle="Jours entre l'achat et la livraison"
          aside={
            data.median_delivery_days != null && (
              <div className="badge">
                <span>Médiane</span>
                <strong>{fmt.number(data.median_delivery_days, 0)} jours</strong>
              </div>
            )
          }
        >
          <Chart option={histogram} height={230} label="Nombre de commandes livrées par délai de livraison" />
        </Card>
      </Grid>
    </>
  );
}
