"use client";

import { CurrencyDollarCircle, Home03, Stars02 } from "@untitledui/icons";
import { MetricChangeIndicator } from "@/components/application/metrics/metrics";
import { Badge, BadgeWithIcon } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { money, pct, signedMoney } from "@/lib/format";
import type { Analysis } from "@/lib/types";

interface Props {
    a: Analysis;
    aiEnabled: boolean;
    onAskAi: () => void;
}

export function EstimateSummary({ a, aiEnabled, onAskAi }: Props) {
    const v = a.valuation;
    const basis = v.primary_basis ? v.bases[v.primary_basis] : null;
    const ch = a.change_since_last_sale;
    const s = a.subject;

    return (
        <section aria-labelledby="estimate-heading" className="overflow-hidden rounded-xl bg-primary shadow-xs ring-1 ring-secondary">
            <div className="flex flex-col gap-4 p-5">
                <div className="flex items-start gap-3">
                    <FeaturedIcon icon={CurrencyDollarCircle} color="brand" theme="light" size="lg" />
                    <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                        <h2 id="estimate-heading" className="text-sm font-medium text-tertiary">
                            Estimated value · {a.valuation_date}
                        </h2>
                        {v.estimate !== null ? (
                            <p className="text-display-sm font-semibold text-primary" data-testid="estimate-value">
                                {money(v.estimate)}
                            </p>
                        ) : (
                            <p className="text-lg font-semibold text-warning-primary" data-testid="estimate-value">
                                Not enough data for an estimate
                            </p>
                        )}
                    </div>
                    <Button size="sm" color={aiEnabled ? "secondary" : "tertiary"} iconLeading={Stars02} onClick={onAskAi}>
                        Ask AI
                    </Button>
                </div>

                {v.estimate !== null && (
                    <div className="flex flex-wrap items-center gap-2">
                        <Badge type="modern" color="gray" size="md">
                            Range {money(v.range_low)} – {money(v.range_high)}
                        </Badge>
                        <Badge type="pill-color" color="brand" size="md">
                            {basis?.label}
                        </Badge>
                        <Badge type="pill-color" color="gray" size="md">
                            {v.point_statistic === "mean" ? "Average" : "Median"} of {basis?.n} comps
                        </Badge>
                        {v.adjustments_total !== 0 && (
                            <Badge type="pill-color" color="warning" size="md">
                                Adjustments {signedMoney(v.adjustments_total)}
                            </Badge>
                        )}
                        {v.appreciation_pct !== 0 && (
                            <Badge type="pill-color" color="warning" size="md">
                                Appreciation {pct(v.appreciation_pct)}
                            </Badge>
                        )}
                    </div>
                )}
            </div>

            <dl className="grid grid-cols-1 divide-y divide-secondary border-t border-secondary sm:grid-cols-2 sm:divide-x sm:divide-y-0">
                <div className="flex flex-col gap-1 px-5 py-4">
                    <dt className="text-sm font-medium text-tertiary">Estimated change since the last sale</dt>
                    {ch ? (
                        <dd className="flex flex-wrap items-center gap-2">
                            <span className="text-lg font-semibold text-primary">{signedMoney(ch.amount)}</span>
                            <MetricChangeIndicator type="modern" trend={ch.amount >= 0 ? "positive" : "negative"} value={pct(ch.pct)} />
                            <span className="w-full text-xs text-tertiary">
                                vs {money(ch.last_sale_price)} on {ch.last_sale_date}
                            </span>
                        </dd>
                    ) : (
                        <dd className="text-sm text-tertiary">
                            {a.plan
                                ? "Not shown for a planned house: the last sale was of the house on record."
                                : a.latest_transfer
                                  ? `No arm's-length sale on record (latest transfer ${a.latest_transfer.sale_date}: ${a.latest_transfer.validity}).`
                                  : "No recorded sale of the subject."}
                        </dd>
                    )}
                </div>
                <div className="flex flex-col gap-1 px-5 py-4">
                    <dt className="text-sm font-medium text-tertiary">County assessment {s.assessed_tax_year ?? ""}</dt>
                    <dd className="flex flex-wrap items-center gap-2">
                        <span className="text-lg font-semibold text-primary">{money(s.assessed_total)}</span>
                        <BadgeWithIcon type="modern" color="gray" size="sm" iconLeading={Home03}>
                            assessor record
                        </BadgeWithIcon>
                    </dd>
                </div>
            </dl>
        </section>
    );
}
