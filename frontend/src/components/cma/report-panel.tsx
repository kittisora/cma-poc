"use client";

import { useEffect, useState } from "react";
import { Download01, Edit05, Eye, File06, Palette, Stars02, Trash01 } from "@untitledui/icons";
import { Heading as AriaHeading } from "react-aria-components";
import { FileUpload } from "@/components/application/file-upload/file-upload-base";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { SlideoutMenu } from "@/components/application/slideout-menus/slideout-menu";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { CloseButton } from "@/components/base/buttons/close-button";
import { Input } from "@/components/base/input/input";
import { TextArea } from "@/components/base/textarea/textarea";
import { Toggle } from "@/components/base/toggle/toggle";
import { api, downloadReport } from "@/lib/api";
import type { Analysis, Branding, CMARequest, ReportModel } from "@/lib/types";
import { notify } from "./notify";

interface Props {
    a: Analysis;
    req: CMARequest;
    aiEnabled: boolean;
    narrative: string;
    narrativeSource: string;
    setNarrative: (s: string, source?: string) => void;
}

const EMPTY: Branding = {
    company: "",
    agent_name: "",
    agent_title: "",
    phone: "",
    email: "",
    website: "",
    license_line: "",
    primary_color: "#1F4E79",
    logo_data_url: null,
    footer_note: "",
};

const SWATCHES = ["#1F4E79", "#206CDC", "#0E7490", "#047857", "#B45309", "#9F1239", "#6D28D9", "#111827"];

export function ReportPanel({ a, req, aiEnabled, narrative, narrativeSource, setNarrative }: Props) {
    const [branding, setBranding] = useState<Branding>(EMPTY);
    const [preparedFor, setPreparedFor] = useState("");
    const [includeSources, setIncludeSources] = useState(true);
    const [preview, setPreview] = useState<ReportModel | null>(null);
    const [busy, setBusy] = useState<"" | "draft" | "preview" | "pdf" | "docx">("");
    const [brandingOpen, setBrandingOpen] = useState(false);

    useEffect(() => {
        api.getBranding()
            .then(setBranding)
            .catch(() => undefined);
    }, []);

    const body = () => ({
        cma: req,
        branding,
        narrative,
        prepared_for: preparedFor,
        include_sources: includeSources,
        expected_estimate: a.valuation.estimate,
        narrative_source: narrativeSource || "agent",
    });

    const draft = async () => {
        setBusy("draft");
        try {
            const r = await api.narrative(req);
            setNarrative(r.narrative, r.generated_by);
            if (r.note) notify("info", "Template narrative used", r.note);
            else notify("success", r.generated_by === "ai" ? "AI draft ready" : "Draft ready", "Review and edit it before exporting.");
        } catch (e) {
            notify("error", "Could not draft the narrative", (e as Error).message);
        } finally {
            setBusy("");
        }
    };

    const doPreview = async () => {
        setBusy("preview");
        try {
            setPreview(await api.preview(body()));
        } catch (e) {
            notify("error", "Preview failed", (e as Error).message);
        } finally {
            setBusy("");
        }
    };

    const doExport = async (fmt: "pdf" | "docx") => {
        setBusy(fmt);
        try {
            const name = await downloadReport(fmt, body());
            notify("success", `Downloaded ${name}`, "The report uses exactly the figures and narrative shown here.");
        } catch (e) {
            notify("error", `${fmt.toUpperCase()} export failed`, (e as Error).message);
        } finally {
            setBusy("");
        }
    };

    const noEstimate = a.valuation.estimate === null;

    return (
        <div className="flex flex-col gap-6">
            <section className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-3">
                    <h3 className="flex-1 text-sm font-semibold text-primary">Narrative</h3>
                    {narrative && (
                        <Badge type="pill-color" color={narrativeSource === "ai" ? "brand" : "gray"} size="sm">
                            {narrativeSource === "ai" ? "AI draft, edited by you" : narrativeSource === "template" ? "Template draft" : "Written by you"}
                        </Badge>
                    )}
                    <Button size="sm" color="secondary" iconLeading={aiEnabled ? Stars02 : Edit05} isLoading={busy === "draft"} showTextWhileLoading onClick={draft}>
                        {aiEnabled ? "Draft with AI" : "Draft narrative"}
                    </Button>
                </div>
                {!aiEnabled && <p className="text-xs text-tertiary">AI not configured, so the draft is built from the computed results.</p>}
                <TextArea
                    aria-label="Narrative text"
                    rows={12}
                    value={narrative}
                    onChange={(x) => setNarrative(x)}
                    placeholder="Draft the narrative, then review and edit it. The exported report uses exactly this text."
                />
            </section>

            <section className="flex flex-col gap-4 border-t border-secondary pt-5">
                <h3 className="text-sm font-semibold text-primary">Report details</h3>
                <Input label="Prepared for" placeholder="Client name (optional)" value={preparedFor} onChange={setPreparedFor} />
                <Toggle label="Include sources and record IDs" isSelected={includeSources} onChange={setIncludeSources} />
                <div className="flex items-center gap-3">
                    <span className="size-5 rounded-full ring-1 ring-secondary" style={{ background: branding.primary_color }} aria-hidden="true" />
                    <span className="flex-1 truncate text-sm text-tertiary">{branding.company || "No company name set"}</span>
                    <Button size="sm" color="link-color" iconLeading={Palette} onClick={() => setBrandingOpen(true)}>
                        Branding
                    </Button>
                </div>
            </section>

            <div className="sticky bottom-0 -mx-1 flex flex-wrap gap-2 border-t border-secondary bg-primary px-1 pt-4 pb-1">
                <Button size="md" color="secondary" iconLeading={Eye} isLoading={busy === "preview"} showTextWhileLoading onClick={doPreview}>
                    Preview
                </Button>
                <Button size="md" iconLeading={Download01} isDisabled={noEstimate || busy !== ""} isLoading={busy === "pdf"} showTextWhileLoading onClick={() => doExport("pdf")}>
                    Export PDF
                </Button>
                <Button size="md" iconLeading={File06} isDisabled={noEstimate || busy !== ""} isLoading={busy === "docx"} showTextWhileLoading onClick={() => doExport("docx")}>
                    Export Word
                </Button>
            </div>

            <BrandingSlideout open={brandingOpen} onClose={() => setBrandingOpen(false)} branding={branding} setBranding={setBranding} />

            <ModalOverlay isDismissable isOpen={preview !== null} onOpenChange={(o) => !o && setPreview(null)}>
                <Modal className="max-w-3xl">
                    <Dialog aria-label="Report preview">{preview && <ReportPreview r={preview} onClose={() => setPreview(null)} />}</Dialog>
                </Modal>
            </ModalOverlay>
        </div>
    );
}

function BrandingSlideout({
    open,
    onClose,
    branding,
    setBranding,
}: {
    open: boolean;
    onClose: () => void;
    branding: Branding;
    setBranding: (b: Branding) => void;
}) {
    const [saving, setSaving] = useState(false);
    const field = (k: keyof Branding, label: string, placeholder = "") => (
        <Input label={label} placeholder={placeholder} value={(branding[k] as string) ?? ""} onChange={(v) => setBranding({ ...branding, [k]: v })} />
    );

    const onLogo = (files: FileList) => {
        const file = files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => setBranding({ ...branding, logo_data_url: String(reader.result) });
        reader.readAsDataURL(file);
    };

    const save = async () => {
        setSaving(true);
        try {
            setBranding(await api.putBranding(branding));
            notify("success", "Branding saved", "Every report from this app now uses it.");
            onClose();
        } catch (e) {
            notify("error", "Could not save branding", (e as Error).message);
        } finally {
            setSaving(false);
        }
    };

    return (
        <SlideoutMenu isOpen={open} onOpenChange={(o) => !o && onClose()} isDismissable className="max-w-lg">
            <SlideoutMenu.Header onClose={onClose}>
                <h2 className="text-lg font-semibold text-primary">Report branding</h2>
                <p className="text-sm text-tertiary">Shown on the PDF and Word reports. Saved for the whole team.</p>
            </SlideoutMenu.Header>
            <SlideoutMenu.Content>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {field("company", "Company", "Your Brokerage")}
                    {field("agent_name", "Agent name")}
                    {field("agent_title", "Title")}
                    {field("phone", "Phone")}
                    {field("email", "Email")}
                    {field("website", "Website")}
                </div>
                {field("license_line", "License line")}
                {field("footer_note", "Footer note")}
                <div className="flex flex-col gap-2">
                    <span className="text-sm font-medium text-secondary">Accent color</span>
                    <div className="flex flex-wrap items-center gap-2">
                        {SWATCHES.map((c) => (
                            <button
                                key={c}
                                type="button"
                                aria-label={`Use color ${c}`}
                                aria-pressed={branding.primary_color.toUpperCase() === c}
                                onClick={() => setBranding({ ...branding, primary_color: c })}
                                className="size-7 cursor-pointer rounded-full ring-1 ring-secondary outline-focus-ring ring-inset focus-visible:outline-2 focus-visible:outline-offset-2 aria-pressed:ring-2 aria-pressed:ring-offset-2 aria-pressed:ring-brand"
                                style={{ background: c }}
                            />
                        ))}
                        <Input
                            aria-label="Accent color hex"
                            size="sm"
                            className="w-28"
                            value={branding.primary_color}
                            onChange={(v) => /^#[0-9a-fA-F]{0,6}$/.test(v) && setBranding({ ...branding, primary_color: v })}
                        />
                    </div>
                </div>
                <div className="flex flex-col gap-2 pb-4">
                    <span className="text-sm font-medium text-secondary">Logo</span>
                    {branding.logo_data_url ? (
                        <div className="flex items-center gap-3 rounded-xl p-3 ring-1 ring-secondary ring-inset">
                            <img src={branding.logo_data_url} alt="Current logo" className="h-10 max-w-40 object-contain" />
                            <span className="flex-1" />
                            <Button size="sm" color="tertiary-destructive" iconLeading={Trash01} onClick={() => setBranding({ ...branding, logo_data_url: null })}>
                                Remove
                            </Button>
                        </div>
                    ) : (
                        <FileUpload.DropZone
                            hint="PNG or JPEG, under 1 MB"
                            accept="image/png,image/jpeg"
                            allowsMultiple={false}
                            maxSize={1_000_000}
                            onDropFiles={onLogo}
                            onSizeLimitExceed={() => notify("error", "Logo too large", "Use a PNG or JPEG under 1 MB.")}
                            onDropUnacceptedFiles={() => notify("error", "Unsupported file", "Use a PNG or JPEG image.")}
                        />
                    )}
                </div>
            </SlideoutMenu.Content>
            <SlideoutMenu.Footer className="flex justify-end gap-3">
                <Button color="secondary" onClick={onClose}>
                    Close
                </Button>
                <Button isLoading={saving} showTextWhileLoading onClick={save}>
                    Save for the team
                </Button>
            </SlideoutMenu.Footer>
        </SlideoutMenu>
    );
}

function ReportPreview({ r, onClose }: { r: ReportModel; onClose: () => void }) {
    const accent = r.branding.primary_color || "#1F4E79";
    return (
        <article className="relative w-full overflow-hidden rounded-2xl bg-primary shadow-xl" aria-label="Report preview">
            <CloseButton onClick={onClose} className="absolute top-3 right-3" />
            <header className="flex items-center gap-4 px-6 py-5 text-white" style={{ background: accent }}>
                <div className="flex-1">
                    <p className="text-lg font-semibold">{r.branding.company}</p>
                    <p className="text-sm opacity-90">{[r.branding.agent_name, r.branding.phone, r.branding.email].filter(Boolean).join(" · ")}</p>
                </div>
                {r.branding.logo_data_url && <img src={r.branding.logo_data_url} alt={`${r.branding.company} logo`} className="mr-8 h-10 rounded bg-white p-1" />}
            </header>
            <div className="flex max-h-[70vh] flex-col gap-4 overflow-y-auto px-6 py-5 text-sm text-secondary">
                <div>
                    <AriaHeading slot="title" className="text-xl font-semibold text-primary">
                        {r.title}
                    </AriaHeading>
                    <p className="text-tertiary">
                        {r.prepared_for && `Prepared for ${r.prepared_for} · `}Valuation date {r.valuation_date}
                    </p>
                </div>
                <div className="rounded-xl bg-secondary p-4">
                    <p className="text-display-xs font-semibold text-primary">{r.estimate.estimate}</p>
                    <p>Range {r.estimate.range}</p>
                    <p className="text-xs text-tertiary">
                        {r.estimate.basis} ({r.estimate.statistic})
                    </p>
                </div>
                <h4 className="font-semibold text-primary">Comparable sales</h4>
                <ol className="list-decimal pl-5">
                    {r.comps.map((c) => (
                        <li key={String(c.n)}>
                            {c.address} — {c.sale_date}, {c.price}, {c.above_grade_sf} sf AG ({c.ppsf_ag}/sf), {c.distance}
                        </li>
                    ))}
                </ol>
                {r.map_png_b64 && (
                    <img className="rounded-lg ring-1 ring-secondary" src={`data:image/png;base64,${r.map_png_b64}`} alt="Location diagram of the subject and comparable sales" />
                )}
                <h4 className="font-semibold text-primary">Calculation</h4>
                <ul className="list-disc pl-5 text-xs">
                    {r.method_lines.map((l) => (
                        <li key={l}>{l}</li>
                    ))}
                </ul>
                {r.narrative && (
                    <>
                        <h4 className="font-semibold text-primary">Analysis</h4>
                        <p className="text-xs whitespace-pre-wrap">{r.narrative}</p>
                    </>
                )}
                {r.sources.length > 0 && (
                    <p className="text-xs text-tertiary">
                        {r.sources.length} source records listed · CMA {r.fingerprint}
                    </p>
                )}
                <p className="text-xs text-quaternary">{r.disclaimer}</p>
            </div>
        </article>
    );
}
