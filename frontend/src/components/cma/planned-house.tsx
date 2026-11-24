"use client";

import { useState } from "react";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { InputNumber } from "@/components/base/input/input-number";
import { Select } from "@/components/base/select/select";
import { PROPERTY_TYPES } from "@/lib/format";
import type { Meta, Property, SubjectPlan } from "@/lib/types";

const KEEP = "__county";
const NUMBER_FIELDS: { key: keyof SubjectPlan; label: string; county: (s: Property) => number | null; min: number; max: number }[] = [
    { key: "beds", label: "Bedrooms", county: (s) => s.beds, min: 0, max: 20 },
    { key: "full_baths", label: "Full baths", county: (s) => s.full_baths, min: 0, max: 20 },
    { key: "half_baths", label: "Half baths", county: (s) => s.half_baths, min: 0, max: 20 },
    { key: "above_grade_sf", label: "Above-grade sq ft", county: (s) => s.above_grade_sf, min: 100, max: 30000 },
    { key: "total_finished_sf", label: "Total finished sq ft", county: (s) => s.total_finished_sf, min: 100, max: 30000 },
    { key: "year_built", label: "Year built", county: (s) => s.year_built, min: 1700, max: 2100 },
];

interface Props {
    /** The subject as the county records it (before any plan was applied). */
    county: Property;
    plan: SubjectPlan | null;
    options: Meta["subject_options"];
    onApply: (p: SubjectPlan | null) => void;
    onClose: () => void;
}

/** Drop blank fields; an empty plan means "use the county record". */
function clean(p: SubjectPlan): SubjectPlan | null {
    const out = Object.fromEntries(
        Object.entries(p).filter(([, v]) => v !== null && v !== undefined && v !== "" && !(typeof v === "number" && Number.isNaN(v))),
    ) as SubjectPlan;
    return Object.keys(out).some((k) => k !== "note") ? out : null;
}

/**
 * Describe the house being sold or built when it differs from the county record
 * (e.g. a new 5-bedroom house replacing an older 3-bedroom one). Comps are ranked and priced against it.
 */
export function PlannedHouseForm({ county, plan, options, onApply, onClose }: Props) {
    const [draft, setDraft] = useState<SubjectPlan>(plan ?? {});
    const set = (patch: SubjectPlan) => setDraft((d) => ({ ...d, ...patch }));

    const choice = (key: "style" | "condition" | "basement" | "property_type", label: string, values: { id: string; label: string }[], countyValue: string | null) => (
        <Select
            label={label}
            selectedKey={(draft[key] as string | null | undefined) ?? KEEP}
            onSelectionChange={(k) => set({ [key]: k === KEEP || k === null ? null : String(k) })}
            items={[{ id: KEEP, label: `Keep county (${countyValue ?? "not recorded"})` }, ...values]}
        >
            {(item) => <Select.Item id={item.id}>{item.label}</Select.Item>}
        </Select>
    );

    return (
        <form
            className="flex flex-col gap-4 border-t border-secondary bg-secondary_alt p-5"
            aria-label="Planned house"
            onSubmit={(e) => {
                e.preventDefault();
                onApply(clean(draft));
                onClose();
            }}
        >
            <div className="flex flex-col gap-1">
                <h3 className="text-sm font-semibold text-primary">House to sell or build</h3>
                <p className="text-sm text-tertiary">
                    Describe the house you are pricing when it differs from the county record, for example a new 5-bedroom house replacing the current one.
                    Comps are then chosen and priced against these values. Leave a field blank to keep the county value. Reports label these as agent input.
                </p>
            </div>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
                {choice(
                    "property_type",
                    "Property type",
                    (["DETACHED", "TOWNHOUSE", "CONDO", "DUPLEX"] as const).map((t) => ({ id: t, label: PROPERTY_TYPES[t] ?? t })),
                    PROPERTY_TYPES[county.property_type] ?? county.land_use,
                )}
                {NUMBER_FIELDS.map((f) => (
                    <InputNumber
                        key={f.key}
                        label={f.label}
                        placeholder={f.county(county) !== null ? `County: ${f.county(county)?.toLocaleString()}` : "County: not recorded"}
                        minValue={f.min}
                        maxValue={f.max}
                        formatOptions={{ maximumFractionDigits: 0, useGrouping: f.key !== "year_built" }}
                        value={(draft[f.key] as number | null | undefined) ?? Number.NaN}
                        onChange={(n) => set({ [f.key]: Number.isNaN(n) ? null : n })}
                    />
                ))}
                {choice("style", "Style", options.styles.map((x) => ({ id: x, label: x })), county.style)}
                {choice(
                    "condition",
                    "Condition",
                    options.conditions.map((x) => ({ id: x, label: x })),
                    county.condition,
                )}
                {choice("basement", "Basement", options.basements.map((x) => ({ id: x, label: x })), county.basement)}
            </div>
            <Input label="Note (shown in the report sources)" placeholder="e.g. builder plans dated 11/2026" value={draft.note ?? ""} onChange={(v) => set({ note: v })} />
            <div className="flex flex-wrap gap-2">
                <Button type="submit" size="md">
                    Apply to this CMA
                </Button>
                {plan && (
                    <Button
                        size="md"
                        color="secondary"
                        onClick={() => {
                            onApply(null);
                            onClose();
                        }}
                    >
                        Use county record
                    </Button>
                )}
                <Button size="md" color="tertiary" onClick={onClose}>
                    Cancel
                </Button>
            </div>
        </form>
    );
}
