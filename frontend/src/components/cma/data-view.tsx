"use client";

/* eslint-disable @typescript-eslint/no-explicit-any */
import { Database02, FileShield02, LinkExternal01, RefreshCcw05 } from "@untitledui/icons";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { Table, TableCard } from "@/components/application/table/table";
import { Badge, BadgeWithDot } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { useCma } from "@/providers/cma-provider";
import { Callout } from "./callout";
import { PageHeader } from "./page-header";

const STATUS: Record<string, { label: string; color: "brand" | "success" | "warning" | "gray" | "error" }> = {
    county: { label: "County record", color: "success" },
    partial: { label: "Partly in county data", color: "warning" },
    agent_or_mls: { label: "Agent input / MLS", color: "brand" },
    calculated: { label: "Calculated", color: "gray" },
    calculated_with_input: { label: "Calculated (needs agent input)", color: "warning" },
    client_decision: { label: "Client decision", color: "error" },
};

const Stat = ({ label, value }: { label: string; value: React.ReactNode }) => (
    <div className="flex flex-col gap-1 rounded-xl bg-primary px-4 py-4 shadow-xs ring-1 ring-secondary">
        <dt className="text-sm font-medium text-tertiary">{label}</dt>
        <dd className="text-display-xs font-semibold text-primary tabular-nums">{value}</dd>
    </div>
);

export function DataView() {
    const { meta } = useCma();
    if (!meta) return <LoadingIndicator type="line-spinner" size="md" label="Loading…" />;
    const lr = meta.data.last_refresh;
    const counts = (lr?.counts ?? {}) as Record<string, any>;

    return (
        <div className="flex flex-col gap-6">
            <PageHeader
                crumb="Data & sources"
                title="Data & sources"
                description="Where every figure comes from, when it was last refreshed, and which workbook fields need another source."
            />

            <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <Stat label="Parcels" value={meta.data.parcels.toLocaleString()} />
                <Stat label="Sales stored" value={meta.data.sales.toLocaleString()} />
                <Stat label="Latest sale" value={meta.data.latest_sale_date ?? "—"} />
                <Stat label="Last refresh" value={counts.timings_seconds?.total ? `${counts.timings_seconds.total} s` : "—"} />
            </dl>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <section className="flex flex-col gap-3 rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary">
                    <div className="flex items-center gap-3">
                        <FeaturedIcon icon={Database02} color="brand" theme="light" size="md" />
                        <h2 className="text-md font-semibold text-primary">Source</h2>
                        <BadgeWithDot type="modern" color="warning" size="sm">
                            Public records, not MLS
                        </BadgeWithDot>
                    </div>
                    <p className="text-sm text-secondary">{meta.provider.label}</p>
                    <p className="text-sm text-tertiary">{meta.provider.attribution}</p>
                    <p className="text-sm text-tertiary">
                        An approved MLS feed or another licensed provider can be added as a separate provider without changing the comp or pricing logic.
                    </p>
                    <ul className="flex flex-col gap-1">
                        {meta.provider.datasets.map((d) => (
                            <li key={d.key}>
                                <Button href={d.url} target="_blank" rel="noreferrer" color="link-color" size="sm" iconTrailing={LinkExternal01}>
                                    {d.title}
                                </Button>
                            </li>
                        ))}
                    </ul>
                </section>

                <section className="flex flex-col gap-3 rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary">
                    <div className="flex items-center gap-3">
                        <FeaturedIcon icon={RefreshCcw05} color="gray" theme="modern" size="md" />
                        <h2 className="text-md font-semibold text-primary">Last refresh</h2>
                    </div>
                    {lr ? (
                        <dl className="grid grid-cols-[max-content_1fr] gap-x-6 gap-y-2 text-sm">
                            <dt className="text-tertiary">Finished</dt>
                            <dd className="text-primary">{lr.finished_at?.replace("T", " ").slice(0, 19)} UTC</dd>
                            <dt className="text-tertiary">ZIP codes</dt>
                            <dd className="text-primary">{lr.zips}</dd>
                            <dt className="text-tertiary">Duplicate rows collapsed</dt>
                            <dd className="text-primary">{counts.sales?.duplicate_rows_collapsed ?? "—"}</dd>
                            <dt className="text-tertiary">Multi-parcel sales flagged</dt>
                            <dd className="text-primary">{counts.sales?.multi_parcel_sales ?? "—"}</dd>
                        </dl>
                    ) : (
                        <Callout tone="warning" title="No data loaded">
                            Run <code>scripts\refresh.ps1</code> (or <code>python -m app.ingest.refresh</code> in the backend).
                        </Callout>
                    )}
                    <p className="text-xs text-tertiary">The county updates its extract daily. Re-running the refresh only updates what changed and never deletes sales.</p>
                </section>
            </div>

            <Callout tone="warning" title="Terms of use">
                <p>{meta.provider.terms_summary}</p>
                <a href={meta.provider.terms_url} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 font-semibold text-brand-secondary hover:underline">
                    <FileShield02 className="size-4" aria-hidden="true" />
                    {meta.provider.terms_url}
                </a>
            </Callout>

            <TableCard.Root size="sm">
                <TableCard.Header title="Workbook fields and where they come from" badge={`${meta.field_map.length} fields`} />
                <Table aria-label="Field availability for the client's CMA workbook" size="sm">
                    <Table.Header>
                        <Table.Head id="field" label="Workbook field" isRowHeader />
                        <Table.Head id="status" label="Availability" />
                        <Table.Head id="source" label="Source" />
                        <Table.Head id="note" label="Note" />
                    </Table.Header>
                    <Table.Body items={meta.field_map.map((f, i) => ({ ...f, id: i }))}>
                        {(f) => (
                            <Table.Row id={f.id} className="h-auto">
                                <Table.Cell className="py-3 align-top font-medium text-primary">{f.workbook}</Table.Cell>
                                <Table.Cell className="py-3 align-top">
                                    <Badge type="pill-color" color={STATUS[f.status]?.color ?? "gray"} size="sm">
                                        {STATUS[f.status]?.label ?? f.status}
                                    </Badge>
                                </Table.Cell>
                                <Table.Cell className="py-3 align-top text-xs">{f.source}</Table.Cell>
                                <Table.Cell className="py-3 align-top text-xs">{f.note}</Table.Cell>
                            </Table.Row>
                        )}
                    </Table.Body>
                </Table>
            </TableCard.Root>
        </div>
    );
}
