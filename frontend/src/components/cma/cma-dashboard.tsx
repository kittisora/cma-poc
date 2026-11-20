"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, Edit05, Map01, SearchLg, Sliders02, Stars02, Zap } from "@untitledui/icons";
import dynamic from "next/dynamic";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { Tabs } from "@/components/application/tabs/tabs";
import { BadgeWithIcon } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { api } from "@/lib/api";
import type { Comp } from "@/lib/types";
import { useCma } from "@/providers/cma-provider";
import { cx } from "@/utils/cx";
import { AssistantSlideout } from "./assistant-slideout";
import { Callout } from "./callout";
import { CompDetail } from "./comp-detail";
import { CompTable } from "./comp-table";
import { CriteriaPanel } from "./criteria-panel";
import { EstimateSummary } from "./estimate-summary";
import { notify } from "./notify";
import { PpsfChart } from "./ppsf-chart";
import { PricingPanel } from "./pricing-panel";
import { PropertyFinder } from "./property-finder";
import { ReportPanel } from "./report-panel";
import { SearchExplanation } from "./search-explanation";
import { SubjectCard } from "./subject-card";
import { ValuationDate } from "./valuation-date";

// Leaflet needs the browser, so the map is loaded on the client only.
const CompMap = dynamic(() => import("./comp-map"), {
    ssr: false,
    loading: () => <div className="h-96 animate-pulse rounded-xl bg-secondary" aria-hidden="true" />,
});

const EXAMPLES = [
    { q: "8069 fairfax rd", zip: "22308", label: "8069 Fairfax Rd · 22308" },
    { q: "7910 martha washington st", zip: "22309", label: "7910 Martha Washington St · 22309" },
];

export function CmaDashboard() {
    const cma = useCma();
    const { meta, analysis, loading } = cma;
    const [tab, setTab] = useState<string>("pricing");
    const [detail, setDetail] = useState<Comp | null>(null);
    const [askOpen, setAskOpen] = useState(false);
    const [showNotes, setShowNotes] = useState(false);

    const detailComp = useMemo(() => (detail ? (analysis?.comps.find((c) => c.sale_id === detail.sale_id) ?? detail) : null), [detail, analysis]);

    if (cma.metaError) {
        return (
            <EmptyState size="md" className="py-16">
                <EmptyState.Header pattern="circle">
                    <EmptyState.FeaturedIcon icon={AlertTriangle} color="error" theme="light" />
                </EmptyState.Header>
                <EmptyState.Content>
                    <EmptyState.Title>Cannot reach the API</EmptyState.Title>
                    <EmptyState.Description>
                        {cma.metaError}. Start the backend with <code>scripts\run.ps1</code> (or <code>uvicorn app.main:app --port 8000</code>).
                    </EmptyState.Description>
                </EmptyState.Content>
            </EmptyState>
        );
    }
    if (!meta || !cma.criteria) {
        return (
            <div className="flex flex-1 items-center justify-center py-24">
                <LoadingIndicator type="line-spinner" size="md" label="Loading…" />
            </div>
        );
    }

    const tryExample = async (q: string, zip: string) => {
        try {
            const r = await api.search(q, zip);
            if (r.results[0]) cma.chooseSubject(r.results[0]);
            else notify("error", "Example address not found", "Run the data refresh first.");
        } catch (e) {
            notify("error", "Search failed", (e as Error).message);
        }
    };

    const subjectLabel = analysis ? `${analysis.subject.address}, ${analysis.subject.zip}` : "";

    return (
        <div className="flex flex-col gap-6">
            <section aria-label="Subject and valuation date" className="flex flex-col gap-4 rounded-xl bg-primary p-4 shadow-xs ring-1 ring-secondary md:p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
                    <div className="flex-1">
                        <PropertyFinder current={cma.subject} onSelect={cma.chooseSubject} />
                    </div>
                    <ValuationDate value={cma.valuationDate} max={meta.today} onChange={cma.setValuationDate} />
                    <div className="flex h-10 min-w-44 items-center lg:justify-end" role="status" aria-live="polite">
                        {loading ? (
                            <LoadingIndicator type="line-simple" size="sm" label="Analyzing…" />
                        ) : cma.readyIn !== null ? (
                            <BadgeWithIcon type="pill-color" color="success" size="md" iconLeading={Zap}>
                                Comps and pricing in {cma.readyIn.toFixed(1)} s
                            </BadgeWithIcon>
                        ) : null}
                    </div>
                </div>
            </section>

            {meta.data.sales === 0 && (
                <Callout tone="warning" title="No data loaded yet">
                    Run the data refresh (<code>scripts\refresh.ps1</code>) before searching.
                </Callout>
            )}
            {cma.error && (
                <Callout
                    tone="error"
                    title="Something went wrong"
                    role="alert"
                    actions={
                        <Button size="sm" color="secondary" onClick={cma.clearError}>
                            Dismiss
                        </Button>
                    }
                >
                    {cma.error}
                </Callout>
            )}

            {!analysis && !loading && (
                <EmptyState size="lg" className="py-12">
                    <EmptyState.Header pattern="grid">
                        <EmptyState.FeaturedIcon icon={SearchLg} color="brand" theme="light" />
                    </EmptyState.Header>
                    <EmptyState.Content>
                        <EmptyState.Title>Find the subject property</EmptyState.Title>
                        <EmptyState.Description>
                            Choose a subdivision, block or street, then pick the property. The app finds recorded sales on or before the valuation date, ranks them
                            by similarity (never by price), and prices the subject with the workbook&apos;s price-per-square-foot method.
                        </EmptyState.Description>
                    </EmptyState.Content>
                    <EmptyState.Footer className="flex-wrap justify-center">
                        {EXAMPLES.map((e) => (
                            <Button key={e.q} color="secondary" iconLeading={Map01} onClick={() => tryExample(e.q, e.zip)}>
                                Try {e.label}
                            </Button>
                        ))}
                    </EmptyState.Footer>
                </EmptyState>
            )}
            {!analysis && loading && (
                <div className="flex justify-center py-24">
                    <LoadingIndicator type="line-spinner" size="md" label="Finding comparable sales…" />
                </div>
            )}

            {analysis && (
                <div className={cx("grid grid-cols-1 gap-6 2xl:grid-cols-[minmax(0,1fr)_500px] xl:grid-cols-[minmax(0,1fr)_440px]")} aria-busy={loading}>
                    <div className="flex min-w-0 flex-col gap-6">
                        <SubjectCard a={analysis} />
                        <SearchExplanation a={analysis} onApplyHint={cma.applyHint} />
                        <div className="grid grid-cols-1 gap-6 2xl:grid-cols-[3fr_2fr]">
                            <CompMap
                                subject={analysis.subject}
                                comps={analysis.comps}
                                radiusMiles={analysis.criteria.max_distance_miles}
                                highlighted={cma.highlighted}
                                onSelect={cma.setHighlighted}
                            />
                            <PpsfChart a={analysis} highlighted={cma.highlighted} onHighlight={cma.setHighlighted} />
                        </div>
                        <CompTable
                            comps={analysis.comps}
                            eligibleCount={analysis.search.eligible_count}
                            selectedIds={cma.selectedIds}
                            highlighted={cma.highlighted}
                            busy={loading}
                            manual={analysis.selection_mode === "manual"}
                            maxResults={cma.criteria.max_results}
                            onHighlight={cma.setHighlighted}
                            onToggle={cma.toggleComp}
                            onResetSelection={cma.resetSelection}
                            onTotalFinished={cma.saveTotalFinished}
                            onOpenDetail={setDetail}
                        />
                    </div>

                    <aside aria-label="Valuation and report" className="flex min-w-0 flex-col gap-4 *:shrink-0 xl:sticky xl:top-20 xl:max-h-[calc(100dvh-6rem)] xl:self-start xl:overflow-y-auto xl:pb-2">
                        <EstimateSummary a={analysis} aiEnabled={meta.ai_enabled} onAskAi={() => setAskOpen(true)} />

                        {analysis.warnings.length > 0 && (
                            <Callout
                                tone="warning"
                                title={`${analysis.warnings.length} note${analysis.warnings.length > 1 ? "s" : ""} on data and method`}
                                actions={
                                    <Button
                                        size="sm"
                                        color="link-gray"
                                        iconTrailing={showNotes ? ChevronUp : ChevronDown}
                                        aria-expanded={showNotes}
                                        onClick={() => setShowNotes(!showNotes)}
                                    >
                                        {showNotes ? "Hide" : "Show"}
                                    </Button>
                                }
                            >
                                {showNotes && (
                                    <ul className="flex list-disc flex-col gap-1 pl-4 text-xs">
                                        {analysis.warnings.map((w) => (
                                            <li key={w}>{w}</li>
                                        ))}
                                    </ul>
                                )}
                            </Callout>
                        )}

                        <div className="rounded-xl bg-primary p-4 shadow-xs ring-1 ring-secondary">
                            <Tabs selectedKey={tab} onSelectionChange={(k) => setTab(String(k))}>
                                <Tabs.List
                                    type="button-minimal"
                                    size="sm"
                                    fullWidth
                                    aria-label="CMA tools"
                                    items={[
                                        { id: "pricing", label: "Pricing", icon: Edit05 },
                                        { id: "rules", label: "Search rules", icon: Sliders02 },
                                        { id: "report", label: "Report", icon: Stars02 },
                                    ]}
                                />
                                <Tabs.Panel id="pricing" className="pt-5">
                                    <PricingPanel
                                        a={analysis}
                                        adjustments={cma.adjustments}
                                        setAdjustments={cma.setAdjustments}
                                        appreciation={cma.appreciation}
                                        setAppreciation={cma.setAppreciation}
                                        pointStat={cma.pointStat}
                                        setPointStat={cma.setPointStat}
                                        primaryBasis={cma.primaryBasis}
                                        setPrimaryBasis={cma.setPrimaryBasis}
                                        onSubjectTotalFinished={(v) => cma.saveTotalFinished(analysis.subject.pin, v)}
                                    />
                                </Tabs.Panel>
                                <Tabs.Panel id="rules" className="pt-5">
                                    <CriteriaPanel
                                        criteria={cma.criteria}
                                        meta={meta}
                                        onChange={cma.changeCriteria}
                                        onReset={() => cma.changeCriteria(meta.default_criteria)}
                                    />
                                </Tabs.Panel>
                                <Tabs.Panel id="report" className="pt-5">
                                    {cma.req && (
                                        <ReportPanel
                                            a={analysis}
                                            req={cma.req}
                                            aiEnabled={meta.ai_enabled}
                                            narrative={cma.narrative}
                                            narrativeSource={cma.narrativeSource}
                                            setNarrative={cma.setNarrative}
                                        />
                                    )}
                                </Tabs.Panel>
                            </Tabs>
                        </div>
                    </aside>
                </div>
            )}

            <CompDetail
                comp={detailComp}
                isSelected={detailComp ? cma.selectedIds.includes(detailComp.sale_id) : false}
                onToggle={cma.toggleComp}
                onClose={() => setDetail(null)}
            />
            <AssistantSlideout
                open={askOpen}
                onClose={() => setAskOpen(false)}
                req={cma.req}
                subjectLabel={subjectLabel}
                enabled={meta.ai_enabled}
                model={meta.ai_model}
                provider={meta.ai_provider}
            />
        </div>
    );
}
