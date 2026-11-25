"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, FilterLines, Plus } from "@untitledui/icons";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import type { Analysis, AreaScope, Hint } from "@/lib/types";
import { Callout } from "./callout";
import { LookbackPicker } from "./lookback-picker";
import { ScopePicker } from "./scope-picker";

interface Props {
    a: Analysis;
    onApplyHint: (h: Hint) => void;
    onScope: (s: AreaScope) => void;
    onLookback: (months: number) => void;
}

export function SearchExplanation({ a, onApplyHint, onScope, onLookback }: Props) {
    const s = a.search;
    const [open, setOpen] = useState(false);
    const removed = s.funnel.filter((f) => f.removed > 0);

    return (
        <section aria-labelledby="funnel-heading" className="flex flex-col gap-3 rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary">
            <div className="flex flex-wrap items-center gap-2">
                <h3 id="funnel-heading" className="flex-1 text-sm font-semibold text-primary">
                    {s.eligible_count} eligible of {s.pool_count} recorded transfers {s.scope_label}, {s.window_start} to {a.valuation_date}
                </h3>
                <Badge type="pill-color" color={s.insufficient ? "error" : s.limited ? "warning" : "success"} size="sm">
                    {s.insufficient ? "Below minimum" : s.limited ? "Limited" : "Enough comps"}
                </Badge>
            </div>
            <div className="flex flex-wrap items-start gap-x-6 gap-y-3">
                <ScopePicker value={a.criteria.area_scope} radiusMiles={a.criteria.max_distance_miles} subject={a.subject} onChange={onScope} />
                <LookbackPicker months={a.criteria.lookback_months} onChange={onLookback} />
            </div>
            {s.later_sales_excluded > 0 && (
                <p className="text-xs text-tertiary">{s.later_sales_excluded} sale(s) recorded after the valuation date were excluded.</p>
            )}

            <div>
                <Button
                    color="link-gray"
                    size="sm"
                    iconLeading={FilterLines}
                    iconTrailing={open ? ChevronUp : ChevronDown}
                    aria-expanded={open}
                    onClick={() => setOpen(!open)}
                >
                    What each rule removed
                </Button>
                {open && (
                    <ul className="mt-2 flex flex-col gap-1 text-sm text-tertiary">
                        {removed.length === 0 && <li>No transfers were removed by the rules.</li>}
                        {removed.map((f) => (
                            <li key={f.key}>
                                <span className="font-semibold text-secondary tabular-nums">{f.removed}</span> — {f.label}
                                {f.detail && <span className="text-quaternary"> ({f.detail})</span>}
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            {s.limit_explanation && (
                <Callout
                    tone={s.insufficient ? "error" : "warning"}
                    title={s.insufficient ? "Too few comparable sales" : "The search rules limited the results"}
                    role="status"
                    actions={
                        s.hints.length > 0
                            ? s.hints.map((h) => (
                                  <Button key={h.change} size="sm" color="secondary" iconLeading={Plus} onClick={() => onApplyHint(h)}>
                                      {h.change} (+{h.added})
                                  </Button>
                              ))
                            : undefined
                    }
                >
                    {s.limit_explanation}
                </Callout>
            )}
        </section>
    );
}
