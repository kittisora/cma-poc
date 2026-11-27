"use client";

import { LinkExternal01 } from "@untitledui/icons";
import type { BadgeColors } from "@/components/base/badges/badge-types";
import { Badge } from "@/components/base/badges/badges";
import type { Permit, PermitStage } from "@/lib/types";

export const STAGE_LABEL: Record<PermitStage, string> = {
    active: "Issued / under construction",
    pending: "In review",
    completed: "Completed",
    stale: "Old, not closed",
    inactive: "Expired / withdrawn",
};

const STAGE_COLOR: Record<PermitStage, BadgeColors> = {
    active: "warning",
    pending: "blue",
    completed: "success",
    stale: "gray",
    inactive: "gray",
};

/** Map marker colours by stage (hex, for Leaflet). */
export const STAGE_HEX: Record<PermitStage, string> = {
    active: "#dc6803",
    pending: "#2e90fa",
    completed: "#12b76a",
    stale: "#98a2b3",
    inactive: "#98a2b3",
};

export function PermitStageBadge({ stage }: { stage: PermitStage }) {
    return (
        <Badge type="pill-color" color={STAGE_COLOR[stage]} size="sm" className="whitespace-nowrap">
            {STAGE_LABEL[stage]}
        </Badge>
    );
}

/** Compact list of permits on one parcel (subject card, comp detail). */
export function PermitList({
    permits,
    empty = "No permits on record (Fairfax County PLUS, since 2022 for building permits).",
}: {
    permits: Permit[];
    empty?: string;
}) {
    if (!permits.length) return <p className="text-sm text-tertiary">{empty}</p>;
    return (
        <ul className="flex flex-col divide-y divide-secondary">
            {permits.map((p) => (
                <li key={`${p.kind}-${p.record_id}`} className="flex flex-wrap items-start gap-x-3 gap-y-1 py-2 text-sm">
                    <div className="flex min-w-0 flex-1 flex-col">
                        <span className="font-medium text-primary">
                            {p.type ?? "Permit"}
                            {p.new_construction && <span className="ml-1 text-xs font-normal text-warning-primary">· new construction</span>}
                        </span>
                        <span className="text-xs text-tertiary">
                            {p.record_id} · {p.status ?? "—"}
                            {p.submitted && ` · submitted ${p.submitted}`}
                            {p.issued && ` · ${p.kind === "site" ? "approved" : "issued"} ${p.issued}`}
                            {p.closed && ` · closed ${p.closed}`}
                        </span>
                        {p.project && <span className="text-xs text-quaternary">{p.project}</span>}
                    </div>
                    <PermitStageBadge stage={p.stage} />
                    {p.link && (
                        <a
                            href={p.link}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-xs font-semibold text-brand-secondary hover:underline"
                        >
                            PLUS record <LinkExternal01 className="size-3" aria-hidden="true" />
                        </a>
                    )}
                </li>
            ))}
        </ul>
    );
}
