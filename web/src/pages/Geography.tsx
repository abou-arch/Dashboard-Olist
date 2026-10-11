import { Building2, Landmark, MapPin } from "lucide-react";
import { useMemo } from "react";

import { BrazilMap, STATE_NAMES } from "../components/BrazilMap";
import { Chart } from "../components/Chart";
import { DataTable } from "../components/DataTable";
import { Kpi } from "../components/Kpi";
import { Card, Grid, Page, type Loaded } from "../components/Page";
import type { GeographyData } from "../lib/api";
import { MAP_ASPECT, barChart, barHeight, cityMapChart } from "../lib/charts";
import { useFilters, usePageData } from "../lib/data";
import * as fmt from "../lib/format";
import { useTokens } from "../lib/theme";

/** Nombre de villes en bulles sur la carte (les plus gros CA). */
const MAP_CITIES = 300;

export function Geography() {
  const { filters } = useFilters();
  const state = usePageData<GeographyData>("geography", filters);
  return (
    <Page title="Géographie" intro="Où sont les clients et d'où viennent les ventes" state={state}>
      {(data) => <Content data={data} />}
    </Page>
  );
}

const optional = (format: (v: number) => string) => (v: unknown) => (v == null ? "–" : format(Number(v)));

function Content({ data }: { data: Loaded<GeographyData> }) {
  const t = useTokens();
  const { by_state: states, cities } = data;
  const top = cities.slice(0, 15);
  const first = states[0];

  const values = useMemo(() => Object.fromEntries(states.map((s) => [s.customer_state, s.revenue])), [states]);
  const cityMap = useMemo(
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
  const sellerStates = useMemo(
    () =>
      barChart(
        data.by_seller_state.map((s) => ({
          label: s.seller_state,
          value: s.revenue,
          text: fmt.compactCurrency(s.revenue),
          tooltip: [`CA : ${fmt.currency(s.revenue)}`, `Part du CA : ${fmt.percent(s.share)}`, `Vendeurs : ${fmt.number(s.sellers)}`],
        })),
        t,
      ),
    [data.by_seller_state, t],
  );

  return (
    <>
      <Grid cols="3">
        <Kpi label="Villes clientes" icon={MapPin} value={fmt.number(cities.length)}
          note={`Dans ${states.length} États`} help="Villes où vit au moins un client ayant commandé sur la période." />
        <Kpi label="Premier État" icon={Landmark}
          value={first ? <>{first.customer_state} <small>{fmt.percent(first.share, 0)} du CA</small></> : "–"}
          note={first ? STATE_NAMES[first.customer_state] : null} />
        <Kpi label="15 premières villes" icon={Building2}
          value={fmt.percent(top.reduce((sum, c) => sum + c.share, 0), 0)} note="du chiffre d'affaires" />
      </Grid>

      <Grid cols="2">
        <Card title="Chiffre d'affaires par État" subtitle="Plus la couleur est claire, plus l'État pèse">
          <BrazilMap
            values={values}
            t={t}
            label="Carte du chiffre d'affaires par État"
            tooltip={(state) => {
              const row = states.find((s) => s.customer_state === state);
              return row ? [`CA : ${fmt.currency(row.revenue)}`, `Part : ${fmt.percent(row.share)}`] : ["Aucune vente"];
            }}
          />
        </Card>
        <Card title="Villes clientes" subtitle={`En doré, les ${MAP_CITIES} villes au plus gros CA ; en gris, toutes les autres`}>
          <Chart option={cityMap} aspect={MAP_ASPECT} label="Carte des villes clientes, bulles proportionnelles au chiffre d'affaires" />
        </Card>
      </Grid>

      <Card className="spaced" title="Indicateurs par État du client">
        <div className="table-wrap" style={{ maxHeight: 520 }}>
          <DataTable
            caption="Ventes et livraisons par État du client"
            rows={states.map((s) => ({ ...s, name: STATE_NAMES[s.customer_state] ?? s.customer_state }))}
            columns={[
              { key: "name", label: "État" },
              { key: "revenue", label: "CA", align: "right", format: (v) => fmt.currency(Number(v)) },
              { key: "share", label: "Part du CA", align: "right", format: (v) => fmt.percent(Number(v)) },
              { key: "orders", label: "Commandes", align: "right", format: (v) => fmt.number(Number(v)) },
              { key: "customers", label: "Clients", align: "right", format: (v) => fmt.number(Number(v)) },
              { key: "delivery_days", label: "Délai moyen", align: "right", format: optional((v) => fmt.days(v)) },
              { key: "late_rate", label: "En retard", align: "right", format: optional((v) => fmt.percent(v)) },
              { key: "freight_value", label: "Port moyen", align: "right", format: optional((v) => fmt.currency(v, 2)) },
            ]}
          />
        </div>
      </Card>

      <Grid cols="2">
        <Card title="Les 15 premières villes" subtitle="Par chiffre d'affaires">
          <DataTable
            caption="Les 15 villes au plus gros chiffre d'affaires"
            rows={top}
            columns={[
              { key: "city", label: "Ville" },
              { key: "revenue", label: "CA", align: "right", format: (v) => fmt.currency(Number(v)) },
              { key: "customers", label: "Clients", align: "right", format: (v) => fmt.number(Number(v)) },
            ]}
          />
        </Card>
        <Card title="D'où viennent les ventes" subtitle="Chiffre d'affaires par État du vendeur">
          <Chart option={sellerStates} height={barHeight(data.by_seller_state.length)} label="Chiffre d'affaires par État du vendeur" />
          <p className="caption">Le filtre « États » porte sur le client, pas sur le vendeur.</p>
        </Card>
      </Grid>
    </>
  );
}
