// Petite icône « i » qui affiche une explication au survol ou au clavier.
export function InfoTip({ text }: { text: string }) {
  return (
    <button type="button" className="info" aria-label={text}>
      i<span className="tip" aria-hidden="true">{text}</span>
    </button>
  );
}
