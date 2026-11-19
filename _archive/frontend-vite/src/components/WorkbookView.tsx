import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";

export function WorkbookView() {
  const [subject, setSubject] = useState("1009 New");
  const [finished, setFinished] = useState("");
  const [garage, setGarage] = useState("");
  const [apprec, setApprec] = useState("0");
  const [r, setR] = useState<Record<string, any> | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      api
        .regression({ subject, finished_sf: finished || undefined, garage_adjustment: garage || undefined, appreciation_pct: apprec || 0 })
        .then((x) => {
          setR(x);
          setErr("");
          if (!finished) setFinished(String(x.inputs.finished_sf));
          if (!garage) setGarage(String(x.inputs.garage_adjustment));
        })
        .catch((e) => setErr(e.message));
    }, 200);
    return () => clearTimeout(t);
  }, [subject, finished, garage, apprec]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!r) return <main className="page"><p>{err || "Loading…"}</p></main>;
  const reg = r.regression;
  return (
    <main className="page workbook">
      <h1>Workbook regression check</h1>
      <p className="lead">
        Reproduces the client's “{r.workbook}” pricing method from its original inputs, then shows how the estimate
        changes under the app's own rules. Valuation date {r.valuation_date}.
      </p>
      <p className="callout">{r.address_verification.result}</p>

      <fieldset className="form-grid inline">
        <legend>Inputs (editable assumptions for this workbook example only)</legend>
        <label>
          Subject
          <select value={subject} onChange={(e) => { setSubject(e.target.value); setFinished(""); setGarage(""); }}>
            {Object.keys(r.subjects).map((s: string) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label>Finished sq ft<input inputMode="numeric" value={finished} onChange={(e) => setFinished(e.target.value)} /></label>
        <label>Garage/ADU adjustment ($)<input inputMode="numeric" value={garage} onChange={(e) => setGarage(e.target.value)} /></label>
        <label>Appreciation %<input type="number" step="0.1" value={apprec} onChange={(e) => setApprec(e.target.value)} /></label>
      </fieldset>
      <p className="small muted">{r.inputs.garage_adjustment_note}</p>

      {reg.expected !== null && (
        <p className={reg.passed ? "pass" : "warn"} role="status">
          {reg.passed ? "✔ Regression passed" : "✖ Regression failed"}: workbook cell total {money(reg.expected, true)}, app{" "}
          {money(reg.actual, true)}
        </p>
      )}
      {reg.expected === null && <p className="small muted">Inputs differ from the workbook's, so there is no workbook total to compare against.</p>}

      <div className="variants">
        {r.variants.map((v: any) => (
          <section key={v.variant} className="card variant">
            <h2>{v.variant}. {v.title}</h2>
            <p className="est-value">{money(v.estimate, true)}</p>
            <p className="small">{v.description}</p>
            {v.lines && <ol className="calc small">{v.lines.map((l: string) => <li key={l}>{l}</li>)}</ol>}
            {v.comps && (
              <table className="mini">
                <caption className="sr-only">Comps used</caption>
                <thead><tr><th scope="col">Comp</th><th scope="col" className="num">Sold</th><th scope="col" className="num">Area</th><th scope="col" className="num">$/sf</th></tr></thead>
                <tbody>
                  {v.comps.map((c: any) => (
                    <tr key={c.address ?? c.label}>
                      <td>{c.address ?? c.label}</td>
                      <td className="num">{money(c.sold_price ?? c.price)}</td>
                      <td className="num">{(c.area ?? 0).toLocaleString()}</td>
                      <td className="num">${(c.ppsf ?? 0).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {v.excluded && (
              <details>
                <summary className="small">Excluded by the app's rules ({v.excluded.length})</summary>
                <ul className="small">{v.excluded.map((x: any) => <li key={x.address}>{x.address}: {x.reason}</li>)}</ul>
              </details>
            )}
          </section>
        ))}
      </div>
      <p className="callout">{r.live_comparison.reason}</p>

      <h2>Issues found in the workbook</h2>
      <div className="table-wrap" role="region" aria-labelledby="flags-cap" tabIndex={0}>
        <table className="comps flags">
          <caption id="flags-cap">Formula and data issues. “Decision” marks items that need the client's choice.</caption>
          <thead><tr><th scope="col">Cells</th><th scope="col">Severity</th><th scope="col">Issue</th><th scope="col">Detail</th><th scope="col">Decision</th></tr></thead>
          <tbody>
            {r.flags.map((f: any) => (
              <tr key={f.cells + f.issue}>
                <td><code>{f.cells}</code></td>
                <td><span className={`sev sev-${f.severity}`}>{f.severity}</span></td>
                <td>{f.issue}</td>
                <td className="small">{f.detail ?? ""}</td>
                <td>{f.decision ? "Client" : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
