"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ChevronRight } from "@untitledui/icons";
import type { Selection, SortDescriptor } from "react-aria-components";
import { Table, TableCard } from "@/components/application/table/table";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { ProgressBarBase } from "@/components/base/progress-indicators/progress-indicators";
import { money, num, ppsf } from "@/lib/format";
import type { Comp } from "@/lib/types";
import { cx } from "@/utils/cx";

type Col = { id: string; label: string; tooltip?: string; value: (c: Comp) => number | string | null; text?: boolean };

const COLS: Col[] = [
    { id: "rank", label: "Rank", value: (c) => c.rank },
    { id: "score", label: "Score", tooltip: "Similarity 0–100 from the ranking factors. Sale price is never a factor.", value: (c) => c.score },
    { id: "address", label: "Address", text: true, value: (c) => c.address },
    { id: "date", label: "Sold", text: true, value: (c) => c.sale.sale_date },
    { id: "price", label: "Price", value: (c) => c.sale.price },
    { id: "ag", label: "Above-grade sf", tooltip: "County assessor above-grade living area (SFLA).", value: (c) => c.property.above_grade_sf },
    { id: "ppsf", label: "$/AG sf", value: (c) => c.ppsf_above_grade },
    { id: "tf", label: "Total fin. sf", tooltip: "Total finished area from the listing (agent input). Not in county records.", value: (c) => c.total_finished_sf },
    { id: "ppsf_tf", label: "$/TF sf", value: (c) => c.ppsf_total_finished },
    { id: "beds", label: "Beds", value: (c) => c.property.beds },
    { id: "baths", label: "Baths", value: (c) => (c.property.full_baths ?? 0) + 0.5 * (c.property.half_baths ?? 0) },
    { id: "year", label: "Built", value: (c) => c.property.year_built },
    { id: "lot", label: "Lot sf", value: (c) => c.property.lot_sf },
    { id: "dist", label: "Miles", value: (c) => c.distance_miles },
];

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
const LIMIT = 15;

interface Props {
    comps: Comp[];
    /** All sales that passed the rules; the API returns the highest-ranked of them. */
    eligibleCount: number;
    selectedIds: number[];
    highlighted: number | null;
    busy: boolean;
    manual: boolean;
    maxResults: number;
    onHighlight: (id: number) => void;
    onToggle: (id: number, include: boolean) => void;
    onResetSelection: () => void;
    onTotalFinished: (pin: string, value: number | null) => void;
    onOpenDetail: (c: Comp) => void;
}

export function CompTable(p: Props) {
    const [sort, setSort] = useState<SortDescriptor>({ column: "rank", direction: "ascending" });
    const [showAll, setShowAll] = useState(false);

    const rows = useMemo(() => {
        const col = COLS.find((c) => c.id === sort.column) ?? COLS[0];
        const f = sort.direction === "ascending" ? 1 : -1;
        return [...p.comps].sort((a, b) => {
            const va = col.value(a);
            const vb = col.value(b);
            if (va === null || va === undefined) return 1;
            if (vb === null || vb === undefined) return -1;
            return f * (col.text ? collator.compare(String(va), String(vb)) : (va as number) - (vb as number));
        });
    }, [p.comps, sort]);

    const visible = showAll ? rows : rows.filter((c) => c.rank <= LIMIT || p.selectedIds.includes(c.sale_id) || c.sale_id === p.highlighted);
    const selectedOrder = new Map(
        p.comps
            .filter((c) => c.selected)
            .sort((a, b) => a.rank - b.rank)
            .map((c, i) => [c.sale_id, i + 1]),
    );

    // Bring the highlighted comp (e.g. clicked on the map) into view.
    useEffect(() => {
        if (p.highlighted === null) return;
        document.getElementById(`comp-row-${p.highlighted}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }, [p.highlighted]);

    const onSelectionChange = (keys: Selection) => {
        const next = keys === "all" ? new Set(visible.map((c) => c.sale_id)) : new Set([...keys].map(Number));
        const prev = new Set(p.selectedIds);
        for (const c of visible) {
            if (next.has(c.sale_id) !== prev.has(c.sale_id)) p.onToggle(c.sale_id, next.has(c.sale_id));
        }
    };

    return (
        <TableCard.Root size="sm" data-testid="comp-table">
            <TableCard.Header
                title="Comparable sales"
                badge={p.comps.length < p.eligibleCount ? `top ${p.comps.length} of ${p.eligibleCount} eligible` : `${p.comps.length} eligible`}
                description="Ranked by similarity to the subject; ranking never uses price. Checked rows are used in the valuation. Click a row to find it on the map."
                contentTrailing={
                    p.manual ? (
                        <Button size="sm" color="secondary" onClick={p.onResetSelection}>
                            Reset to the top {p.maxResults}
                        </Button>
                    ) : (
                        <Badge type="pill-color" color="brand" size="md">
                            Top {p.maxResults} selected automatically
                        </Badge>
                    )
                }
            />
            <Table
                aria-label="Eligible comparable sales"
                aria-busy={p.busy}
                selectionMode="multiple"
                selectionBehavior="toggle"
                selectedKeys={new Set(p.selectedIds.filter((id) => visible.some((c) => c.sale_id === id)))}
                onSelectionChange={onSelectionChange}
                sortDescriptor={sort}
                onSortChange={setSort}
                onRowAction={(key) => p.onHighlight(Number(key))}
                className={cx(p.busy && "opacity-70 transition-opacity")}
            >
                <Table.Header>
                    {COLS.map((c) => (
                        <Table.Head key={c.id} id={c.id} label={c.label} tooltip={c.tooltip} allowsSorting isRowHeader={c.id === "address"} className="px-3" />
                    ))}
                    <Table.Head id="why" label="Detail" className="px-3" />
                </Table.Header>
                <Table.Body items={visible.map((c) => ({ ...c, id: c.sale_id }))}>
                    {(c) => (
                        <Table.Row
                            id={c.sale_id}
                            textValue={c.address}
                            data-highlighted={p.highlighted === c.sale_id || undefined}
                            data-comp-no={selectedOrder.get(c.sale_id)}
                            className={cx("h-auto", p.highlighted === c.sale_id && "bg-warning-primary hover:bg-warning-primary")}
                        >
                            <Table.Cell className="px-3 tabular-nums">
                                <span id={`comp-row-${c.sale_id}`} className="flex items-center gap-1.5">
                                    {c.rank}
                                    {c.selected && (
                                        <span
                                            className="flex size-5 items-center justify-center rounded-full bg-brand-solid text-[11px] font-bold text-white"
                                            aria-label={`Comp ${selectedOrder.get(c.sale_id)}`}
                                        >
                                            {selectedOrder.get(c.sale_id)}
                                        </span>
                                    )}
                                </span>
                            </Table.Cell>
                            <Table.Cell className="px-3">
                                <div className="flex w-16 flex-col gap-1">
                                    <span className="text-xs font-semibold text-primary tabular-nums">{c.score.toFixed(0)}</span>
                                    <ProgressBarBase value={c.score} />
                                </div>
                            </Table.Cell>
                            <Table.Cell className="min-w-80 px-3 py-2.5">
                                <div className="flex flex-col gap-0.5">
                                    <span className="font-medium text-primary">{c.address}</span>
                                    <span className="line-clamp-2 text-xs text-tertiary" title={c.reason}>
                                        {c.reason}
                                    </span>
                                    {c.warnings.map((w) => (
                                        <span key={w} className="inline-flex items-center gap-1 text-xs text-warning-primary">
                                            <AlertTriangle className="size-3.5" aria-hidden="true" />
                                            {w}
                                        </span>
                                    ))}
                                </div>
                            </Table.Cell>
                            <Table.Cell className="px-3 whitespace-nowrap">{c.sale.sale_date}</Table.Cell>
                            <Table.Cell className="px-3 font-medium text-primary tabular-nums">{money(c.sale.price)}</Table.Cell>
                            <Table.Cell className="px-3 tabular-nums">{num(c.property.above_grade_sf)}</Table.Cell>
                            <Table.Cell className="px-3 tabular-nums">{ppsf(c.ppsf_above_grade)}</Table.Cell>
                            <Table.Cell className="px-3">
                                <TfInput comp={c} onCommit={p.onTotalFinished} />
                            </Table.Cell>
                            <Table.Cell className="px-3 tabular-nums">{ppsf(c.ppsf_total_finished)}</Table.Cell>
                            <Table.Cell className="px-3 tabular-nums">{c.property.beds ?? "—"}</Table.Cell>
                            <Table.Cell className="px-3 tabular-nums">{c.property.baths_label ?? "—"}</Table.Cell>
                            <Table.Cell className="px-3 tabular-nums">{c.property.year_built ?? "—"}</Table.Cell>
                            <Table.Cell className="px-3 tabular-nums">{num(c.property.lot_sf)}</Table.Cell>
                            <Table.Cell className="px-3 tabular-nums">{c.distance_miles?.toFixed(2) ?? "—"}</Table.Cell>
                            <Table.Cell className="px-3">
                                <ButtonUtility
                                    size="xs"
                                    color="tertiary"
                                    icon={ChevronRight}
                                    tooltip="Factor detail and source record"
                                    aria-label={`Details for ${c.address}`}
                                    onClick={() => p.onOpenDetail(c)}
                                />
                            </Table.Cell>
                        </Table.Row>
                    )}
                </Table.Body>
            </Table>
            {(rows.length > visible.length || showAll) && (
                <div className="flex justify-center border-t border-secondary px-4 py-3">
                    <Button size="sm" color="link-color" onClick={() => setShowAll(!showAll)}>
                        {showAll ? `Show the top ${LIMIT} and selected` : `Show all ${rows.length} ranked sales`}
                    </Button>
                </div>
            )}
        </TableCard.Root>
    );
}

/** Total finished sq ft (agent input from the listing), saved on blur or Enter. */
function TfInput({ comp, onCommit }: { comp: Comp; onCommit: (pin: string, v: number | null) => void }) {
    const [v, setV] = useState(comp.total_finished_sf?.toString() ?? "");
    useEffect(() => {
        setV(comp.total_finished_sf?.toString() ?? "");
    }, [comp.total_finished_sf]);
    const commit = () => {
        const n = v.trim() === "" ? null : Number(v.replace(/,/g, ""));
        if (n !== null && (!Number.isFinite(n) || n < 100)) return;
        if (n !== comp.total_finished_sf) onCommit(comp.pin, n);
    };
    return (
        <input
            className="w-20 rounded-md bg-primary px-2 py-1 text-sm text-primary tabular-nums shadow-xs ring-1 ring-primary outline-hidden ring-inset placeholder:text-placeholder focus:ring-2 focus:ring-brand"
            inputMode="numeric"
            value={v}
            placeholder="enter"
            title={comp.total_finished_source ? `Source: ${comp.total_finished_source}` : "Total finished sq ft from the listing (agent input)"}
            aria-label={`Total finished square feet for ${comp.address}`}
            onChange={(e) => setV(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
                e.stopPropagation(); // keep typing inside the input (the table grid handles arrow/space keys)
                if (e.key === "Enter") (e.target as HTMLInputElement).blur();
            }}
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
        />
    );
}
