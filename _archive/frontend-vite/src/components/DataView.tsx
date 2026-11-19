import type { Meta } from "../types";

const STATUS_LABEL: Record<string, string> = {
  county: "County record",
  partial: "Partly in county data",
  agent_or_mls: "Agent input / MLS",
  calculated: "Calculated",
  calculated_with_input: "Calculated (needs agent input)",
  client_decision: "Client decision",
};

export function DataView({ meta }: { meta: Meta }) {
  const lr = meta.data.last_refresh;
  const counts = (lr?.counts ?? {}) as Record<string, any>;
  return (
    <main className="page">
      <h1>Data & sources</h1>
      <section className="card">
        <h2>Source</h2>
        <p>{meta.provider.label}</p>
        <p className="small">{meta.provider.attribution}</p>
        <p className="small">
          This is <strong>public-record data, not MLS data</strong>. An approved MLS feed or another licensed provider can
          be added as a separate provider without changing the comp or pricing logic.
        </p>
        <ul className="small">
          {meta.provider.datasets.map((d) => (
            <li key={d.key}><a href={d.url} target="_blank" rel="noreferrer">{d.title}</a></li>
          ))}
        </ul>
      </section>
      <section className="card">
        <h2>Last refresh</h2>
        {lr ? (
          <dl className="facts">
            <div><dt>Finished</dt><dd>{lr.finished_at?.replace("T", " ").slice(0, 19)} UTC</dd></div>
            <div><dt>ZIP codes</dt><dd>{lr.zips}</dd></div>
            <div><dt>Parcels</dt><dd>{meta.data.parcels.toLocaleString()}</dd></div>
            <div><dt>Sales stored</dt><dd>{meta.data.sales.toLocaleString()}</dd></div>
            <div><dt>Latest sale</dt><dd>{meta.data.latest_sale_date}</dd></div>
            <div><dt>Duplicate rows collapsed</dt><dd>{counts.sales?.duplicate_rows_collapsed ?? "—"}</dd></div>
            <div><dt>Multi-parcel sales flagged</dt><dd>{counts.sales?.multi_parcel_sales ?? "—"}</dd></div>
            <div><dt>Refresh time</dt><dd>{counts.timings_seconds?.total ? `${counts.timings_seconds.total}s` : "—"}</dd></div>
          </dl>
        ) : (
          <p className="warn">No data loaded. Run <code>python -m app.ingest.refresh</code> in the backend.</p>
        )}
      </section>
      <section className="card">
        <h2>Terms of use</h2>
        <p className="small">{meta.provider.terms_summary}</p>
        <p className="small"><a href={meta.provider.terms_url} target="_blank" rel="noreferrer">{meta.provider.terms_url}</a></p>
      </section>
      <section>
        <h2>Workbook fields and where they come from</h2>
        <div className="table-wrap" role="region" aria-labelledby="fm-cap" tabIndex={0}>
          <table className="comps">
            <caption id="fm-cap">Field availability for the client's CMA workbook</caption>
            <thead><tr><th scope="col">Workbook field</th><th scope="col">Availability</th><th scope="col">Source</th><th scope="col">Note</th></tr></thead>
            <tbody>
              {meta.field_map.map((f) => (
                <tr key={f.workbook}>
                  <td>{f.workbook}</td>
                  <td><span className={`chip chip-${f.status}`}>{STATUS_LABEL[f.status] ?? f.status}</span></td>
                  <td className="small">{f.source}</td>
                  <td className="small">{f.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
