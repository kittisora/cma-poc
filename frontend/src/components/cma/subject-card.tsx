"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, ClockRewind, Edit05, Home02, HomeLine } from "@untitledui/icons";
import { Table } from "@/components/application/table/table";
import { Badge, BadgeWithDot } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { PROPERTY_TYPES, money, num } from "@/lib/format";
import type { Analysis, Meta, Property, SubjectPlan } from "@/lib/types";
import { PlannedHouseForm } from "./planned-house";

interface Props {
    a: Analysis;
    plan: SubjectPlan | null;
    options: Meta["subject_options"];
    onPlan: (p: SubjectPlan | null) => void;
}

export function SubjectCard({ a, plan, options, onPlan }: Props) {
    const s = a.subject;
    const [showHistory, setShowHistory] = useState(false);
    const [editing, setEditing] = useState(false);
    const planned = new Set(s.planned ?? []);
    // the subject as the county records it: the analysed subject with the planned values swapped back
    const county = { ...s, ...(a.county_values ?? {}) } as Property;
    const cv = (k: keyof Property, fmt: (v: never) => string = (v) => String(v)) =>
        county[k] === null || county[k] === undefined ? "not recorded" : fmt(county[k] as never);
    const facts: [string, string, string | null][] = [
        ["Type", a.subject_label, planned.has("property_type") ? (PROPERTY_TYPES[county.property_type] ?? county.property_type) : null],
        ["Style", s.style ?? "—", planned.has("style") ? cv("style") : null],
        [
            "Built",
            s.year_built ? `${s.year_built}${s.year_remodeled ? ` (remodel ${s.year_remodeled})` : ""}` : "—",
            planned.has("year_built") ? cv("year_built") : null,
        ],
        [
            "Beds / baths",
            `${s.beds ?? "—"} / ${s.baths_label ?? "—"}`,
            ["beds", "full_baths", "half_baths"].some((k) => planned.has(k)) ? `${county.beds ?? "—"} / ${county.full_baths ?? 0}/${county.half_baths ?? 0}` : null,
        ],
        ["Above-grade", s.above_grade_sf ? `${num(s.above_grade_sf)} sf` : "not recorded", planned.has("above_grade_sf") ? cv("above_grade_sf", (v: number) => `${num(v)} sf`) : null],
        [
            "Total finished",
            s.total_finished_sf ? `${num(s.total_finished_sf)} sf (${s.total_finished_source})` : "not recorded",
            planned.has("total_finished_sf") ? cv("total_finished_sf", (v: number) => `${num(v)} sf`) : null,
        ],
        ["Basement", `${s.basement ?? "—"}${s.rec_room_sf ? ` · rec room ${num(s.rec_room_sf)} sf` : ""}`, planned.has("basement") ? cv("basement") : null],
        ["Lot", s.lot_sf ? `${num(s.lot_sf)} sf` : "—", null],
        ["Condition / grade", `${s.condition ?? "—"} / ${s.grade ?? "—"}`, planned.has("condition") ? cv("condition") : null],
        ["Garage", s.garage_evidence ?? "not recorded", null],
    ];

    return (
        <section aria-labelledby="subject-heading" className="rounded-xl bg-primary shadow-xs ring-1 ring-secondary">
            <header className="flex flex-wrap items-start gap-3 border-b border-secondary p-5">
                <FeaturedIcon icon={Home02} color="gray" theme="modern" size="lg" />
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <h2 id="subject-heading" className="text-lg font-semibold text-primary">
                        {s.address}
                        <span className="font-normal text-tertiary">
                            {" "}
                            · {s.city} VA {s.zip}
                        </span>
                    </h2>
                    <div className="flex flex-wrap gap-2">
                        <Badge type="modern" color="gray" size="sm">
                            <span className="whitespace-pre">PARID {s.pin}</span>
                        </Badge>
                        {s.subdivision && (
                            <Badge type="modern" color="gray" size="sm">
                                {s.subdivision}
                                {s.block ? ` · Block ${s.block}` : ""}
                            </Badge>
                        )}
                        {planned.size > 0 ? (
                            <BadgeWithDot type="modern" color="warning" size="sm">
                                Planned house (agent input)
                            </BadgeWithDot>
                        ) : (
                            <BadgeWithDot type="modern" color="brand" size="sm">
                                County record
                            </BadgeWithDot>
                        )}
                    </div>
                </div>
                <Button size="sm" color={planned.size ? "secondary" : "primary"} iconLeading={planned.size ? Edit05 : HomeLine} onClick={() => setEditing(!editing)} aria-expanded={editing}>
                    {planned.size ? "Edit planned house" : "Describe house to sell / build"}
                </Button>
            </header>

            {editing && <PlannedHouseForm key={JSON.stringify(plan)} county={county} plan={plan} options={options} onApply={onPlan} onClose={() => setEditing(false)} />}

            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 p-5 md:grid-cols-3 xl:grid-cols-5">
                {facts.map(([k, v, countyValue]) => (
                    <div key={k} className="flex min-w-0 flex-col gap-0.5">
                        <dt className="text-xs font-medium text-quaternary">
                            {k}
                            {countyValue !== null && <span className="ml-1 text-warning-primary">· planned</span>}
                        </dt>
                        <dd className="text-sm font-medium text-primary">{v}</dd>
                        {countyValue !== null && <dd className="text-xs text-tertiary">County: {countyValue}</dd>}
                    </div>
                ))}
            </dl>

            {s.notes.length > 0 && (
                <ul className="flex flex-col gap-1 px-5 pb-4 text-xs text-tertiary">
                    {s.notes.map((n) => (
                        <li key={n}>{n}</li>
                    ))}
                </ul>
            )}

            <div className="border-t border-secondary px-5 py-3">
                <Button
                    color="link-gray"
                    size="sm"
                    iconLeading={ClockRewind}
                    iconTrailing={showHistory ? ChevronUp : ChevronDown}
                    aria-expanded={showHistory}
                    onClick={() => setShowHistory(!showHistory)}
                >
                    Recorded transfers of this property ({a.sale_history.length})
                </Button>
            </div>
            {showHistory && (
                <Table aria-label="Recorded transfers of the subject" size="sm">
                    <Table.Header>
                        <Table.Head id="date" label="Date" isRowHeader />
                        <Table.Head id="price" label="Price" />
                        <Table.Head id="validity" label="County validity" />
                        <Table.Head id="deed" label="Deed" />
                    </Table.Header>
                    <Table.Body items={a.sale_history.map((h) => ({ ...h, id: h.sale_id }))}>
                        {(h) => (
                            <Table.Row id={h.sale_id}>
                                <Table.Cell className="whitespace-nowrap">{h.sale_date}</Table.Cell>
                                <Table.Cell className="tabular-nums">{money(h.price)}</Table.Cell>
                                <Table.Cell>
                                    {h.validity ?? "—"}
                                    {h.multi_parcel ? " (multi-parcel)" : ""}
                                    {!h.in_latest_source ? " (kept from history)" : ""}
                                </Table.Cell>
                                <Table.Cell className="whitespace-nowrap">{h.deed_ref}</Table.Cell>
                            </Table.Row>
                        )}
                    </Table.Body>
                </Table>
            )}
        </section>
    );
}
