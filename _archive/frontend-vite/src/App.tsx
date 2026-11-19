import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { AgentPanel } from "./components/AgentPanel";
import { CompMap } from "./components/CompMap";
import { CompTable } from "./components/CompTable";
import { CriteriaPanel } from "./components/CriteriaPanel";
import { DataView } from "./components/DataView";
import { ReportPanel } from "./components/ReportPanel";
import { SearchBar } from "./components/SearchBar";
import { SearchExplanation, SubjectCard } from "./components/SubjectCard";
import { EstimateSummary, PricingPanel } from "./components/ValuationPanel";
import { WorkbookView } from "./components/WorkbookView";
import type { Adjustment, Analysis, CMARequest, Criteria, Hint, Meta, SearchResult } from "./types";

type View = "cma" | "workbook" | "data";
type Tab = "pricing" | "rules" | "report" | "ai";

const TABS: { id: Tab; label: string }[] = [
  { id: "pricing", label: "Pricing" },
  { id: "rules", label: "Search rules" },
  { id: "report", label: "Report" },
  { id: "ai", label: "Ask AI" },
];

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState("");
  const [view, setView] = useState<View>("cma");

  const [pin, setPin] = useState<string | null>(null);
  const [valuationDate, setValuationDate] = useState("");
  const [criteria, setCriteria] = useState<Criteria | null>(null);
  const [selected, setSelected] = useState<number[] | null>(null);
  const [adjustments, setAdjustments] = useState<Adjustment[]>([]);
  const [appreciation, setAppreciation] = useState(0);
  const [pointStat, setPointStat] = useState<"mean" | "median">("mean");
  const [primaryBasis, setPrimaryBasis] = useState<"auto" | "above_grade" | "total_finished">("auto");
  const [narrative, setNarrative] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("pricing");
  const [readyIn, setReadyIn] = useState<string>("");
  const t0 = useRef<number | null>(null);

  useEffect(() => {
    api
      .meta()
      .then((m) => {
        setMeta(m);
        setCriteria(m.default_criteria);
        setValuationDate(m.today);
      })
      .catch((e) => setMetaError(e.message));
  }, []);

  const req: CMARequest | null = useMemo(
    () =>
      pin && criteria && valuationDate
        ? {
            subject_pin: pin,
            valuation_date: valuationDate,
            criteria,
            selected_sale_ids: selected,
            adjustments: adjustments.filter((a) => a.label.trim()),
            appreciation_pct: appreciation,
            point_statistic: pointStat,
            primary_basis: primaryBasis,
          }
        : null,
    [pin, criteria, valuationDate, selected, adjustments, appreciation, pointStat, primaryBasis],
  );

  useEffect(() => {
    if (!req) return;
    const ctrl = new AbortController();
    const t = setTimeout(() => {
      setLoading(true);
      api
        .analyze(req, ctrl.signal)
        .then((a) => {
          setAnalysis(a);
          setError("");
          if (t0.current !== null) {
            setReadyIn(`Comps and pricing ready in ${((performance.now() - t0.current) / 1000).toFixed(1)} s`);
            t0.current = null;
          }
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        })
        .finally(() => setLoading(false));
    }, 250);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [req, refreshKey]);

  const chooseSubject = (r: SearchResult) => {
    t0.current = performance.now();
    setReadyIn("");
    setPin(r.pin);
    setSelected(null);
    setAdjustments([]);
    setAppreciation(0);
    setNarrative("");
    setHighlighted(null);
    setAnalysis(null);
  };

  const changeCriteria = (c: Criteria) => {
    setCriteria(c);
    setSelected(null);
  };

  const toggle = (id: number, include: boolean) => {
    const base = selected ?? analysis?.selected_sale_ids ?? [];
    setSelected(include ? [...base.filter((x) => x !== id), id] : base.filter((x) => x !== id));
  };

  const saveInput = useCallback(async (p: string, value: number | null) => {
    try {
      await api.setInput(p, "total_finished_sf", value, "entered in CMA");
      setRefreshKey((k) => k + 1);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const applyHint = (h: Hint) => criteria && changeCriteria({ ...criteria, ...h.patch } as Criteria);

  if (metaError) {
    return (
      <div className="page">
        <h1>CMA</h1>
        <p className="warn">Cannot reach the API ({metaError}). Start the backend: <code>uvicorn app.main:app --port 8000</code></p>
      </div>
    );
  }
  if (!meta || !criteria) return <div className="page">Loading…</div>;

  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className="topbar">
        <div className="brand">
          <span className="logo" aria-hidden="true">▲</span>
          <span>
            CMA <span className="muted">· Fairfax County {meta.target_zips.join(" / ")}</span>
          </span>
        </div>
        <nav aria-label="Sections">
          {(["cma", "workbook", "data"] as View[]).map((v) => (
            <button key={v} type="button" className={`nav ${view === v ? "active" : ""}`} aria-current={view === v ? "page" : undefined} onClick={() => setView(v)}>
              {v === "cma" ? "CMA" : v === "workbook" ? "Workbook check" : "Data & sources"}
            </button>
          ))}
        </nav>
        <div className="data-badge" title={meta.provider.attribution}>
          Public records (not MLS) · latest sale {meta.data.latest_sale_date ?? "—"}
        </div>
      </header>

      {view === "workbook" && <WorkbookView />}
      {view === "data" && <DataView meta={meta} />}
      {view === "cma" && (
        <main id="main" className="cma">
          <div className="toolbar">
            <SearchBar zips={meta.target_zips} onSelect={chooseSubject} />
            <label className="date">
              Valuation date
              <input type="date" value={valuationDate} max={meta.today} onChange={(e) => { setValuationDate(e.target.value); setSelected(null); }} />
            </label>
            <p className="status small" role="status">
              {loading ? "Analyzing…" : readyIn}
            </p>
          </div>
          {error && <p className="warn" role="alert">{error}</p>}
          {meta.data.sales === 0 && (
            <p className="warn">No data loaded yet. Run the data refresh in the backend before searching.</p>
          )}
          {!analysis && !loading && (
            <section className="empty">
              <h1>Start with an address</h1>
              <p>
                Search an address in ZIP {meta.target_zips.join(" or ")}. The app finds recorded sales on or before the
                valuation date, ranks them by similarity, and prices the subject with the workbook's price-per-square-foot
                method.
              </p>
            </section>
          )}
          {analysis && (
            <div className={`grid ${loading ? "is-loading" : ""}`} aria-busy={loading}>
              <div className="left">
                <SubjectCard a={analysis} />
                <SearchExplanation a={analysis} onApplyHint={applyHint} />
                <CompMap
                  subject={analysis.subject}
                  comps={analysis.comps}
                  radiusMiles={analysis.criteria.max_distance_miles}
                  highlighted={highlighted}
                  onSelect={setHighlighted}
                />
                <CompTable
                  comps={analysis.comps}
                  highlighted={highlighted}
                  onHighlight={setHighlighted}
                  onToggle={toggle}
                  onTotalFinished={saveInput}
                  busy={loading}
                  selectedIds={selected ?? analysis.selected_sale_ids}
                />
                {analysis.selection_mode === "manual" && (
                  <button type="button" className="secondary" onClick={() => setSelected(null)}>
                    Reset to the top {criteria.max_results} ranked comps
                  </button>
                )}
              </div>
              <aside className="right" aria-label="Valuation and report">
                <EstimateSummary a={analysis} />
                {analysis.warnings.length > 0 && (
                  <details className="warnings">
                    <summary>{analysis.warnings.length} note{analysis.warnings.length > 1 ? "s" : ""} on data and method</summary>
                    <ul className="small">{analysis.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
                  </details>
                )}
                <div role="tablist" aria-label="CMA tools" className="tabs">
                  {TABS.map((t) => (
                    <button
                      key={t.id}
                      role="tab"
                      id={`tab-${t.id}`}
                      aria-selected={tab === t.id}
                      aria-controls={`panel-${t.id}`}
                      tabIndex={tab === t.id ? 0 : -1}
                      onClick={() => setTab(t.id)}
                      onKeyDown={(e) => {
                        const i = TABS.findIndex((x) => x.id === tab);
                        if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                          const n = TABS[(i + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length];
                          setTab(n.id);
                          document.getElementById(`tab-${n.id}`)?.focus();
                        }
                      }}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
                <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="tabpanel">
                  {tab === "pricing" && (
                    <PricingPanel
                      a={analysis}
                      adjustments={adjustments}
                      setAdjustments={setAdjustments}
                      appreciation={appreciation}
                      setAppreciation={setAppreciation}
                      pointStat={pointStat}
                      setPointStat={setPointStat}
                      primaryBasis={primaryBasis}
                      setPrimaryBasis={setPrimaryBasis}
                      onSubjectTotalFinished={(v) => saveInput(analysis.subject.pin, v)}
                    />
                  )}
                  {tab === "rules" && (
                    <CriteriaPanel criteria={criteria} meta={meta} onChange={changeCriteria} onReset={() => changeCriteria(meta.default_criteria)} />
                  )}
                  {tab === "report" && req && (
                    <ReportPanel a={analysis} req={req} aiEnabled={meta.ai_enabled} narrative={narrative} setNarrative={setNarrative} />
                  )}
                  {tab === "ai" && req && <AgentPanel req={req} enabled={meta.ai_enabled} model={meta.ai_model} />}
                </div>
              </aside>
            </div>
          )}
        </main>
      )}
      <footer className="foot small muted">
        Data: Fairfax County, Virginia public records via ArcGIS Online · not an appraisal ·{" "}
        <a href={meta.provider.terms_url} target="_blank" rel="noreferrer">county data terms</a>
      </footer>
    </>
  );
}
