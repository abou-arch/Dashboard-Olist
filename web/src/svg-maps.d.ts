// Types du paquet @svg-maps/brazil (carte des États, licence CC BY 4.0).
declare module "@svg-maps/brazil" {
  interface Location {
    id: string;
    name: string;
    path: string;
  }
  const map: { label: string; viewBox: string; locations: Location[] };
  export default map;
}
