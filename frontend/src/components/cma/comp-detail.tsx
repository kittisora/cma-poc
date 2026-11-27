"use client";

import { LinkExternal01 } from "@untitledui/icons";
import { SlideoutMenu } from "@/components/application/slideout-menus/slideout-menu";
import { Badge, BadgeWithDot } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { Checkbox } from "@/components/base/checkbox/checkbox";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { money, num, ppsf } from "@/lib/format";
import type { Comp } from "@/lib/types";
import { PermitList } from "./permit-badge";

interface Props {
    comp: Comp | null;
    isSelected: boolean;
    onToggle: (id: number, include: boolean) => void;
    onClose: () => void;
}

/** Slide-out with the factor-by-factor comparison and the county record behind one comp. */
export function CompDetail({ comp: c, isSelected, onToggle, onClose }: Props) {
    return (
        <SlideoutMenu isOpen={c !== null} onOpenChange={(open) => !open && onClose()} isDismissable className="max-w-xl">
            {c && (
                <>
                    <SlideoutMenu.Header onClose={onClose} className="flex flex-col gap-1">
                        <p className="text-sm font-medium text-tertiary">
                            Rank {c.rank} · score {c.score.toFixed(0)}
                        </p>
                        <h2 className="pr-8 text-lg font-semibold text-primary">{c.address}</h2>
                        <div className="flex flex-wrap gap-2 pt-1">
                            <Badge type="modern" color="gray" size="sm">
                                Sold {c.sale.sale_date}
                            </Badge>
                            <Badge type="modern" color="gray" size="sm">
                                {money(c.sale.price)}
                            </Badge>
                            <Badge type="modern" color="gray" size="sm">
                                {ppsf(c.ppsf_above_grade)} / AG sf
                            </Badge>
                            <Badge type="modern" color="gray" size="sm">
                                {c.distance_miles?.toFixed(2)} mi
                            </Badge>
                        </div>
                    </SlideoutMenu.Header>
                    <SlideoutMenu.Content>
                        <Checkbox
                            size="md"
                            label="Use this sale in the valuation"
                            hint="Manual selections replace the automatic top-ranked set."
                            isSelected={isSelected}
                            onChange={(v) => onToggle(c.sale_id, v)}
                        />
                        <p className="text-sm text-secondary">{c.reason}</p>

                        <section aria-labelledby="factors-heading" className="flex flex-col gap-4">
                            <h3 id="factors-heading" className="text-sm font-semibold text-primary">
                                Similarity factors
                            </h3>
                            {c.factors.map((f) => (
                                <div key={f.key} className="flex flex-col gap-1.5">
                                    <div className="flex items-baseline justify-between gap-3">
                                        <span className="text-sm font-medium text-secondary">{f.label}</span>
                                        <span className="text-xs text-quaternary">weight {f.weight}</span>
                                    </div>
                                    {f.score === null ? (
                                        <Badge type="pill-color" color="gray" size="sm">
                                            not compared (no data)
                                        </Badge>
                                    ) : (
                                        <ProgressBar value={Math.round(f.score * 100)} labelPosition="right" valueFormatter={(v) => `${v}%`} />
                                    )}
                                    <p className="text-xs text-tertiary">{f.detail}</p>
                                </div>
                            ))}
                        </section>

                        <section aria-labelledby="permits-heading" className="flex flex-col gap-1">
                            <h3 id="permits-heading" className="text-sm font-semibold text-primary">
                                Permits on this parcel ({c.permits?.length ?? 0})
                            </h3>
                            <PermitList permits={c.permits ?? []} />
                        </section>

                        <section aria-labelledby="record-heading" className="flex flex-col gap-2 pb-6">
                            <h3 id="record-heading" className="text-sm font-semibold text-primary">
                                Source record
                            </h3>
                            <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
                                <dt className="text-tertiary">County validity</dt>
                                <dd className="text-primary">{c.sale.validity}</dd>
                                <dt className="text-tertiary">Record</dt>
                                <dd className="whitespace-pre-wrap text-primary">{c.source.record_id}</dd>
                                <dt className="text-tertiary">Retrieved</dt>
                                <dd className="text-primary">{c.source.retrieved_at?.slice(0, 19).replace("T", " ")} UTC</dd>
                                <dt className="text-tertiary">Above-grade / lot</dt>
                                <dd className="text-primary">
                                    {num(c.property.above_grade_sf)} sf / {num(c.property.lot_sf)} sf
                                </dd>
                                <dt className="text-tertiary">Condition / grade</dt>
                                <dd className="text-primary">
                                    {c.property.condition ?? "—"} / {c.property.grade ?? "—"} · {c.property.style ?? "—"}
                                </dd>
                            </dl>
                            <div className="flex flex-wrap gap-2">
                                <BadgeWithDot type="modern" color="brand" size="sm">
                                    Fairfax County public record
                                </BadgeWithDot>
                                {!c.sale.in_latest_source && (
                                    <Badge type="pill-color" color="warning" size="sm">
                                        No longer in the latest county extract
                                    </Badge>
                                )}
                            </div>
                            {c.source.url && (
                                <Button href={c.source.url} target="_blank" rel="noreferrer" color="link-color" size="sm" iconTrailing={LinkExternal01}>
                                    Open the county dataset
                                </Button>
                            )}
                        </section>
                    </SlideoutMenu.Content>
                </>
            )}
        </SlideoutMenu>
    );
}
