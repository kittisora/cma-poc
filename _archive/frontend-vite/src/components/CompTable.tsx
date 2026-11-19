import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { money, num } from "../format";
import type { Comp } from "../types";

type SortKey =
  | "rank" | "score" | "address" | "date" | "price" | "ag" | "ppsf" | "tf" | "ppsf_tf" | "beds" | "baths"
  | "year" | "lot" | "dist";

interface Col {
  key: SortKey;
  label: string;
  type: "number" | "text";
  value: (c: Comp) => number | string | null;
}

const COLS: Col[] = [
  { key: "rank", label: "Rank", type: "number", value: (c) => c.rank },
  { key: "score", label: "Score", type: "number", value: (c) => c.score },
  { key: "address", label: "Address", type: "text", value: (c) => c.address },
  { key: "date", label: "Sold", type: "text", value: (c) => c.sale.sale_date },
  { key: "price", label: "Price", type: "number", value: (c) => c.sale.price },
  { key: "ag", label: "Above-grade sf", type: "number", value: (c) => c.property.above_grade_sf },
  { key: "ppsf", label: "$/AG sf", type: "number", value: (c) => c.ppsf_above_grade },
  { key: "tf", label: "Total fin. sf", type: "number", value: (c) => c.total_finished_sf },
  { key: "ppsf_tf", label: "$/TF sf", type: "number", value: (c) => c.ppsf_total_finished },
  { key: "beds", label: "Beds", type: "number", value: (c) => c.property.beds },
  { key: "baths", label: "Baths", type: "number", value: (c) => (c.property.full_baths ?? 0) + 0.5 * (c.property.half_baths ?? 0) },
  { key: "year", label: "Built", type: "number", value: (c) => c.property.year_built },
  { key: "lot", label: "Lot sf", type: "number", value: (c) => c.property.lot_sf },
  { key: "dist", label: "Miles", type: "number", value: (c) => c.distance_miles },
];

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

interface Props {
  comps: Comp[];
  highlighted: number | null;
  onHighlight: (id: number | null) => void;
  onToggle: (id: number, include: boolean) => void;
  onTotalFinished: (pin: string, value: number | null) => void;
  busy: boolean;
  /** Current selection, updated immediately on click (the server confirms it on the next analysis). */
  selectedIds: number[];
}

export function CompTable({ comps, highlighted, onHighlight, onToggle, onTotalFinished, busy, selectedIds }: Props) {
  const [sort, setSort] = useState<{ key: SortKey; dir: "ascending" | "descending" }>({ key: "rank", dir: "ascending" });
  const [open, setOpen] = useState<number | null>(null);
  const [announce, setAnnounce] = useState("");
  const [showAll, setShowAll] = useState(false);
  const LIMIT = 15;
  const rowRefs = useRef(new Map<number, HTMLTableRowElement>());

  const rows = useMemo(() => {
    const col = COLS.find((c) => c.key === sort.key)!;
    const f = sort.dir === "ascending" ? 1 : -1;
    return [...comps].sort((a, b) => {
      const va = col.value(a), vb = col.value(b);
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      return f * (col.type === "number" ? (va as number) - (vb as number) : collator.compare(String(va), String(vb)));
    });
  }, [comps, sort]);

  const visible = showAll
    ? rows
    : rows.filter((c) => c.rank <= LIMIT || selectedIds.includes(c.sale_id) || c.sale_id === highlighted);

  useEffect(() => {
    if (highlighted === null) return;
    const el = rowRefs.current.get(highlighted);
    el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [highlighted]);

  const clickSort = (col: Col) => {
    const dir = sort.key === col.key && sort.dir === "ascending" ? "descending" : "ascending";
    setSort({ key: col.key, dir });
    setAnnounce(`Sorted by ${col.label}, ${dir}, ${comps.length} rows`);
  };

  const selectedOrder = new Map(comps.filter((c) => c.selected).sort((a, b) => a.rank - b.rank).map((c, i) => [c.sale_id, i + 1]));

  return (
    <div className="table-wrap" role="region" aria-labelledby="comp-caption" tabIndex={0}>
      <table className="comps" aria-busy={busy}>
        <caption id="comp-caption">
          Eligible sales, ranked by similarity to the subject (ranking never uses price). Checked rows are used in
          the valuation.
        </caption>
        <thead>
          <tr>
            <th scope="col">Use</th>
            {COLS.map((c) => (
              <th key={c.key} scope="col" aria-sort={sort.key === c.key ? sort.dir : undefined} className={c.type === "number" ? "num" : ""}>
                <button type="button" onClick={() => clickSort(c)}>
                  {c.label}
                  <svg aria-hidden="true" viewBox="0 0 10 10" className="sort-icon">
                    <path d="M5 1 8 4H2zM5 9 2 6h6z" fill="currentColor" />
                  </svg>
                </button>
              </th>
            ))}
            <th scope="col">Why</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((c) => (
            <Fragment key={c.sale_id}>
              <tr
                ref={(el) => {
                  if (el) rowRefs.current.set(c.sale_id, el);
                  else rowRefs.current.delete(c.sale_id);
                }}
                className={`${c.selected ? "is-selected" : ""} ${highlighted === c.sale_id ? "is-highlighted" : ""}`}
                onClick={() => onHighlight(c.sale_id)}
                aria-current={highlighted === c.sale_id ? "true" : undefined}
              >
                <td>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(c.sale_id)}
                    aria-label={`Use ${c.address} in the valuation`}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => onToggle(c.sale_id, e.target.checked)}
                  />
                  {c.selected && <span className="comp-no" aria-hidden="true">{selectedOrder.get(c.sale_id)}</span>}
                </td>
                <td className="num">{c.rank}</td>
                <td className="num">
                  <span className="score" style={{ ["--s" as string]: `${c.score}%` }}>{c.score.toFixed(0)}</span>
                </td>
                <td className="addr">{c.address}</td>
                <td className="nowrap">{c.sale.sale_date}</td>
                <td className="num">{money(c.sale.price)}</td>
                <td className="num">{num(c.property.above_grade_sf)}</td>
                <td className="num">{c.ppsf_above_grade ? `$${c.ppsf_above_grade.toFixed(0)}` : "—"}</td>
                <td className="num" onClick={(e) => e.stopPropagation()}>
                  <TfInput comp={c} onCommit={onTotalFinished} />
                </td>
                <td className="num">{c.ppsf_total_finished ? `$${c.ppsf_total_finished.toFixed(0)}` : "—"}</td>
                <td className="num">{c.property.beds ?? "—"}</td>
                <td className="num">{c.property.baths_label ?? "—"}</td>
                <td className="num">{c.property.year_built ?? "—"}</td>
                <td className="num">{num(c.property.lot_sf)}</td>
                <td className="num">{c.distance_miles?.toFixed(2) ?? "—"}</td>
                <td>
                  <button
                    type="button"
                    className="link"
                    aria-expanded={open === c.sale_id}
                    aria-controls={`why-${c.sale_id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setOpen(open === c.sale_id ? null : c.sale_id);
                    }}
                  >
                    {open === c.sale_id ? "Hide" : "Details"}
                  </button>
                </td>
              </tr>
              <tr className="reason-row">
                <td />
                <td colSpan={COLS.length + 1} className="reason">
                  {c.reason}
                  {c.warnings.map((w) => (
                    <span key={w} className="warn-inline"> ⚠ {w}</span>
                  ))}
                </td>
              </tr>
              {open === c.sale_id && (
                <tr id={`why-${c.sale_id}`} className="detail-row">
                  <td />
                  <td colSpan={COLS.length + 1}>
                    <FactorDetail c={c} />
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
      {rows.length > visible.length || showAll ? (
        <div className="table-foot">
          <button type="button" className="secondary small" onClick={() => setShowAll(!showAll)}>
            {showAll ? `Show top ${LIMIT} and selected` : `Show all ${rows.length} eligible sales`}
          </button>
        </div>
      ) : null}
      <p role="status" className="sr-only">{announce}</p>
    </div>
  );
}

function TfInput({ comp, onCommit }: { comp: Comp; onCommit: (pin: string, v: number | null) => void }) {
  const [v, setV] = useState(comp.total_finished_sf?.toString() ?? "");
  useEffect(() => setV(comp.total_finished_sf?.toString() ?? ""), [comp.total_finished_sf]);
  const commit = () => {
    const n = v.trim() === "" ? null : Number(v.replace(/,/g, ""));
    if (n !== null && (!Number.isFinite(n) || n < 100)) return;
    if (n !== comp.total_finished_sf) onCommit(comp.pin, n);
  };
  return (
    <input
      className="tf-input"
      inputMode="numeric"
      value={v}
      placeholder="enter"
      title={comp.total_finished_source ? `Source: ${comp.total_finished_source}` : "Total finished sq ft from the listing (agent input)"}
      aria-label={`Total finished square feet for ${comp.address}`}
      onChange={(e) => setV(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
    />
  );
}

function FactorDetail({ c }: { c: Comp }) {
  return (
    <div className="factors">
      <table className="factor-table">
        <caption className="sr-only">Similarity factors for {c.address}</caption>
        <thead>
          <tr>
            <th scope="col">Factor</th>
            <th scope="col" className="num">Weight</th>
            <th scope="col">Match</th>
            <th scope="col">Comparison</th>
          </tr>
        </thead>
        <tbody>
          {c.factors.map((f) => (
            <tr key={f.key}>
              <td>{f.label}</td>
              <td className="num">{f.weight}</td>
              <td>
                {f.score === null ? (
                  <span className="muted">not compared</span>
                ) : (
                  <span className="bar" aria-label={`${Math.round(f.score * 100)}% match`}>
                    <span style={{ width: `${f.score * 100}%` }} />
                  </span>
                )}
              </td>
              <td>{f.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <dl className="record">
        <dt>County validity</dt>
        <dd>{c.sale.validity}</dd>
        <dt>Record</dt>
        <dd>
          {c.source.record_id}
          {c.source.url && (
            <>
              {" · "}
              <a href={c.source.url} target="_blank" rel="noreferrer">dataset</a>
            </>
          )}
        </dd>
        <dt>Retrieved</dt>
        <dd>{c.source.retrieved_at?.slice(0, 19).replace("T", " ")} UTC</dd>
        <dt>Assessor condition / grade</dt>
        <dd>
          {c.property.condition ?? "—"} / {c.property.grade ?? "—"} · {c.property.style ?? "—"}
        </dd>
      </dl>
    </div>
  );
}
