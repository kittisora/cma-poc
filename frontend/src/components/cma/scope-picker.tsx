"use client";

import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";
import type { AreaScope, Property } from "@/lib/types";

interface Props {
    value: AreaScope;
    radiusMiles: number;
    /** The subject: the subdivision/block options need it to have one. */
    subject?: Pick<Property, "subdivision" | "block"> | null;
    onChange: (s: AreaScope) => void;
}

/** "Comps from": within the radius, the subject's subdivision (community), or its subdivision and block. */
export function ScopePicker({ value, radiusMiles, subject, onChange }: Props) {
    const sub = subject?.subdivision?.trim();
    return (
        <div className="flex flex-col gap-1.5">
            <span id="scope-label" className="text-sm font-medium text-secondary">
                Comps from
            </span>
            <ButtonGroup
                aria-labelledby="scope-label"
                size="sm"
                disallowEmptySelection
                selectedKeys={new Set([value])}
                onSelectionChange={(keys) => {
                    const k = [...keys][0];
                    if (k) onChange(k as AreaScope);
                }}
            >
                <ButtonGroupItem id="radius">Within {radiusMiles} mi</ButtonGroupItem>
                <ButtonGroupItem id="subdivision" isDisabled={subject !== undefined && !sub}>
                    Same subdivision
                </ButtonGroupItem>
                <ButtonGroupItem id="block" isDisabled={subject !== undefined && !subject?.block}>
                    Same block
                </ButtonGroupItem>
            </ButtonGroup>
            {subject && (
                <p className="text-xs text-tertiary">
                    {sub ? `Subject: ${sub}${subject.block ? `, block ${subject.block}` : " (no block in the county legal description)"}` : "The subject has no subdivision on record."}
                </p>
            )}
        </div>
    );
}
