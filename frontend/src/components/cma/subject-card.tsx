"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, ClockRewind, Home02 } from "@untitledui/icons";
import { Table } from "@/components/application/table/table";
import { Badge, BadgeWithDot } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { money, num } from "@/lib/format";
import type { Analysis } from "@/lib/types";

export function SubjectCard({ a }: { a: Analysis }) {
    const s = a.subject;
    const [showHistory, setShowHistory] = useState(false);
    const facts: [string, string][] = [
        ["Type", a.subject_label],
        ["Style", s.style ?? "—"],
        ["Built", s.year_built ? `${s.year_built}${s.year_remodeled ? ` (remodel ${s.year_remodeled})` : ""}` : "—"],
        ["Beds / baths", `${s.beds ?? "—"} / ${s.baths_label ?? "—"}`],
        ["Above-grade", s.above_grade_sf ? `${num(s.above_grade_sf)} sf` : "not recorded"],
        ["Total finished", s.total_finished_sf ? `${num(s.total_finished_sf)} sf (${s.total_finished_source})` : "not recorded"],
        ["Basement", `${s.basement ?? "—"}${s.rec_room_sf ? ` · rec room ${num(s.rec_room_sf)} sf` : ""}`],
        ["Lot", s.lot_sf ? `${num(s.lot_sf)} sf` : "—"],
        ["Condition / grade", `${s.condition ?? "—"} / ${s.grade ?? "—"}`],
        ["Garage", s.garage_evidence ?? "not recorded"],
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
                            </Badge>
                        )}
                        <BadgeWithDot type="modern" color="brand" size="sm">
                            County record
                        </BadgeWithDot>
                    </div>
                </div>
            </header>

            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 p-5 md:grid-cols-3 xl:grid-cols-5">
                {facts.map(([k, v]) => (
                    <div key={k} className="flex min-w-0 flex-col gap-0.5">
                        <dt className="text-xs font-medium text-quaternary">{k}</dt>
                        <dd className="text-sm font-medium text-primary">{v}</dd>
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
