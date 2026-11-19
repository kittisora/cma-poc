import { useEffect, useState } from "react";
import { money, pct, signedMoney } from "../format";
import type { Adjustment, Analysis, BasisResult } from "../types";

export function EstimateSummary({ a }: { a: Analysis }) {
  const v = a.valuation;
  const basis = v.primary_basis ? v.bases[v.primary_basis] : null;
  return (
    <section className="estimate" aria-labelledby="est-h">
      <h2 id="est-h" className="eyebrow">Estimated value · {a.valuation_date}</h2>
      {v.estimate !== null ? (
        <>
          <p className="est-value">{money(v.estimate)}</p>
          <p className="est-range">
            Range {money(v.range_low)} – {money(v.range_high)}
          </p>
          <p className="est-basis">
            {basis?.label} · {v.point_statistic === "mean" ? "average" : "median"} of {basis?.n} comps
          </p>
        </>
      ) : (
        <p className="est-none">Not enough data for an estimate yet.</p>
      )}
      {a.change_since_last_sale && (
        <p className="est-change">
          <strong>{a.change_since_last_sale.label}:</strong> {signedMoney(a.change_since_last_sale.amount)} (
          {pct(a.change_since_last_sale.pct)}) vs {money(a.change_since_last_sale.last_sale_price)} on{" "}
          {a.change_since_last_sale.last_sale_date}
        </p>
      )}
      {!a.change_since_last_sale && a.latest_transfer && (
        <p className="est-change muted">
          No arm's-length sale of the subject on record before the valuation date (latest transfer{" "}
          {a.latest_transfer.sale_date}: {a.latest_transfer.validity}).
        </p>
      )}
    </section>
  );
}

interface PricingProps {
  a: Analysis;
  adjustments: Adjustment[];
  setAdjustments: (a: Adjustment[]) => void;
  appreciation: number;
  setAppreciation: (n: number) => void;
  pointStat: "mean" | "median";
  setPointStat: (s: "mean" | "median") => void;
  primaryBasis: "auto" | "above_grade" | "total_finished";
  setPrimaryBasis: (b: "auto" | "above_grade" | "total_finished") => void;
  onSubjectTotalFinished: (v: number | null) => void;
}

export function PricingPanel(p: PricingProps) {
  const v = p.a.valuation;
  const [tf, setTf] = useState(p.a.subject.total_finished_sf?.toString() ?? "");
  useEffect(() => setTf(p.a.subject.total_finished_sf?.toString() ?? ""), [p.a.subject.total_finished_sf, p.a.subject.pin]);

  const commitTf = () => {
    const n = tf.trim() === "" ? null : Number(tf.replace(/,/g, ""));
    if (n !== null && (!Number.isFinite(n) || n < 100)) return;
    if (n !== p.a.subject.total_finished_sf) p.onSubjectTotalFinished(n);
  };

  const updateAdj = (i: number, patch: Partial<Adjustment>) =>
    p.setAdjustments(p.adjustments.map((a, j) => (j === i ? { ...a, ...patch } : a)));

  return (
    <div className="panel-body">
      <fieldset className="form-grid">
        <legend>Subject area</legend>
        <label>
          Above-grade sq ft <small>(county assessor)</small>
          <input value={p.a.subject.above_grade_sf ?? "not recorded"} readOnly />
        </label>
        <label>
          Total finished sq ft <small>(listing / agent input)</small>
          <input
            inputMode="numeric"
            value={tf}
            placeholder="not in county records"
            onChange={(e) => setTf(e.target.value)}
            onBlur={commitTf}
            onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
          />
        </label>
      </fieldset>

      <fieldset className="form-grid">
        <legend>Method</legend>
        <label>
          Headline method
          <select value={p.primaryBasis} onChange={(e) => p.setPrimaryBasis(e.target.value as PricingProps["primaryBasis"])}>
            <option value="auto">Automatic (total finished when complete)</option>
            <option value="above_grade">Above-grade $/sf</option>
            <option value="total_finished">Total finished $/sf</option>
          </select>
        </label>
        <label>
          Point estimate
          <select value={p.pointStat} onChange={(e) => p.setPointStat(e.target.value as "mean" | "median")}>
            <option value="mean">Average $/sf (workbook)</option>
            <option value="median">Median $/sf</option>
          </select>
        </label>
        <label>
          Appreciation %
          <input
            type="number"
            step="0.1"
            value={p.appreciation}
            onChange={(e) => p.setAppreciation(Number(e.target.value) || 0)}
          />
        </label>
      </fieldset>

      <fieldset>
        <legend>Adjustments (agent assumptions)</legend>
        {p.adjustments.length === 0 && <p className="muted small">None. Add one for features the comps do not share, such as a detached garage or ADU.</p>}
        {p.adjustments.map((a, i) => (
          <div className="adj-row" key={i}>
            <input aria-label="Adjustment label" value={a.label} onChange={(e) => updateAdj(i, { label: e.target.value })} />
            <input
              aria-label="Adjustment amount in dollars"
              type="number"
              step="1000"
              value={a.amount}
              onChange={(e) => updateAdj(i, { amount: Number(e.target.value) || 0 })}
            />
            <input aria-label="Adjustment note" placeholder="basis / note" value={a.note ?? ""} onChange={(e) => updateAdj(i, { note: e.target.value })} />
            <button type="button" className="icon-btn" aria-label={`Remove ${a.label}`} onClick={() => p.setAdjustments(p.adjustments.filter((_, j) => j !== i))}>
              ×
            </button>
          </div>
        ))}
        <button type="button" className="secondary" onClick={() => p.setAdjustments([...p.adjustments, { label: "Garage/ADU", amount: 0, note: "" }])}>
          Add adjustment
        </button>
      </fieldset>

      <BasisCard b={v.bases.above_grade} primary={v.primary_basis === "above_grade"} />
      <BasisCard b={v.bases.total_finished} primary={v.primary_basis === "total_finished"} />
      {v.warnings.map((w) => (
        <p className="warn" key={w}>{w}</p>
      ))}
    </div>
  );
}

function BasisCard({ b, primary }: { b: BasisResult; primary: boolean }) {
  return (
    <section className={`basis ${primary ? "basis-primary" : ""}`} aria-label={b.label}>
      <h3>
        {b.label} {primary && <span className="tag">headline</span>}
      </h3>
      {!b.available ? (
        <p className="muted">{b.reason_unavailable}</p>
      ) : (
        <>
          <table className="mini">
            <caption className="sr-only">Indicated values</caption>
            <thead>
              <tr>
                <th scope="col">Statistic</th>
                <th scope="col" className="num">$/sf</th>
                <th scope="col" className="num">× {b.subject_area?.toLocaleString()} sf</th>
              </tr>
            </thead>
            <tbody>
              {(["mean", "median", "high", "low"] as const).map((k) => (
                <tr key={k}>
                  <th scope="row">{k === "mean" ? "Average" : k[0].toUpperCase() + k.slice(1)}</th>
                  <td className="num">${b.ppsf[k]?.toFixed(2)}</td>
                  <td className="num">{money(b.indicated[k])}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ol className="calc">
            {b.lines.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ol>
          {b.warnings.map((w) => (
            <p className="warn small" key={w}>{w}</p>
          ))}
        </>
      )}
    </section>
  );
}
