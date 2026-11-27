"use client";

import { useEffect, useState } from "react";
import { Building07, Grid01 } from "@untitledui/icons";
import type { Selection } from "react-aria-components";
import { MultiSelect } from "@/components/base/select/multi-select";
import { Select } from "@/components/base/select/select";
import { type AreaFilter, api } from "@/lib/api";
import type { AreaOption } from "@/lib/types";

const ANY = "__any";

const optionItems = (opts: AreaOption[]) =>
    opts.map((o) => ({ id: o.name, label: o.name, supportingText: `${o.count.toLocaleString()} address${o.count === 1 ? "" : "es"}` }));

interface Props {
    value: AreaFilter;
    onChange: (v: AreaFilter) => void;
    /** Changing this remounts the subdivision box, clearing any half-typed text (used by "Clear filters"). */
    resetKey?: number;
    shortcut?: boolean;
}

/**
 * Subdivision → Block → Streets. Each narrows the next: blocks list only the chosen subdivision's,
 * streets only those in the chosen subdivision and block. Several streets can be picked at once.
 */
export function AreaFilters({ value, onChange, resetKey = 0, shortcut = true }: Props) {
    const { subdivision = null, block = null, streets = [] } = value;
    const [options, setOptions] = useState<{ subdivisions: AreaOption[]; blocks: AreaOption[]; streets: AreaOption[] }>({
        subdivisions: [],
        blocks: [],
        streets: [],
    });
    const [error, setError] = useState("");

    useEffect(() => {
        const ctrl = new AbortController();
        api.areas({ subdivision, block }, ctrl.signal)
            .then((o) => {
                setOptions(o);
                setError("");
            })
            .catch((e: Error) => {
                if (e.name !== "AbortError") setError(`Could not load search filters: ${e.message}`);
            });
        return () => ctrl.abort();
    }, [subdivision, block]);

    const blockDisabled = !subdivision || options.blocks.length === 0;
    const streetItems = optionItems(options.streets);
    const selected: Selection = new Set(streets);

    return (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,0.6fr)_minmax(0,1.1fr)]">
            <Select.ComboBox
                key={`sub-${resetKey}`}
                label="Subdivision"
                placeholder="Type to search subdivisions"
                icon={Building07}
                shortcut={shortcut}
                items={optionItems(options.subdivisions)}
                selectedKey={subdivision}
                onSelectionChange={(k) => onChange({ subdivision: k === null ? null : String(k), block: null, streets: [] })}
                menuTrigger="focus"
                hint={error || undefined}
            >
                {(item) => (
                    <Select.Item id={item.id} supportingText={item.supportingText}>
                        {item.label}
                    </Select.Item>
                )}
            </Select.ComboBox>
            <Select
                key={`blk-${resetKey}-${subdivision}`}
                label="Block"
                placeholder={!subdivision ? "Choose a subdivision first" : blockDisabled ? "No blocks recorded" : "Any block"}
                icon={Grid01}
                isDisabled={blockDisabled}
                selectedKey={block ?? ANY}
                onSelectionChange={(k) => onChange({ subdivision, block: k === null || k === ANY ? null : String(k), streets: [] })}
                items={[{ id: ANY, label: "Any block" }, ...optionItems(options.blocks)]}
            >
                {(item) => (
                    <Select.Item id={item.id} supportingText={item.supportingText}>
                        {item.label}
                    </Select.Item>
                )}
            </Select>
            <MultiSelect
                key={`st-${resetKey}-${subdivision}-${block}`}
                label="Streets"
                placeholder={subdivision ? "All streets" : "Choose one or more streets"}
                items={streetItems}
                selectedKeys={selected}
                onSelectionChange={(keys) => onChange({ subdivision, block, streets: keys === "all" ? streetItems.map((s) => s.id) : [...keys].map(String) })}
                onReset={() => onChange({ subdivision, block, streets: [] })}
                onSelectAll={() => onChange({ subdivision, block, streets: streetItems.map((s) => s.id) })}
                selectedCountFormatter={(n) => (n === 1 ? streets[0] : `${n} streets`)}
                emptyStateTitle="No streets found"
            >
                {(item) => (
                    <MultiSelect.Item id={item.id} supportingText={item.supportingText} selectionIndicator="checkbox" selectionIndicatorAlign="left">
                        {item.label}
                    </MultiSelect.Item>
                )}
            </MultiSelect>
        </div>
    );
}

export const hasAreaFilter = (f: AreaFilter) => !!(f.subdivision || f.block || (f.streets && f.streets.length));
