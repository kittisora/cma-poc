"use client";

import type { PropsWithChildren } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Adjustment, Analysis, CMARequest, Criteria, Hint, Meta, SearchResult } from "@/lib/types";

export type PrimaryBasis = "auto" | "above_grade" | "total_finished";
export type PointStat = "mean" | "median";

interface CmaState {
    meta: Meta | null;
    metaError: string;
    subject: SearchResult | null;
    valuationDate: string;
    criteria: Criteria | null;
    selectedIds: number[];
    adjustments: Adjustment[];
    appreciation: number;
    pointStat: PointStat;
    primaryBasis: PrimaryBasis;
    narrative: string;
    narrativeSource: string;
    analysis: Analysis | null;
    req: CMARequest | null;
    loading: boolean;
    error: string;
    highlighted: number | null;
    readyIn: number | null;
    chooseSubject: (r: SearchResult) => void;
    setValuationDate: (d: string) => void;
    changeCriteria: (c: Criteria) => void;
    applyHint: (h: Hint) => void;
    toggleComp: (id: number, include: boolean) => void;
    resetSelection: () => void;
    setAdjustments: (a: Adjustment[]) => void;
    setAppreciation: (n: number) => void;
    setPointStat: (s: PointStat) => void;
    setPrimaryBasis: (b: PrimaryBasis) => void;
    setNarrative: (s: string, source?: string) => void;
    setHighlighted: (id: number | null) => void;
    saveTotalFinished: (pin: string, value: number | null) => Promise<void>;
    clearError: () => void;
}

const CmaContext = createContext<CmaState | null>(null);

export const useCma = () => {
    const ctx = useContext(CmaContext);
    if (!ctx) throw new Error("useCma must be used inside <CmaProvider>");
    return ctx;
};

export function CmaProvider({ children }: PropsWithChildren) {
    const [meta, setMeta] = useState<Meta | null>(null);
    const [metaError, setMetaError] = useState("");
    const [subject, setSubject] = useState<SearchResult | null>(null);
    const [valuationDate, setValuationDateState] = useState("");
    const [criteria, setCriteria] = useState<Criteria | null>(null);
    const [manualSelection, setManualSelection] = useState<number[] | null>(null);
    const [adjustments, setAdjustments] = useState<Adjustment[]>([]);
    const [appreciation, setAppreciation] = useState(0);
    const [pointStat, setPointStat] = useState<PointStat>("mean");
    const [primaryBasis, setPrimaryBasis] = useState<PrimaryBasis>("auto");
    const [narrative, setNarrativeText] = useState("");
    const [narrativeSource, setNarrativeSource] = useState("agent");
    const [refreshKey, setRefreshKey] = useState(0);
    const [analysis, setAnalysis] = useState<Analysis | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [highlighted, setHighlighted] = useState<number | null>(null);
    const [readyIn, setReadyIn] = useState<number | null>(null);
    const t0 = useRef<number | null>(null);

    useEffect(() => {
        api.meta()
            .then((m) => {
                setMeta(m);
                setCriteria(m.default_criteria);
                setValuationDateState(m.today);
            })
            .catch((e: Error) => setMetaError(e.message));
    }, []);

    const req: CMARequest | null = useMemo(
        () =>
            subject && criteria && valuationDate
                ? {
                      subject_pin: subject.pin,
                      valuation_date: valuationDate,
                      criteria,
                      selected_sale_ids: manualSelection,
                      adjustments: adjustments.filter((a) => a.label.trim()),
                      appreciation_pct: appreciation,
                      point_statistic: pointStat,
                      primary_basis: primaryBasis,
                  }
                : null,
        [subject, criteria, valuationDate, manualSelection, adjustments, appreciation, pointStat, primaryBasis],
    );

    // Re-run the analysis (debounced) whenever an input changes. Only the latest request wins.
    useEffect(() => {
        if (!req) return;
        const ctrl = new AbortController();
        const t = setTimeout(() => {
            setLoading(true);
            api.analyze(req, ctrl.signal)
                .then((a) => {
                    setAnalysis(a);
                    setError("");
                    if (t0.current !== null) {
                        setReadyIn((performance.now() - t0.current) / 1000);
                        t0.current = null;
                    }
                })
                .catch((e: Error) => {
                    if (e.name !== "AbortError") setError(e.message);
                })
                .finally(() => {
                    if (!ctrl.signal.aborted) setLoading(false);
                });
        }, 250);
        return () => {
            clearTimeout(t);
            ctrl.abort();
        };
    }, [req, refreshKey]);

    const chooseSubject = useCallback((r: SearchResult) => {
        t0.current = performance.now();
        setReadyIn(null);
        setSubject(r);
        setManualSelection(null);
        setAdjustments([]);
        setAppreciation(0);
        setNarrativeText("");
        setHighlighted(null);
        setAnalysis(null);
    }, []);

    const changeCriteria = useCallback((c: Criteria) => {
        setCriteria(c);
        setManualSelection(null);
    }, []);

    const value: CmaState = {
        meta,
        metaError,
        subject,
        valuationDate,
        criteria,
        selectedIds: manualSelection ?? analysis?.selected_sale_ids ?? [],
        adjustments,
        appreciation,
        pointStat,
        primaryBasis,
        narrative,
        narrativeSource,
        analysis,
        req,
        loading,
        error,
        highlighted,
        readyIn,
        chooseSubject,
        setValuationDate: (d) => {
            setValuationDateState(d);
            setManualSelection(null);
        },
        changeCriteria,
        applyHint: (h) => criteria && changeCriteria({ ...criteria, ...h.patch } as Criteria),
        toggleComp: (id, include) => {
            const base = manualSelection ?? analysis?.selected_sale_ids ?? [];
            setManualSelection(include ? [...base.filter((x) => x !== id), id] : base.filter((x) => x !== id));
        },
        resetSelection: () => setManualSelection(null),
        setAdjustments,
        setAppreciation,
        setPointStat,
        setPrimaryBasis,
        setNarrative: (s, source) => {
            setNarrativeText(s);
            if (source) setNarrativeSource(source);
        },
        setHighlighted,
        saveTotalFinished: async (pin, v) => {
            try {
                await api.setInput(pin, "total_finished_sf", v, "entered in CMA");
                setRefreshKey((k) => k + 1);
            } catch (e) {
                setError((e as Error).message);
            }
        },
        clearError: () => setError(""),
    };

    return <CmaContext.Provider value={value}>{children}</CmaContext.Provider>;
}
