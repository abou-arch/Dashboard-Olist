import { useMemo } from "react";

import { Chart } from "../components/Chart";
import { DataTable } from "../components/DataTable";
import { Kpi, KpiGrid } from "../components/Kpi";
import { NoComparison, Page, Section, deltaNote, type Loaded } from "../components/Page";
import type { CustomersData } from "../lib/api";
import { MAP_ASPECT, barChart, barHeight, cityMapChart, heatmapChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import { absoluteDelta, pointDelta, relativeDelta } from "../lib/delta";
import * as fmt from "../lib/format";
import { useTokens } from "../lib/theme";

/** Nombre de villes en bulles bleues sur la carte (les plus gros CA). */
const MAP_CITIES = 300;

export function Customers() {
  const { filters } = useFilters();
  const state = usePageData<CustomersData>("customers", filters);
  return (
    <Page title="Clients" intro="Qui achète, comment et quand. Montants en réais (R$), hors commandes annulées." state={state}>
      {(data) => <Content data={data} />}
    </Page>
  );
}

function Content({ data }: { data: Loaded<CustomersData> }) {
  const t = useTokens();
  const { kpis, previous_kpis: prev, cities } = data;
  const note = deltaNote(data);

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
  const payments = useMemo(
    () =>
      barChart(
        data.payments.map((p) => ({
          label: p.label,
          value: p.share,
          text: fmt.percent(p.share),
          tooltip: [
            `${fmt.percent(p.share)} des commandes`,
            `Commandes : ${fmt.number(p.orders)}`,
            `Panier moyen : ${fmt.currency(p.basket, 2)}`,
          ],
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
  const heatmap = useMemo(
    () => heatmapChart(data.heatmap.days, data.heatmap.hours.map((h) => `${h}h`), data.heatmap.values, "commandes", t),
    [data.heatmap, t],
  );
  const map = useMemo(
    () =>
      cityMapChart(
        cities
          .filter((c) => c.lat != null && c.lng != null)
          .map((c) => ({
            name: c.city,
            lat: c.lat!,
            lng: c.lng!,
            size: c.revenue,
            tooltip: [`CA : ${fmt.currency(c.revenue)}`, `Clients : ${fmt.number(c.customers)}`],
          })),
        MAP_CITIES,
        t,
      ),
    [cities, t],
  );
  const top = cities.slice(0, 15);

  return (
    <>
      <KpiGrid>
        <Kpi
          label="Clients"
          value={fmt.number(kpis.customers)}
          delta={relativeDelta(kpis.customers, prev?.customers)}
          deltaNote={note}
          help="Clients distincts ayant passé au moins une commande sur la période."
        />
        <Kpi
          label="Clients revenus"
          value={fmt.orDash(kpis.repeat_rate, (v) => fmt.percent(v))}
          delta={pointDelta(kpis.repeat_rate, prev?.repeat_rate)}
          deltaNote={note}
          help="Part des clients ayant passé au moins deux commandes sur la période."
        />
        <Kpi
          label="CA par client"
          value={fmt.orDash(kpis.revenue_per_customer, (v) => fmt.currency(v, 2))}
          delta={relativeDelta(kpis.revenue_per_customer, prev?.revenue_per_customer)}
          deltaNote={note}
          help="Chiffre d'affaires de la période / nombre de clients."
        />
        <Kpi
          label="Paiement par carte de crédit"
          value={fmt.orDash(kpis.credit_card_share, (v) => fmt.percent(v))}
          delta={pointDelta(kpis.credit_card_share, prev?.credit_card_share, "off")}
          deltaNote={note}
          help="Part des commandes payées principalement par carte de crédit."
        />
        <Kpi
          label="Mensualités moyennes (carte)"
          value={fmt.orDash(kpis.average_installments, (v) => fmt.number(v, 1))}
          delta={absoluteDelta(kpis.average_installments, prev?.average_installments, "", 1, "off")}
          deltaNote={note}
          help="Nombre moyen de mensualités des commandes payées par carte de crédit."
        />
        <Kpi
          label="Commandes par client"
          value={fmt.orDash(kpis.orders_per_customer, (v) => fmt.number(v, 2))}
          delta={absoluteDelta(kpis.orders_per_customer, prev?.orders_per_customer)}
          deltaNote={note}
        />
      </KpiGrid>
      <NoComparison data={data} />

      <div className="grid-2 section">
        <div>
          <h2>Clients selon leur nombre de commandes</h2>
          <Chart option={loyalty} height={barHeight(data.loyalty.length)} label="Part des clients selon leur nombre de commandes" />
          <p className="caption">
            Sur la période choisie. Presque tous les clients n'achètent qu'une fois : la croissance repose sur l'acquisition.
          </p>
        </div>
        <div>
          <h2>Moyens de paiement</h2>
          <Chart option={payments} height={barHeight(data.payments.length)} label="Part des commandes par moyen de paiement" />
          <p className="caption">
            Moyen de paiement principal (le plus gros montant) de chaque commande. Le boleto est un bordereau bancaire payé en espèces
            ou en ligne.
          </p>
        </div>
        <div>
          <h2>Panier moyen selon les mensualités</h2>
          <Chart option={installments} height={barHeight(data.installments.length)} label="Panier moyen selon le nombre de mensualités" />
          <p className="caption">Commandes payées par carte de crédit : plus le panier est gros, plus il est étalé.</p>
        </div>
        <div>
          <h2>Quand les clients achètent</h2>
          <Chart option={heatmap} height={300} label="Nombre de commandes par jour de la semaine et heure" />
          <p className="caption">Nombre de commandes par jour de la semaine et heure d'achat (heure de Brasília).</p>
        </div>
      </div>

      <Section title="Où sont les clients">
        <div className="grid-3-2">
          <div>
            <Chart option={map} aspect={MAP_ASPECT} label="Carte des villes clientes, bulles proportionnelles au chiffre d'affaires" />
            <p className="caption">
              En bleu, les {Math.min(MAP_CITIES, cities.length)} villes au plus gros CA (surface proportionnelle au CA) ; en gris, les{" "}
              {fmt.number(cities.length)} villes où vivent des clients.
            </p>
          </div>
          <div>
            <div className="table-card">
              <DataTable
                caption="Les 15 villes au plus gros chiffre d'affaires"
                rows={top}
                columns={[
                  { key: "city", label: "Ville" },
                  { key: "revenue", label: "CA", align: "right", format: (v) => fmt.currency(Number(v)) },
                  { key: "customers", label: "Clients", align: "right", format: (v) => fmt.number(Number(v)) },
                ]}
              />
            </div>
            <p className="caption">
              Les 15 premières villes font {fmt.percent(top.reduce((sum, c) => sum + c.share, 0), 0)} du CA.
            </p>
          </div>
        </div>
      </Section>
    </>
  );
}
