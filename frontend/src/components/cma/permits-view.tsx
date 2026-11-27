"use client";

import { useEffect, useMemo, useState } from "react";
import { LinkExternal01, XClose } from "@untitledui/icons";
import dynamic from "next/dynamic";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";
import { Button } from "@/components/base/buttons/button";
import { Select } from "@/components/base/select/select";
import { Toggle } from "@/components/base/toggle/toggle";
import { type AreaFilter, api } from "@/lib/api";
import type { PermitSearch, PermitStage } from "@/lib/types";
import { AreaFilters, hasAreaFilter } from "./area-filters";
import { Callout } from "./callout";
import { PageHeader } from "./page-header";
import { PermitStageBadge, STAGE_LABEL } from "./permit-badge";

const PermitsMap = dynamic(() => import("./permits-map"), {
    ssr: false,
    loading: () => <div className="h-[28rem] animate-pulse rounded-xl bg-secondary" aria-hidden="true" />,
});

const STAGES: (PermitStage | "all")[] = ["active", "pending", "completed", "stale", "inactive", "all"];
const TABLE_LIMIT = 500;

function Stat({ label, value, hint }: { label: string; value: number | string; hint?: string }) {
    return (
        <div className="flex flex-col gap-1 rounded-xl bg-primary px-4 py-4 shadow-xs ring-1 ring-secondary">
            <dt className="text-sm font-medium text-tertiary">{label}</dt>
            <dd className="text-display-xs font-semibold text-primary tabular-nums">{value}</dd>
            {hint && <dd className="text-xs text-quaternary">{hint}</dd>}
        </div>
    );
}

/** Permit status in an area: what is under construction, in review or finished (Fairfax County PLUS). */
export function PermitsView() {
    const [area, setArea] = useState<AreaFilter>({ subdivision: null, block: null, streets: [] });
    const [resetKey, setResetKey] = useState(0);
    const [stage, setStage] = useState<PermitStage | "all">("active");
    const [kind, setKind] = useState<"all" | "building" | "site">("all");
    const [newOnly, setNewOnly] = useState(false);
    const [data, setData] = useState<PermitSearch | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const key = JSON.stringify([area, stage, kind, newOnly]);
    useEffect(() => {
        const ctrl = new AbortController();
        setLoading(true);
        api.permits({ ...area, stage: stage === "all" ? null : stage, kind: kind === "all" ? null : kind, new_only: newOnly }, ctrl.signal)
            .then((d) => {
                setData(d);
                setError("");
            })
            .catch((e: Error) => {
                if (e.name !== "AbortError") setError(e.message);
            })
            .finally(() => {
                if (!ctrl.signal.aborted) setLoading(false);
            });
        return () => ctrl.abort();
    }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

    const s = data?.summary;
    const where = area.subdivision
        ? `${area.subdivision}${area.block ? `, block ${area.block}` : ""}${area.streets?.length ? ` · ${area.streets.length === 1 ? area.streets[0] : `${area.streets.length} streets`}` : ""}`
        : area.streets?.length
          ? area.streets.length === 1
              ? area.streets[0]
              : `${area.streets.length} streets`
          : "all loaded ZIP codes";
    const rows = useMemo(() => data?.results.slice(0, TABLE_LIMIT) ?? [], [data]);

    return (
        <div className="flex flex-col gap-6">
            <PageHeader
                title="Permits & development"
                description="Building permits and site / land-development records from Fairfax County PLUS for the chosen subdivision, block or streets: what is under construction, in review or finished. Refreshed daily with the county data."
            />

            <section aria-label="Filters" className="flex flex-col gap-4 rounded-xl bg-primary p-4 shadow-xs ring-1 ring-secondary md:p-5">
                <AreaFilters value={area} onChange={setArea} resetKey={resetKey} shortcut={false} />
                <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
                    <div className="flex flex-col gap-1.5">
                        <span id="stage-label" className="text-sm font-medium text-secondary">
                            Status
                        </span>
                        <ButtonGroup
                            aria-labelledby="stage-label"
                            size="sm"
                            disallowEmptySelection
                            selectedKeys={new Set([stage])}
                            onSelectionChange={(keys) => {
                                const k = [...keys][0];
                                if (k) setStage(k as PermitStage | "all");
                            }}
                        >
                            {STAGES.map((st) => (
                                <ButtonGroupItem key={st} id={st}>
                                    {st === "all" ? "All" : STAGE_LABEL[st]}
                                </ButtonGroupItem>
                            ))}
                        </ButtonGroup>
                    </div>
                    <Select
                        label="Record type"
                        className="w-60"
                        selectedKey={kind}
                        onSelectionChange={(k) => setKind((k as typeof kind) ?? "all")}
                        items={[
                            { id: "all", label: "Building permits and site records" },
                            { id: "building", label: "Building permits" },
                            { id: "site", label: "Site / land development" },
                        ]}
                    >
                        {(item) => <Select.Item id={item.id}>{item.label}</Select.Item>}
                    </Select>
                    <Toggle label="New construction only" hint="New houses, infill lot grading, subdivisions" isSelected={newOnly} onChange={setNewOnly} />
                    {hasAreaFilter(area) && (
                        <Button
                            size="sm"
                            color="secondary"
                            iconLeading={XClose}
                            onClick={() => {
                                setArea({ subdivision: null, block: null, streets: [] });
                                setResetKey((k) => k + 1);
                            }}
                        >
                            Clear area
                        </Button>
                    )}
                </div>
            </section>

            {error && (
                <Callout tone="error" title="Could not load permits" role="alert">
                    {error}
                </Callout>
            )}

            {data && s && (
                <>
                    <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
                        <Stat label="Records shown" value={data.total.toLocaleString()} hint={where} />
                        <Stat label="Parcels" value={s.parcels.toLocaleString()} />
                        <Stat
                            label="New construction"
                            value={Object.values(s.new_construction).reduce((a, b) => a + (b ?? 0), 0)}
                            hint={s.new_construction.active ? `${s.new_construction.active} under way` : undefined}
                        />
                        <Stat
                            label="Top type"
                            value={Object.keys(s.by_type)[0] ?? "—"}
                            hint={Object.keys(s.by_type)[0] ? `${Object.values(s.by_type)[0]} records` : undefined}
                        />
                    </dl>

                    <PermitsMap permits={data.results} />

                    <section
                        aria-labelledby="permits-table-heading"
                        className="flex flex-col gap-3 rounded-xl bg-primary p-4 shadow-xs ring-1 ring-secondary md:p-5"
                    >
                        <div className="flex flex-wrap items-center gap-2">
                            <h2 id="permits-table-heading" className="flex-1 text-md font-semibold text-primary">
                                {data.total.toLocaleString()} {stage === "all" ? "" : `${STAGE_LABEL[stage as PermitStage].toLowerCase()} `}records · {where}
                            </h2>
                            {loading && <LoadingIndicator type="line-simple" size="sm" />}
                        </div>
                        {Object.keys(s.by_type).length > 0 && (
                            <p className="text-xs text-tertiary">
                                {Object.entries(s.by_type)
                                    .slice(0, 6)
                                    .map(([t, n]) => `${t} ${n}`)
                                    .join(" · ")}
                            </p>
                        )}
                        {data.total === 0 ? (
                            <p className="text-sm text-tertiary">No permits match these filters.</p>
                        ) : (
                            <div className="overflow-x-auto rounded-lg ring-1 ring-secondary">
                                <table className="w-full min-w-[56rem] text-sm">
                                    <caption className="sr-only">Permits</caption>
                                    <thead className="bg-secondary text-xs text-tertiary">
                                        <tr>
                                            {["Address", "Type", "Status", "Submitted", "Issued / approved", "Closed", "Record"].map((h) => (
                                                <th key={h} scope="col" className="px-3 py-2 text-left font-medium whitespace-nowrap">
                                                    {h}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-secondary">
                                        {rows.map((p) => (
                                            <tr key={`${p.kind}-${p.record_id}`} className="align-top">
                                                <th scope="row" className="px-3 py-2 text-left font-medium text-primary">
                                                    {p.site_address ?? p.address ?? "—"}
                                                    {p.subdivision && <span className="block text-xs font-normal text-quaternary">{p.subdivision}</span>}
                                                </th>
                                                <td className="px-3 py-2 text-secondary">
                                                    {p.type}
                                                    {p.new_construction && <span className="block text-xs text-warning-primary">new construction</span>}
                                                    {p.project && <span className="block text-xs text-quaternary">{p.project}</span>}
                                                </td>
                                                <td className="px-3 py-2">
                                                    <PermitStageBadge stage={p.stage} />
                                                    <span className="mt-0.5 block text-xs text-quaternary">{p.status}</span>
                                                </td>
                                                <td className="px-3 py-2 whitespace-nowrap text-tertiary">{p.submitted ?? "—"}</td>
                                                <td className="px-3 py-2 whitespace-nowrap text-tertiary">{p.issued ?? "—"}</td>
                                                <td className="px-3 py-2 whitespace-nowrap text-tertiary">{p.closed ?? "—"}</td>
                                                <td className="px-3 py-2 whitespace-nowrap">
                                                    {p.link ? (
                                                        <a
                                                            href={p.link}
                                                            target="_blank"
                                                            rel="noreferrer"
                                                            className="inline-flex items-center gap-1 font-semibold text-brand-secondary hover:underline"
                                                        >
                                                            {p.record_id} <LinkExternal01 className="size-3" aria-hidden="true" />
                                                        </a>
                                                    ) : (
                                                        p.record_id
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                        {data.total > TABLE_LIMIT && (
                            <p className="text-xs text-tertiary">
                                Showing the {TABLE_LIMIT} most recent of {data.total.toLocaleString()}; the map shows all. Narrow the area or status to see the
                                rest.
                            </p>
                        )}
                        <p className="text-xs text-quaternary">
                            Source: Fairfax County PLUS (Building Records and Site Records, public view). Building permits are available from September 2022. An
                            issued or approved record with no closure after 3 years is shown as &ldquo;Old, not closed&rdquo; rather than under construction.
                        </p>
                    </section>
                </>
            )}
            {!data && !error && (
                <div className="flex justify-center py-16">
                    <LoadingIndicator type="line-spinner" size="md" label="Loading permits…" />
                </div>
            )}
        </div>
    );
}
