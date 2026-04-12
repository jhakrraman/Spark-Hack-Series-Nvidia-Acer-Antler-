// Renders the operator badge in the top-right of the app shell.
export default function AuthButton() {
  return (
    <div className="flex items-center gap-3">
      <span className="flex items-center gap-2 border border-deck-line px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.14em] text-deck-dim">
        <span className="deck-dot text-deck-ok" />
        OPERATOR · LOCAL
      </span>
      <span className="deck-num text-[11px] font-bold text-deck-faint">K-482</span>
    </div>
  );
}
