import { useEffect, useState } from "react";
import { api, downloadReport } from "../api";
import type { Analysis, Branding, CMARequest, ReportModel } from "../types";

interface Props {
  a: Analysis;
  req: CMARequest;
  aiEnabled: boolean;
  narrative: string;
  setNarrative: (s: string) => void;
}

const EMPTY: Branding = {
  company: "", agent_name: "", agent_title: "", phone: "", email: "", website: "", license_line: "",
  primary_color: "#1F4E79", logo_data_url: null, footer_note: "",
};

export function ReportPanel({ a, req, aiEnabled, narrative, setNarrative }: Props) {
  const [branding, setBranding] = useState<Branding>(EMPTY);
  const [preparedFor, setPreparedFor] = useState("");
  const [includeSources, setIncludeSources] = useState(true);
  const [preview, setPreview] = useState<ReportModel | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [narrSource, setNarrSource] = useState<string>("");

  useEffect(() => {
    api.getBranding().then(setBranding).catch(() => undefined);
  }, []);

  const body = () => ({
    cma: req, branding, narrative, prepared_for: preparedFor, include_sources: includeSources,
    expected_estimate: a.valuation.estimate, narrative_source: narrSource || "agent",
  });

  const draft = async () => {
    setBusy(true);
    setStatus(aiEnabled ? "Asking the AI assistant to draft the narrative…" : "Drafting from the computed results…");
    try {
      const r = await api.narrative(req);
      setNarrative(r.narrative);
      setNarrSource(r.generated_by);
      setStatus(r.note ?? (r.generated_by === "ai" ? "AI draft ready — review and edit before exporting." : "Template draft ready — review and edit before exporting."));
    } catch (e) {
      setStatus(`Could not draft the narrative: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const doPreview = async () => {
    setBusy(true);
    try {
      setPreview(await api.preview(body()));
      setStatus("Preview updated.");
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const doExport = async (fmt: "pdf" | "docx") => {
    setBusy(true);
    setStatus(`Building ${fmt.toUpperCase()}…`);
    try {
      const name = await downloadReport(fmt, body());
      setStatus(`Downloaded ${name}`);
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const saveBranding = async () => {
    try {
      setBranding(await api.putBranding(branding));
      setStatus("Branding saved for the team.");
    } catch (e) {
      setStatus((e as Error).message);
    }
  };

  const onLogo = (file: File | undefined) => {
    if (!file) return;
    if (file.size > 1_000_000) {
      setStatus("Logo must be under 1 MB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setBranding({ ...branding, logo_data_url: String(reader.result) });
    reader.readAsDataURL(file);
  };

  const b = (k: keyof Branding) => ({
    value: (branding[k] as string) ?? "",
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setBranding({ ...branding, [k]: e.target.value }),
  });

  return (
    <div className="panel-body">
      <fieldset>
        <legend>Narrative</legend>
        <div className="row-actions">
          <button type="button" onClick={draft} disabled={busy}>
            {aiEnabled ? "Draft with AI" : "Draft narrative"}
          </button>
          {!aiEnabled && <span className="muted small">AI not configured — the draft is built from the computed results.</span>}
        </div>
        <label className="sr-only" htmlFor="narr">Narrative text</label>
        <textarea id="narr" rows={10} value={narrative} onChange={(e) => setNarrative(e.target.value)}
          placeholder="Draft the narrative, then review and edit it. The exported report uses exactly this text." />
      </fieldset>

      <fieldset className="form-grid">
        <legend>Report details</legend>
        <label>Prepared for<input value={preparedFor} onChange={(e) => setPreparedFor(e.target.value)} /></label>
        <label className="check">
          <input type="checkbox" checked={includeSources} onChange={(e) => setIncludeSources(e.target.checked)} />
          Include sources & record IDs
        </label>
      </fieldset>

      <details className="branding">
        <summary>Branding</summary>
        <div className="form-grid">
          <label>Company<input {...b("company")} /></label>
          <label>Agent name<input {...b("agent_name")} /></label>
          <label>Title<input {...b("agent_title")} /></label>
          <label>Phone<input {...b("phone")} /></label>
          <label>Email<input {...b("email")} /></label>
          <label>Website<input {...b("website")} /></label>
          <label>License line<input {...b("license_line")} /></label>
          <label>
            Accent color
            <input type="color" value={branding.primary_color} onChange={(e) => setBranding({ ...branding, primary_color: e.target.value })} />
          </label>
          <label>
            Logo (PNG/JPEG)
            <input type="file" accept="image/png,image/jpeg" onChange={(e) => onLogo(e.target.files?.[0])} />
          </label>
          <label className="full">Footer note<input {...b("footer_note")} /></label>
        </div>
        <button type="button" className="secondary" onClick={saveBranding}>Save branding for the team</button>
      </details>

      <div className="row-actions sticky-actions">
        <button type="button" className="secondary" onClick={doPreview} disabled={busy}>Preview</button>
        <button type="button" onClick={() => doExport("pdf")} disabled={busy || a.valuation.estimate === null}>Export PDF</button>
        <button type="button" onClick={() => doExport("docx")} disabled={busy || a.valuation.estimate === null}>Export Word</button>
      </div>
      <p role="status" className="status">{status}</p>
      {preview && <ReportPreview r={preview} />}
    </div>
  );
}

function ReportPreview({ r }: { r: ReportModel }) {
  const accent = r.branding.primary_color || "#1F4E79";
  return (
    <article className="report-preview" style={{ ["--accent" as string]: accent }} aria-label="Report preview">
      <header>
        <div>
          <strong>{r.branding.company}</strong>
          <div className="small">{[r.branding.agent_name, r.branding.phone, r.branding.email].filter(Boolean).join(" · ")}</div>
        </div>
        {r.branding.logo_data_url && <img src={r.branding.logo_data_url} alt={`${r.branding.company} logo`} />}
      </header>
      <h3>{r.title}</h3>
      <p className="small">{r.prepared_for && `Prepared for ${r.prepared_for} · `}Valuation date {r.valuation_date}</p>
      <div className="rp-est">
        <div className="rp-value">{r.estimate.estimate}</div>
        <div>Range {r.estimate.range}</div>
        <div className="small">{r.estimate.basis} ({r.estimate.statistic})</div>
      </div>
      <h4>Comparable sales</h4>
      <ol className="small">
        {r.comps.map((c) => (
          <li key={String(c.n)}>
            {c.address} — {c.sale_date}, {c.price}, {c.above_grade_sf} sf AG ({c.ppsf_ag}/sf), {c.distance}
          </li>
        ))}
      </ol>
      {r.map_png_b64 && <img className="rp-map" src={`data:image/png;base64,${r.map_png_b64}`} alt="Location diagram of the subject and comparable sales" />}
      <h4>Calculation</h4>
      <ul className="small">{r.method_lines.map((l) => <li key={l}>{l}</li>)}</ul>
      {r.narrative && (<><h4>Analysis</h4><p className="pre small">{r.narrative}</p></>)}
      {r.sources.length > 0 && <p className="small muted">{r.sources.length} source records listed · CMA {r.fingerprint}</p>}
      <p className="tiny muted">{r.disclaimer}</p>
    </article>
  );
}
