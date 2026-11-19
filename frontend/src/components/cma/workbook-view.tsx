"use client";

/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from "react";
import { CheckCircle, FileCheck02, XCircle } from "@untitledui/icons";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { Table, TableCard } from "@/components/application/table/table";
import { Badge, BadgeWithIcon } from "@/components/base/badges/badges";
import { InputNumber } from "@/components/base/input/input-number";
import { Select } from "@/components/base/select/select";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import { Callout } from "./callout";
import { PageHeader } from "./page-header";

const SEVERITY_COLOR: Record<string, "error" | "warning" | "gray" | "brand"> = { high: "error", medium: "warning", low: "gray", info: "brand" };

export function WorkbookView() {
    const [subject, setSubject] = useState("1009 New");
    const [finished, setFinished] = useState<number | null>(null);
    const [garage, setGarage] = useState<number | null>(null);
    const [apprec, setApprec] = useState(0);
    const [r, setR] = useState<Record<string, any> | null>(null);
    const [err, setErr] = useState("");

    useEffect(() => {
        const t = setTimeout(() => {
            api.regression({
                subject,
                finished_sf: finished ?? undefined,
                garage_adjustment: garage ?? undefined,
                appreciation_pct: apprec || 0,
            })
                .then((x) => {
                    setR(x);
                    setErr("");
                    if (finished === null) setFinished(Number(x.inputs.finished_sf));
                    if (garage === null) setGarage(Number(x.inputs.garage_adjustment));
                })
                .catch((e: Error) => setErr(e.message));
        }, 200);
        return () => clearTimeout(t);
    }, [subject, finished, garage, apprec]); // eslint-disable-line react-hooks/exhaustive-deps

    const header = (
        <PageHeader
            crumb="Workbook check"
            title="Workbook regression check"
            description={
                r
                    ? `Reproduces the client's “${r.workbook}” pricing method from its original inputs, then shows how the estimate changes under the app's own rules. Valuation date ${r.valuation_date}.`
                    : "Reproduces the client's workbook pricing method and compares it with the app's rules."
            }
        />
    );

    if (!r) {
        return (
            <>
                {header}
                {err ? <Callout tone="error">{err}</Callout> : <LoadingIndicator type="line-spinner" size="md" label="Loading…" />}
            </>
        );
    }
    const reg = r.regression;

    return (
        <div className="flex flex-col gap-6">
            {header}
            <Callout tone="info" title="Where the workbook's addresses are">
                {r.address_verification.result}
            </Callout>

            <section className="flex flex-col gap-4 rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary" aria-labelledby="wb-inputs">
                <h2 id="wb-inputs" className="text-sm font-semibold text-primary">
                    Inputs (editable assumptions for this workbook example only)
                </h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <Select
                        label="Subject"
                        selectedKey={subject}
                        onSelectionChange={(k) => {
                            setSubject(String(k));
                            setFinished(null);
                            setGarage(null);
                        }}
                        items={Object.keys(r.subjects).map((s) => ({ id: s, label: s }))}
                    >
                        {(item) => <Select.Item id={item.id}>{item.label}</Select.Item>}
                    </Select>
                    <InputNumber
                        label="Finished sq ft"
                        minValue={100}
                        value={finished ?? NaN}
                        formatOptions={{ maximumFractionDigits: 0 }}
                        onChange={(n) => !Number.isNaN(n) && setFinished(n)}
                    />
                    <InputNumber
                        label="Garage/ADU adjustment"
                        step={5000}
                        value={garage ?? NaN}
                        formatOptions={{ style: "currency", currency: "USD", maximumFractionDigits: 0 }}
                        onChange={(n) => !Number.isNaN(n) && setGarage(n)}
                    />
                    <InputNumber label="Appreciation %" step={0.1} value={apprec} onChange={(n) => setApprec(Number.isNaN(n) ? 0 : n)} />
                </div>
                <p className="text-xs text-tertiary">{r.inputs.garage_adjustment_note}</p>
                {reg.expected !== null ? (
                    <div role="status">
                        <BadgeWithIcon type="pill-color" color={reg.passed ? "success" : "error"} size="lg" iconLeading={reg.passed ? CheckCircle : XCircle}>
                            {reg.passed ? "Regression passed" : "Regression failed"}: workbook cell total {money(reg.expected, true)}, app {money(reg.actual, true)}
                        </BadgeWithIcon>
                    </div>
                ) : (
                    <p className="text-xs text-tertiary">Inputs differ from the workbook&apos;s, so there is no workbook total to compare against.</p>
                )}
            </section>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {r.variants.map((v: any) => (
                    <section key={v.variant} className="flex flex-col gap-3 rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary">
                        <div className="flex items-start gap-3">
                            <FeaturedIcon icon={FileCheck02} color={v.variant === "A" ? "brand" : "gray"} theme="light" size="md" />
                            <h2 className="text-sm font-semibold text-primary">
                                {v.variant}. {v.title}
                            </h2>
                        </div>
                        <p className="text-display-xs font-semibold text-primary">{money(v.estimate, true)}</p>
                        <p className="text-sm text-tertiary">{v.description}</p>
                        {v.lines && (
                            <ol className="flex list-decimal flex-col gap-1 pl-5 text-xs text-tertiary">
                                {v.lines.map((l: string) => (
                                    <li key={l}>{l}</li>
                                ))}
                            </ol>
                        )}
                        {v.comps && (
                            <table className="w-full text-xs">
                                <caption className="sr-only">Comps used</caption>
                                <thead>
                                    <tr className="text-quaternary">
                                        <th scope="col" className="py-1 text-left font-medium">
                                            Comp
                                        </th>
                                        <th scope="col" className="py-1 text-right font-medium">
                                            Sold
                                        </th>
                                        <th scope="col" className="py-1 text-right font-medium">
                                            Area
                                        </th>
                                        <th scope="col" className="py-1 text-right font-medium">
                                            $/sf
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-secondary text-secondary">
                                    {v.comps.map((c: any) => (
                                        <tr key={c.address ?? c.label}>
                                            <td className="py-1">{c.address ?? c.label}</td>
                                            <td className="py-1 text-right tabular-nums">{money(c.sold_price ?? c.price)}</td>
                                            <td className="py-1 text-right tabular-nums">{(c.area ?? 0).toLocaleString()}</td>
                                            <td className="py-1 text-right tabular-nums">${(c.ppsf ?? 0).toFixed(2)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                        {v.excluded && v.excluded.length > 0 && (
                            <details className="text-xs text-tertiary">
                                <summary className="cursor-pointer font-medium text-secondary">Excluded by the app&apos;s rules ({v.excluded.length})</summary>
                                <ul className="mt-1 flex list-disc flex-col gap-0.5 pl-4">
                                    {v.excluded.map((x: any) => (
                                        <li key={x.address}>
                                            {x.address}: {x.reason}
                                        </li>
                                    ))}
                                </ul>
                            </details>
                        )}
                    </section>
                ))}
            </div>
            <Callout tone="info">{r.live_comparison.reason}</Callout>

            <TableCard.Root size="sm">
                <TableCard.Header
                    title="Issues found in the workbook"
                    badge={`${r.flags.length}`}
                    description="Formula and data issues. “Client” marks items that need the client's decision."
                />
                <Table aria-label="Workbook issues" size="sm">
                    <Table.Header>
                        <Table.Head id="cells" label="Cells" />
                        <Table.Head id="severity" label="Severity" />
                        <Table.Head id="issue" label="Issue" isRowHeader />
                        <Table.Head id="detail" label="Detail" />
                        <Table.Head id="decision" label="Decision" />
                    </Table.Header>
                    <Table.Body items={r.flags.map((f: any, i: number) => ({ ...f, id: i }))}>
                        {(f: any) => (
                            <Table.Row id={f.id} className="h-auto">
                                <Table.Cell className="py-3 align-top">
                                    <code className="text-xs">{f.cells}</code>
                                </Table.Cell>
                                <Table.Cell className="py-3 align-top">
                                    <Badge type="pill-color" color={SEVERITY_COLOR[f.severity] ?? "gray"} size="sm">
                                        {f.severity}
                                    </Badge>
                                </Table.Cell>
                                <Table.Cell className="py-3 align-top font-medium text-primary">{f.issue}</Table.Cell>
                                <Table.Cell className="py-3 align-top text-xs">{f.detail ?? ""}</Table.Cell>
                                <Table.Cell className="py-3 align-top">
                                    {f.decision ? (
                                        <Badge type="pill-color" color="warning" size="sm">
                                            Client
                                        </Badge>
                                    ) : null}
                                </Table.Cell>
                            </Table.Row>
                        )}
                    </Table.Body>
                </Table>
            </TableCard.Root>
        </div>
    );
}
