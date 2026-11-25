"use client";

import { useEffect, useState } from "react";
import { RefreshCcw01 } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { Checkbox } from "@/components/base/checkbox/checkbox";
import { InputNumber } from "@/components/base/input/input-number";
import { Slider } from "@/components/base/slider/slider";
import { Toggle } from "@/components/base/toggle/toggle";
import type { Criteria, Meta, Property, Weights } from "@/lib/types";
import { LookbackPicker } from "./lookback-picker";
import { ScopePicker } from "./scope-picker";

const WEIGHT_LABELS: Record<keyof Weights, string> = {
    distance: "Distance",
    recency: "Sale recency",
    living_area: "Living area",
    beds: "Bedrooms",
    baths: "Bathrooms",
    lot_size: "Lot size",
    age: "Year built",
    style: "Style",
    condition: "Assessor condition & grade",
    features: "Basement / fireplace / garage",
};

interface Props {
    criteria: Criteria;
    meta: Meta;
    subject?: Property | null;
    onChange: (c: Criteria) => void;
    onReset: () => void;
}

const num = (n: number, fallback: number) => (Number.isNaN(n) ? fallback : n);

/** Moves freely while dragging; re-runs the analysis only when released. */
function WeightSlider({ labelledBy, value, onCommit }: { labelledBy: string; value: number; onCommit: (n: number) => void }) {
    const [local, setLocal] = useState(value);
    useEffect(() => {
        setLocal(value);
    }, [value]);
    const first = (x: number | number[]) => (Array.isArray(x) ? x[0] : x);
    return (
        <Slider
            aria-labelledby={labelledBy}
            minValue={0}
            maxValue={40}
            step={1}
            value={local}
            labelFormatter={(x) => String(x)}
            onChange={(x) => setLocal(first(x))}
            onChangeEnd={(x) => first(x) !== value && onCommit(first(x))}
        />
    );
}

export function CriteriaPanel({ criteria: c, meta, subject, onChange, onReset }: Props) {
    const set = (patch: Partial<Criteria>) => onChange({ ...c, ...patch });
    const allValidity = [...meta.validity_options.default, ...meta.validity_options.optional];
    const totalWeight = Object.values(c.weights).reduce((s, w) => s + w, 0);

    return (
        <div className="flex flex-col gap-6">
            <fieldset className="flex flex-col gap-4">
                <legend className="mb-1 text-sm font-semibold text-primary">Eligibility rules</legend>
                <ScopePicker value={c.area_scope} radiusMiles={c.max_distance_miles} subject={subject} onChange={(area_scope) => set({ area_scope })} />
                <LookbackPicker months={c.lookback_months} onChange={(lookback_months) => set({ lookback_months })} />
                <div className="grid grid-cols-2 gap-4">
                    <InputNumber
                        label="Radius (miles)"
                        hint={c.area_scope !== "radius" ? "Not used for subdivision/block searches" : undefined}
                        isDisabled={c.area_scope !== "radius"}
                        minValue={0.1}
                        maxValue={10}
                        step={0.1}
                        value={c.max_distance_miles}
                        onChange={(n) => set({ max_distance_miles: num(n, 1) })}
                    />
                    <InputNumber label="Look-back (months)" minValue={1} maxValue={60} value={c.lookback_months} onChange={(n) => set({ lookback_months: num(n, 12) })} />
                    <InputNumber label="Comps to select" minValue={1} maxValue={25} value={c.max_results} onChange={(n) => set({ max_results: num(n, 5) })} />
                    <InputNumber label="Minimum comps" minValue={1} maxValue={10} value={c.min_comps} onChange={(n) => set({ min_comps: num(n, 3) })} />
                    <InputNumber
                        label="Living-area tolerance ±%"
                        placeholder="any"
                        minValue={5}
                        maxValue={200}
                        value={c.living_area_tolerance_pct ?? NaN}
                        onChange={(n) => set({ living_area_tolerance_pct: Number.isNaN(n) ? null : n })}
                    />
                    <InputNumber
                        label="Minimum price"
                        minValue={0}
                        step={1000}
                        value={c.min_price}
                        formatOptions={{ style: "currency", currency: "USD", maximumFractionDigits: 0 }}
                        onChange={(n) => set({ min_price: num(n, 0) })}
                    />
                </div>
                <Toggle label="Same property type only" isSelected={c.same_property_type} onChange={(v) => set({ same_property_type: v })} />
                <Toggle
                    label="Exclude multi-parcel deeds"
                    hint="One deed covering several parcels has no per-parcel price."
                    isSelected={c.exclude_multi_parcel}
                    onChange={(v) => set({ exclude_multi_parcel: v })}
                />
            </fieldset>

            <fieldset className="flex flex-col gap-3 border-t border-secondary pt-5">
                <legend className="mb-1 text-sm font-semibold text-primary">County sale-validity codes accepted</legend>
                {allValidity.map((v) => (
                    <Checkbox
                        key={v}
                        label={v}
                        isSelected={c.allowed_validity.includes(v)}
                        onChange={(on) => set({ allowed_validity: on ? [...c.allowed_validity, v] : c.allowed_validity.filter((x) => x !== v) })}
                    />
                ))}
                <p className="text-xs text-tertiary">Non-market transfers (no consideration, related parties, foreclosure, etc.) are never eligible.</p>
            </fieldset>

            <fieldset className="flex flex-col gap-5 border-t border-secondary pt-5">
                <legend className="mb-1 text-sm font-semibold text-primary">Ranking weights</legend>
                {(Object.keys(WEIGHT_LABELS) as (keyof Weights)[]).map((k) => (
                    <div key={k} className="flex flex-col gap-1">
                        <div className="flex items-baseline justify-between text-sm">
                            <span id={`w-${k}`} className="font-medium text-secondary">
                                {WEIGHT_LABELS[k]}
                            </span>
                            <span className="text-tertiary tabular-nums">
                                {c.weights[k]} {totalWeight > 0 && <span className="text-quaternary">({Math.round((c.weights[k] / totalWeight) * 100)}%)</span>}
                            </span>
                        </div>
                        <WeightSlider labelledBy={`w-${k}`} value={c.weights[k]} onCommit={(x) => set({ weights: { ...c.weights, [k]: x } })} />
                    </div>
                ))}
                <p className="text-xs text-tertiary">
                    Each comp&apos;s score is the weighted average of the factors that could be compared (0–100). Factors without data are left out and listed.
                    Sale price is never a factor.
                </p>
            </fieldset>

            <div>
                <Button size="sm" color="secondary" iconLeading={RefreshCcw01} onClick={onReset}>
                    Reset to defaults
                </Button>
            </div>
        </div>
    );
}
