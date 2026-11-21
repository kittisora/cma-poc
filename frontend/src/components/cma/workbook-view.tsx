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
import { useCma } from "@/providers/cma-provider";
import { AddressSearch } from "./address-search";
import { Callout } from "./callout";
import { notify } from "./notify";
import { PageHeader } from "./page-header";

const SEVERITY_COLOR: Record<string, "error" | "warning" | "gray" | "brand"> = { high: "error", medium: "warning", low: "gray", info: "brand" };

type Subject = { kind: "workbook" | "property"; key: string; label: string };

export function WorkbookView() {
    const { meta } = useCma();
    const [subject, setSubject] = useState<Subject | null>(null);
    // Only values the user typed are sent; otherwise the server uses its own defaults (and labels their source).
    const [finished, setFinished] = useState<number | null>(null);
    const [garage, setGarage] = useState<number | null>(null);
    const [apprec, setApprec] = useState(0);
    const [r, setR] = useState<Record<string, any> | null>(null);
    const [err, setErr] = useState("");

    // The page's subject is saved for the whole team; load it first.
    useEffect(() => {
        api.getWorkbookSubject()
            .then((s) => setSubject({ kind: s.kind, key: s.key, label: s.label ?? s.key }))
            .catch(() => setSubject({ kind: "workbook", key: "1009 New", label: "1009 New" }));
    }, []);

    useEffect(() => {
        if (!subject) return;
        const t = setTimeout(() => {
            api.regression({
                ...(subject.kind === "property" ? { subject_pin: subject.key } : { subject: subject.key }),
                finished_sf: finished ?? undefined,
                garage_adjustment: garage ?? undefined,
                appreciation_pct: apprec || 0,
            })
                .then((x) => {
                    setR(x);
                    setErr("");
                })
                .catch((e: Error) => setErr(e.message));
        }, 200);
        return () => clearTimeout(t);
    }, [subject, finished, garage, apprec]); // eslint-disable-line react-hooks/exhaustive-deps

    const changeSubject = async (next: Subject) => {
        setSubject(next);
        setFinished(null);
        setGarage(null);
        setR(null);
        try {
            await api.putWorkbookSubject(next.kind, next.key);
            notify("success", "Subject updated", `${next.label} is now the Workbook Check subject for the team.`);
        } catch (e) {
            notify("error", "Could not save the subject", (e as Error).message);
        }
    };

    const header = (
        <PageHeader
            crumb="Workbook check"
            title="Workbook regression check"
            description={
                r
                    ? `Applies the client's “${r.workbook}” pricing method to the subject below and compares it with the app's own comp selection. Valuation date ${r.valuation_date}.`
                    : "Reproduces the client's workbook pricing method and compares it with the app's rules."
            }
        />
    );

    if (!r || !subject) {
        return (
            <>
                {header}
                {err ? <Callout tone="error">{err}</Callout> : <LoadingIndicator type="line-spinner" size="md" label="Loading…" />}
            </>
        );
    }
    const reg = r.regression;
    const isProperty = r.subject_kind === "property";
    const f = r.subject_facts;
    const subjectItems = [
        ...(subject.kind === "property" ? [{ id: `property|${subject.key}`, label: subject.label, supportingText: "Fairfax County record" }] : []),
        ...Object.keys(r.subjects).map((s) => ({ id: `workbook|${s}`, label: s, supportingText: "workbook example (Oronoco St, 22314)" })),
    ];
    const facts: [string, string][] = f
        ? [
              ["Address", f.address],
              ["PARID", f.pin],
              ["Style / built", `${f.style ?? "—"} · ${f.year_built ?? "—"}`],
              ["Beds / baths", `${f.beds ?? "—"} / ${f.baths ?? "—"}`],
              ["Above-grade", f.above_grade_sf ? `${f.above_grade_sf.toLocaleString()} sf` : "not recorded"],
              ["Total finished", f.total_finished_sf ? `${f.total_finished_sf.toLocaleString()} sf` : "not recorded"],
              ["Assessed", money(f.assessed_total)],
          ]
        : [];

    return (
        <div className="flex flex-col gap-6">
            {header}
            <Callout tone={isProperty ? "success" : "info"} title={isProperty ? "Subject is a Fairfax County property" : "Where the workbook's addresses are"}>
                {r.address_verification.result}
            </Callout>

            <section className="flex flex-col gap-4 rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary" aria-labelledby="wb-subject">
                <h2 id="wb-subject" className="text-sm font-semibold text-primary">
                    Subject property
                </h2>
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
                    <Select
                        label="Subject"
                        hint="Saved for the whole team."
                        selectedKey={`${subject.kind}|${subject.key}`}
                        onSelectionChange={(k) => {
                            const [kind, ...rest] = String(k).split("|");
                            const key = rest.join("|");
                            if (kind === subject.kind && key === subject.key) return;
                            const item = subjectItems.find((i) => i.id === String(k));
                            changeSubject({ kind: kind as Subject["kind"], key, label: item?.label ?? key });
                        }}
                        items={subjectItems}
                    >
                        {(item) => (
                            <Select.Item id={item.id} supportingText={item.supportingText}>
                                {item.label}
                            </Select.Item>
                        )}
                    </Select>
                    <div data-testid="workbook-subject-search">
                        <AddressSearch
                            zips={meta?.target_zips ?? ["22308", "22309"]}
                            current={null}
                            label="Change subject to an address"
                            onSelect={(res) => changeSubject({ kind: "property", key: res.pin, label: `${res.address}, ${res.zip}` })}
                        />
                    </div>
                </div>
                {isProperty && (
                    <dl className="grid grid-cols-2 gap-x-6 gap-y-2 border-t border-secondary pt-4 sm:grid-cols-4 lg:grid-cols-7" data-testid="workbook-subject-facts">
                        {facts.map(([k, v]) => (
                            <div key={k} className="flex min-w-0 flex-col gap-0.5">
                                <dt className="text-xs font-medium text-quaternary">{k}</dt>
                                <dd className="text-sm font-medium whitespace-pre-wrap text-primary">{v}</dd>
                            </div>
                        ))}
                    </dl>
                )}
            </section>

            <section className="flex flex-col gap-4 rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary" aria-labelledby="wb-inputs">
                <h2 id="wb-inputs" className="text-sm font-semibold text-primary">
                    Inputs (editable assumptions for this check only)
                </h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <InputNumber
                        label="Finished sq ft"
                        hint={isProperty ? `Default: ${r.inputs.finished_sf_source}` : undefined}
                        minValue={100}
                        value={finished ?? Number(r.inputs.finished_sf)}
                        formatOptions={{ maximumFractionDigits: 0 }}
                        onChange={(n) => !Number.isNaN(n) && setFinished(n)}
                    />
                    <InputNumber
                        label="Garage/ADU adjustment"
                        step={5000}
                        value={garage ?? Number(r.inputs.garage_adjustment)}
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
                    <p className="text-xs text-tertiary">
                        {isProperty
                            ? "This subject is not in the workbook, so there is no workbook cell total to compare against. Variant C is a live CMA from county records."
                            : "Inputs differ from the workbook's, so there is no workbook total to compare against."}
                    </p>
                )}
            </section>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {r.variants.map((v: any) => (
                    <section key={v.variant} className="flex flex-col gap-3 rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary">
                        <div className="flex items-start gap-3">
                            <FeaturedIcon icon={FileCheck02} color={(isProperty ? v.variant === "C" : v.variant === "A") ? "brand" : "gray"} theme="light" size="md" />
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
