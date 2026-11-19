import { money, num } from "../format";
import type { Analysis, Hint } from "../types";

export function SubjectCard({ a }: { a: Analysis }) {
  const s = a.subject;
  const facts: [string, string][] = [
    ["Type", a.subject_label],
    ["Style", s.style ?? "—"],
    ["Built", s.year_built ? `${s.year_built}${s.year_remodeled ? ` (remodel ${s.year_remodeled})` : ""}` : "—"],
    ["Beds / baths", `${s.beds ?? "—"} / ${s.baths_label ?? "—"}`],
    ["Above-grade", s.above_grade_sf ? `${num(s.above_grade_sf)} sf` : "not recorded"],
    ["Total finished", s.total_finished_sf ? `${num(s.total_finished_sf)} sf (${s.total_finished_source})` : "not recorded"],
    ["Basement", `${s.basement ?? "—"}${s.rec_room_sf ? ` · rec room ${num(s.rec_room_sf)} sf` : ""}`],
    ["Lot", s.lot_sf ? `${num(s.lot_sf)} sf` : "—"],
    ["Condition / grade", `${s.condition ?? "—"} / ${s.grade ?? "—"}`],
    ["Garage", s.garage_evidence ?? "not recorded"],
    [`Assessed ${s.assessed_tax_year ?? ""}`, money(s.assessed_total)],
  ];
  return (
    <section className="subject card" aria-labelledby="subj-h">
      <div className="subject-head">
        <h2 id="subj-h">
          {s.address}
          <span className="muted"> · {s.city} VA {s.zip}</span>
        </h2>
        <span className="pin-id" title="Fairfax County parcel ID (PARID)">PARID {s.pin}</span>
      </div>
      <dl className="facts">
        {facts.map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      {s.notes.map((n) => (
        <p className="note small" key={n}>{n}</p>
      ))}
      <details className="history">
        <summary>Recorded transfers of this property ({a.sale_history.length})</summary>
        <table className="mini">
          <caption className="sr-only">Sale history</caption>
          <thead>
            <tr><th scope="col">Date</th><th scope="col" className="num">Price</th><th scope="col">County validity</th><th scope="col">Deed</th></tr>
          </thead>
          <tbody>
            {a.sale_history.map((h) => (
              <tr key={h.sale_id}>
                <td>{h.sale_date}</td>
                <td className="num">{money(h.price)}</td>
                <td>{h.validity ?? "—"}{h.multi_parcel ? " (multi-parcel)" : ""}{!h.in_latest_source ? " (kept from history)" : ""}</td>
                <td>{h.deed_ref}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}

export function SearchExplanation({ a, onApplyHint }: { a: Analysis; onApplyHint: (h: Hint) => void }) {
  const s = a.search;
  const removed = s.funnel.filter((f) => f.removed > 0);
  return (
    <section className={`funnel ${s.limited ? "funnel-limited" : ""}`} aria-labelledby="funnel-h">
      <h3 id="funnel-h">
        {s.eligible_count} eligible of {s.pool_count} recorded transfers within {a.criteria.max_distance_miles} mi, {s.window_start} to{" "}
        {a.valuation_date}
      </h3>
      {s.later_sales_excluded > 0 && (
        <p className="small">{s.later_sales_excluded} sale(s) recorded after the valuation date were excluded.</p>
      )}
      <details>
        <summary>What each rule removed</summary>
        <ul className="small">
          {removed.length === 0 && <li>No transfers were removed by the rules.</li>}
          {removed.map((f) => (
            <li key={f.key}>
              <strong>{f.removed}</strong> — {f.label}
              {f.detail && <span className="muted"> ({f.detail})</span>}
            </li>
          ))}
        </ul>
      </details>
      {s.limit_explanation && <p className={s.insufficient ? "warn" : "callout"}>{s.limit_explanation}</p>}
      {s.hints.length > 0 && (
        <div className="hints">
          <span className="small">Widen the search:</span>
          {s.hints.map((h) => (
            <button type="button" className="secondary small" key={h.change} onClick={() => onApplyHint(h)}>
              {h.change} (+{h.added})
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
