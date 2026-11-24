"use client";

import { Plus, Trash01 } from "@untitledui/icons";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { Input } from "@/components/base/input/input";
import { InputNumber } from "@/components/base/input/input-number";
import { RadioButton, RadioGroup } from "@/components/base/radio-buttons/radio-buttons";
import { money } from "@/lib/format";
import type { Adjustment, Analysis, BasisResult } from "@/lib/types";
import type { PointStat, PrimaryBasis } from "@/providers/cma-provider";
import { cx } from "@/utils/cx";
import { Callout } from "./callout";

interface Props {
    a: Analysis;
    adjustments: Adjustment[];
    setAdjustments: (a: Adjustment[]) => void;
    appreciation: number;
    setAppreciation: (n: number) => void;
    pointStat: PointStat;
    setPointStat: (s: PointStat) => void;
    primaryBasis: PrimaryBasis;
    setPrimaryBasis: (b: PrimaryBasis) => void;
    onSubjectTotalFinished: (v: number | null) => void;
}

const Fieldset = ({ legend, children, className }: { legend: string; children: React.ReactNode; className?: string }) => (
    <fieldset className={cx("flex flex-col gap-4 border-t border-secondary pt-5 first:border-t-0 first:pt-0", className)}>
        <legend className="mb-1 text-sm font-semibold text-primary">{legend}</legend>
        {children}
    </fieldset>
);

export function PricingPanel(p: Props) {
    const v = p.a.valuation;
    const s = p.a.subject;
    const updateAdj = (i: number, patch: Partial<Adjustment>) => p.setAdjustments(p.adjustments.map((a, j) => (j === i ? { ...a, ...patch } : a)));

    return (
        <div className="flex flex-col gap-6">
            <Fieldset legend="Subject area">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <Input label="Above-grade sq ft" hint="County assessor (SFLA)" value={s.above_grade_sf?.toLocaleString() ?? "not recorded"} isReadOnly />
                    <InputNumber
                        key={`${s.pin}-${s.total_finished_sf}`}
                        label="Total finished sq ft"
                        hint={s.planned?.includes("total_finished_sf") ? "From the planned house (edit it on the subject card)" : "From the listing (agent input)"}
                        isReadOnly={s.planned?.includes("total_finished_sf")}
                        placeholder="not in county records"
                        minValue={100}
                        maxValue={30000}
                        defaultValue={s.total_finished_sf ?? undefined}
                        formatOptions={{ maximumFractionDigits: 0 }}
                        onChange={(n) => {
                            const next = Number.isNaN(n) ? null : n;
                            if (next !== s.total_finished_sf) p.onSubjectTotalFinished(next);
                        }}
                    />
                </div>
            </Fieldset>

            <Fieldset legend="Method">
                <RadioGroup aria-label="Headline method" value={p.primaryBasis} onChange={(x) => p.setPrimaryBasis(x as PrimaryBasis)}>
                    <RadioButton value="auto" label="Automatic" hint="Total finished $/sf when the subject and all comps have it; otherwise above-grade." />
                    <RadioButton value="above_grade" label="Above-grade $/sf" hint="County SFLA for the subject and comps." />
                    <RadioButton value="total_finished" label="Total finished $/sf" hint="Workbook method; needs listing data." />
                </RadioGroup>
                <div className="flex flex-wrap items-end gap-4">
                    <div className="flex flex-col gap-1.5">
                        <span className="text-sm font-medium text-secondary" id="point-stat-label">
                            Point estimate
                        </span>
                        <ButtonGroup
                            aria-labelledby="point-stat-label"
                            size="sm"
                            disallowEmptySelection
                            selectedKeys={new Set([p.pointStat])}
                            onSelectionChange={(keys) => {
                                const k = [...keys][0];
                                if (k) p.setPointStat(k as PointStat);
                            }}
                        >
                            <ButtonGroupItem id="mean">Average $/sf (workbook)</ButtonGroupItem>
                            <ButtonGroupItem id="median">Median $/sf</ButtonGroupItem>
                        </ButtonGroup>
                    </div>
                    <InputNumber
                        className="w-40"
                        label="Appreciation %"
                        step={0.1}
                        minValue={-50}
                        maxValue={50}
                        value={p.appreciation}
                        formatOptions={{ maximumFractionDigits: 2 }}
                        onChange={(n) => p.setAppreciation(Number.isNaN(n) ? 0 : n)}
                    />
                </div>
            </Fieldset>

            <Fieldset legend="Adjustments (agent assumptions)">
                {p.adjustments.length === 0 && (
                    <p className="text-sm text-tertiary">None. Add one for features the comps do not share, such as a detached garage or ADU.</p>
                )}
                {p.adjustments.map((a, i) => (
                    <div key={i} className="grid grid-cols-[1fr_8rem_auto] items-end gap-2 sm:grid-cols-[1fr_9rem_6rem_1fr_auto]" data-testid="adjustment-row">
                        <Input label={i === 0 ? "Label" : undefined} aria-label="Adjustment label" size="sm" value={a.label} onChange={(x) => updateAdj(i, { label: x })} />
                        <InputNumber
                            label={i === 0 ? "Amount" : undefined}
                            aria-label="Adjustment amount in dollars"
                            size="sm"
                            step={1000}
                            value={a.amount}
                            formatOptions={{ style: "currency", currency: "USD", maximumFractionDigits: 0 }}
                            onChange={(n) => updateAdj(i, { amount: Number.isNaN(n) ? 0 : n })}
                        />
                        <InputNumber
                            label={i === 0 ? "Sq ft" : undefined}
                            aria-label="Adjustment area in square feet"
                            size="sm"
                            className="max-sm:row-start-2"
                            minValue={0}
                            value={a.sf ?? Number.NaN}
                            formatOptions={{ maximumFractionDigits: 0 }}
                            onChange={(n) => updateAdj(i, { sf: Number.isNaN(n) ? null : n })}
                        />
                        <Input
                            label={i === 0 ? "Basis / note" : undefined}
                            aria-label="Adjustment note"
                            size="sm"
                            className="max-sm:col-span-2 max-sm:row-start-2"
                            value={a.note ?? ""}
                            onChange={(x) => updateAdj(i, { note: x })}
                        />
                        <ButtonUtility
                            size="sm"
                            color="tertiary"
                            icon={Trash01}
                            tooltip="Remove"
                            aria-label={`Remove ${a.label || "adjustment"}`}
                            onClick={() => p.setAdjustments(p.adjustments.filter((_, j) => j !== i))}
                        />
                    </div>
                ))}
                <div>
                    <Button size="sm" color="secondary" iconLeading={Plus} onClick={() => p.setAdjustments([...p.adjustments, { label: "Garage/ADU", amount: 0, note: "" }])}>
                        Add adjustment
                    </Button>
                </div>
            </Fieldset>

            <Fieldset legend="Estimated prices">
                <EstimatedPrices a={p.a} adjustments={p.adjustments} />
            </Fieldset>

            <Fieldset legend="Calculation">
                <BasisCard b={v.bases.above_grade} primary={v.primary_basis === "above_grade"} />
                <BasisCard b={v.bases.total_finished} primary={v.primary_basis === "total_finished"} />
                {v.warnings.map((w) => (
                    <Callout key={w} tone="warning">
                        {w}
                    </Callout>
                ))}
            </Fieldset>
        </div>
    );
}

/**
 * The client workbook's "ESTIMATED PRICES" block (LOT, FIN SF, AVERAGE, MEDIAN, HIGH, LOW, MEAN VALUE,
 * Appreciation, ADD For Garage/ADU, SF, TOTAL), turned on its side to fit the panel: one column per method.
 */
function EstimatedPrices({ a, adjustments }: { a: Analysis; adjustments: Adjustment[] }) {
    const v = a.valuation;
    const order = [v.primary_basis, ...(["total_finished", "above_grade"] as const).filter((b) => b !== v.primary_basis)];
    const cols = order.map((k) => (k ? v.bases[k] : undefined)).filter((b): b is BasisResult => !!b?.available);
    const addSf = adjustments.reduce((s, x) => s + (x.sf ?? 0), 0);
    if (!cols.length) return <p className="text-sm text-tertiary">Not enough data for an estimate yet.</p>;
    const rows: { label: string; value: (b: BasisResult) => string; strong?: boolean }[] = [
        { label: "Lot", value: () => (a.subject.lot_sf ? `${a.subject.lot_sf.toLocaleString()} sf` : "—") },
        { label: "Fin sf (subject)", value: (b) => `${b.subject_area?.toLocaleString() ?? "—"} sf` },
        { label: "Average", value: (b) => money(b.indicated.mean) },
        { label: "Median", value: (b) => money(b.indicated.median) },
        { label: "High", value: (b) => money(b.indicated.high) },
        { label: "Low", value: (b) => money(b.indicated.low) },
        { label: v.point_statistic === "mean" ? "Mean value" : "Mean value (median $/sf)", value: (b) => money(b.base_value), strong: true },
        { label: `Appreciation (${v.appreciation_pct}%)`, value: (b) => money(b.appreciation_amount) },
        { label: "Add for garage/ADU", value: (b) => money(b.adjustments_total) },
        { label: "SF", value: () => (addSf ? addSf.toLocaleString() : "—") },
    ];
    const short = (b: BasisResult) => (b.basis === "total_finished" ? "Total finished $/sf" : "Above-grade $/sf");
    return (
        <div className="overflow-hidden rounded-lg ring-1 ring-secondary">
            <table className="w-full text-sm tabular-nums">
                <caption className="sr-only">Estimated prices</caption>
                <thead>
                    <tr className="bg-warning-secondary text-primary">
                        <th scope="col" className="px-3 py-2 text-left text-xs font-semibold">
                            Estimated prices
                        </th>
                        {cols.map((b) => (
                            <th key={b.basis} scope="col" className="px-3 py-2 text-right text-xs font-semibold">
                                {short(b)}
                                {b.basis === v.primary_basis && <span className="block font-normal text-tertiary">headline</span>}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-secondary bg-warning-primary">
                    {rows.map((r) => (
                        <tr key={r.label}>
                            <th scope="row" className="px-3 py-1.5 text-left font-medium text-secondary">
                                {r.label}
                            </th>
                            {cols.map((b) => (
                                <td key={b.basis} className={cx("px-3 py-1.5 text-right", r.strong ? "font-medium text-primary" : "text-secondary")}>
                                    {r.value(b)}
                                </td>
                            ))}
                        </tr>
                    ))}
                    <tr className="bg-warning-secondary">
                        <th scope="row" className="px-3 py-2 text-left font-semibold text-primary">
                            Total
                        </th>
                        {cols.map((b) => (
                            <td key={b.basis} className="px-3 py-2 text-right font-semibold text-primary">
                                {money(b.estimate)}
                            </td>
                        ))}
                    </tr>
                </tbody>
            </table>
        </div>
    );
}

function BasisCard({ b, primary }: { b: BasisResult; primary: boolean }) {
    return (
        <section
            aria-label={b.label}
            className={cx("flex flex-col gap-3 rounded-xl p-4 ring-1 ring-inset", primary ? "bg-brand-primary_alt ring-brand" : "bg-primary ring-secondary")}
        >
            <div className="flex items-center gap-2">
                <h3 className="flex-1 text-sm font-semibold text-primary">{b.label}</h3>
                {primary && (
                    <Badge type="pill-color" color="brand" size="sm">
                        Headline
                    </Badge>
                )}
            </div>
            {!b.available ? (
                <p className="text-sm text-tertiary">{b.reason_unavailable}</p>
            ) : (
                <>
                    <table className="w-full text-sm">
                        <caption className="sr-only">Indicated values</caption>
                        <thead>
                            <tr className="text-xs text-quaternary">
                                <th scope="col" className="py-1 text-left font-medium">
                                    Statistic
                                </th>
                                <th scope="col" className="py-1 text-right font-medium">
                                    $/sf
                                </th>
                                <th scope="col" className="py-1 text-right font-medium">
                                    × {b.subject_area?.toLocaleString()} sf
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-secondary">
                            {(["mean", "median", "high", "low"] as const).map((k) => (
                                <tr key={k}>
                                    <th scope="row" className="py-1.5 text-left font-medium text-secondary">
                                        {k === "mean" ? "Average" : k[0].toUpperCase() + k.slice(1)}
                                    </th>
                                    <td className="py-1.5 text-right text-tertiary tabular-nums">${b.ppsf[k]?.toFixed(2)}</td>
                                    <td className="py-1.5 text-right font-medium text-primary tabular-nums">{money(b.indicated[k])}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <ol className="flex list-decimal flex-col gap-1 pl-5 text-xs text-tertiary">
                        {b.lines.map((l) => (
                            <li key={l}>{l}</li>
                        ))}
                    </ol>
                    {b.warnings.map((w) => (
                        <p key={w} className="text-xs text-warning-primary">
                            {w}
                        </p>
                    ))}
                </>
            )}
        </section>
    );
}
