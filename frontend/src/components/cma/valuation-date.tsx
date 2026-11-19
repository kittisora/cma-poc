"use client";

import { useEffect, useState } from "react";
import { type DateValue, parseDate } from "@internationalized/date";
import { DatePicker } from "@/components/application/date-picker/date-picker";

interface Props {
    value: string;
    max: string;
    onChange: (iso: string) => void;
}

/** Valuation date: only sales recorded on or before this date are eligible. Applies on "Apply". */
export function ValuationDate({ value, max, onChange }: Props) {
    const [pending, setPending] = useState<DateValue | null>(value ? parseDate(value) : null);
    useEffect(() => {
        setPending(value ? parseDate(value) : null);
    }, [value]);

    return (
        <div className="flex flex-col gap-1.5" data-testid="valuation-date">
            <span id="valuation-date-label" className="text-sm font-medium text-secondary">
                Valuation date
            </span>
            <DatePicker
                aria-labelledby="valuation-date-label"
                size="md"
                value={pending}
                maxValue={max ? parseDate(max) : undefined}
                onChange={(d) => setPending(d)}
                onApply={() => pending && pending.toString() !== value && onChange(pending.toString())}
                onCancel={() => setPending(value ? parseDate(value) : null)}
            />
        </div>
    );
}
