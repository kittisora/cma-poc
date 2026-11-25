"use client";

import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";

const CHOICES = [
    { months: 3, label: "3 months" },
    { months: 6, label: "6 months" },
    { months: 12, label: "1 year" },
    { months: 24, label: "2 years" },
];

interface Props {
    months: number;
    onChange: (months: number) => void;
}

/** "Sold within": how far back before the valuation date a sale may be to count as a comp. */
export function LookbackPicker({ months, onChange }: Props) {
    const custom = !CHOICES.some((c) => c.months === months);
    return (
        <div className="flex flex-col gap-1.5">
            <span id="lookback-label" className="text-sm font-medium text-secondary">
                Sold within the last
            </span>
            <ButtonGroup
                aria-labelledby="lookback-label"
                size="sm"
                disallowEmptySelection
                selectedKeys={new Set([String(months)])}
                onSelectionChange={(keys) => {
                    const k = [...keys][0];
                    if (k) onChange(Number(k));
                }}
            >
                {CHOICES.map((c) => (
                    <ButtonGroupItem key={c.months} id={String(c.months)}>
                        {c.label}
                    </ButtonGroupItem>
                ))}
            </ButtonGroup>
            {custom && <p className="text-xs text-tertiary">Custom: {months} months (set under Search rules).</p>}
        </div>
    );
}
