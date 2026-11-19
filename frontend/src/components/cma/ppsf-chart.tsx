"use client";

import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartTooltipContent } from "@/components/application/charts/charts-base";
import type { Analysis } from "@/lib/types";

/** Price per square foot of the comps used, with the average and median the estimate is built from. */
export function PpsfChart({ a, highlighted, onHighlight }: { a: Analysis; highlighted: number | null; onHighlight: (id: number) => void }) {
    const v = a.valuation;
    const basis = v.primary_basis ? v.bases[v.primary_basis] : null;
    if (!basis || !basis.available || basis.comps.length === 0) return null;
    const data = basis.comps.map((c, i) => ({ name: `Comp ${i + 1}`, label: c.label, ppsf: Math.round(c.ppsf * 100) / 100, sale_id: c.sale_id }));
    const mean = basis.ppsf.mean ?? 0;
    const median = basis.ppsf.median ?? 0;

    return (
        <section aria-labelledby="ppsf-heading" className="flex flex-col gap-3 rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary">
            <div className="flex flex-wrap items-baseline gap-x-3">
                <h3 id="ppsf-heading" className="text-sm font-semibold text-primary">
                    $/sf of the comps used · {basis.label}
                </h3>
                <p className="text-xs text-tertiary">
                    average ${mean.toFixed(2)} · median ${median.toFixed(2)}
                </p>
            </div>
            <div className="h-48" role="img" aria-label={`Bar chart of price per square foot: ${data.map((d) => `${d.name} $${d.ppsf}`).join(", ")}`}>
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                        <CartesianGrid vertical={false} stroke="currentColor" className="text-utility-neutral-100" />
                        <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 12 }} className="text-tertiary" />
                        <YAxis
                            tickLine={false}
                            axisLine={false}
                            width={48}
                            tick={{ fontSize: 12 }}
                            tickFormatter={(x: number) => `$${x}`}
                            domain={[(min: number) => Math.floor((min * 0.9) / 10) * 10, "auto"]}
                        />
                        <Tooltip
                            cursor={{ fill: "var(--color-bg-secondary)" }}
                            content={<ChartTooltipContent />}
                            formatter={(value) => `$${Number(value).toFixed(2)} / sf`}
                            labelFormatter={(label, payload) => payload?.[0]?.payload?.label ?? label}
                        />
                        <ReferenceLine y={mean} stroke="var(--color-fg-brand-secondary)" strokeDasharray="4 4" label={{ value: "avg", position: "right", fontSize: 11 }} />
                        <Bar dataKey="ppsf" name="$/sf" radius={[6, 6, 0, 0]} maxBarSize={48} onClick={(d) => onHighlight((d as unknown as { sale_id: number }).sale_id)}>
                            {data.map((d) => (
                                <Cell
                                    key={d.sale_id}
                                    cursor="pointer"
                                    fill={d.sale_id === highlighted ? "var(--color-fg-warning-secondary)" : "var(--color-fg-brand-secondary)"}
                                />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </section>
    );
}
