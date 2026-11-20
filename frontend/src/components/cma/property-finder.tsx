"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Building07, Grid01, Home02, MarkerPin02, XClose } from "@untitledui/icons";
import { useHotkeys } from "react-hotkeys-hook";
import { Button } from "@/components/base/buttons/button";
import { Select } from "@/components/base/select/select";
import { api } from "@/lib/api";
import { PROPERTY_TYPES } from "@/lib/format";
import type { AreaOption, SearchResult } from "@/lib/types";

interface Props {
    /** The subject currently analysed (also when chosen elsewhere, e.g. an example button). */
    current: SearchResult | null;
    onSelect: (r: SearchResult) => void;
}

const ANY = "__any";

const optionItems = (opts: AreaOption[], noun: string) =>
    opts.map((o) => ({ id: o.name, label: o.name, supportingText: `${o.count.toLocaleString()} ${noun}${o.count === 1 ? "" : "es"}` }));

/**
 * Find the subject by Subdivision → Block → Street, then pick the property.
 * Each filter narrows the next; any one of them is enough to list properties. ⌘K / Ctrl+K focuses it.
 */
export function PropertyFinder({ current, onSelect }: Props) {
    const [subdivision, setSubdivision] = useState<string | null>(null);
    const [block, setBlock] = useState<string | null>(null);
    const [street, setStreet] = useState<string | null>(null);
    const [options, setOptions] = useState<{ subdivisions: AreaOption[]; blocks: AreaOption[]; streets: AreaOption[] }>({
        subdivisions: [],
        blocks: [],
        streets: [],
    });
    const [found, setFound] = useState<{ key: string; total: number; results: SearchResult[] }>({ key: "", total: 0, results: [] });
    const [status, setStatus] = useState("");
    const wrapRef = useRef<HTMLDivElement>(null);
    // Remounting a ComboBox clears its typed text when its filter is reset.
    const [resetKey, setResetKey] = useState(0);

    useHotkeys(
        "mod+k",
        (e) => {
            e.preventDefault();
            wrapRef.current?.querySelector("input")?.focus();
        },
        { enableOnFormTags: true },
    );

    // Filter choices: blocks narrow to the subdivision, streets to the subdivision and block.
    useEffect(() => {
        const ctrl = new AbortController();
        api.areas({ subdivision, block }, ctrl.signal)
            .then(setOptions)
            .catch((e: Error) => {
                if (e.name !== "AbortError") setStatus(`Could not load search filters: ${e.message}`);
            });
        return () => ctrl.abort();
    }, [subdivision, block]);

    const key = JSON.stringify([subdivision, block, street]);
    const hasFilter = !!(subdivision || block || street);
    useEffect(() => {
        if (!hasFilter) {
            setStatus("");
            return;
        }
        const ctrl = new AbortController();
        api.properties({ subdivision, block, street }, ctrl.signal)
            .then((r) => {
                setFound({ key, total: r.total, results: r.results });
                setStatus(
                    r.total === 0
                        ? "No property matches these filters."
                        : r.total > r.results.length
                          ? `${r.total.toLocaleString()} properties; showing the first ${r.results.length.toLocaleString()}. Add a filter to narrow the list.`
                          : `${r.total.toLocaleString()} ${r.total === 1 ? "property" : "properties"} found`,
                );
            })
            .catch((e: Error) => {
                if (e.name !== "AbortError") setStatus(`Search failed: ${e.message}`);
            });
        return () => ctrl.abort();
    }, [key, hasFilter]); // eslint-disable-line react-hooks/exhaustive-deps

    const results = found.key === key ? found.results : [];
    const propertyItems = useMemo(
        () =>
            results.map((r, i) => ({
                id: `${i}|${r.pin}`,
                label: r.address,
                supportingText: [
                    r.zip,
                    PROPERTY_TYPES[r.property_type ?? "OTHER"] ?? r.land_use ?? "",
                    r.lot ? `Lot ${r.lot}` : "",
                    r.block ? `Blk ${r.block}` : "",
                    !subdivision && r.subdivision ? r.subdivision : "",
                ]
                    .filter(Boolean)
                    .join(" · "),
            })),
        [results, subdivision],
    );
    const currentId = current ? propertyItems.find((it) => it.id.endsWith(`|${current.pin}`))?.id : undefined;

    const chooseSubdivision = (v: string | null) => {
        setSubdivision(v);
        setBlock(null);
        setStreet(null);
    };
    const chooseBlock = (v: string | null) => {
        setBlock(v);
        setStreet(null);
    };
    const clear = () => {
        setSubdivision(null);
        setBlock(null);
        setStreet(null);
        setResetKey((k) => k + 1);
    };

    const blockDisabled = !subdivision || options.blocks.length === 0;

    return (
        <div ref={wrapRef} className="flex w-full flex-col gap-3" data-testid="property-finder">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,0.6fr)_minmax(0,1fr)]">
                <Select.ComboBox
                    key={`sub-${resetKey}`}
                    label="Subdivision"
                    placeholder="Type to search subdivisions"
                    icon={Building07}
                    items={optionItems(options.subdivisions, "address")}
                    selectedKey={subdivision}
                    onSelectionChange={(k) => chooseSubdivision(k === null ? null : String(k))}
                    menuTrigger="focus"
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
                    onSelectionChange={(k) => chooseBlock(k === null || k === ANY ? null : String(k))}
                    items={[{ id: ANY, label: "Any block" }, ...optionItems(options.blocks, "address")]}
                >
                    {(item) => (
                        <Select.Item id={item.id} supportingText={item.supportingText}>
                            {item.label}
                        </Select.Item>
                    )}
                </Select>
                <Select.ComboBox
                    key={`st-${resetKey}-${subdivision}-${block}`}
                    label="Street"
                    placeholder="Type to search streets"
                    shortcut={false}
                    icon={MarkerPin02}
                    items={optionItems(options.streets, "address")}
                    selectedKey={street}
                    onSelectionChange={(k) => setStreet(k === null ? null : String(k))}
                    menuTrigger="focus"
                >
                    {(item) => (
                        <Select.Item id={item.id} supportingText={item.supportingText}>
                            {item.label}
                        </Select.Item>
                    )}
                </Select.ComboBox>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
                <div className="min-w-0 flex-1">
                    <Select.ComboBox
                        key={`prop-${key}`}
                        label="Property"
                        placeholder={hasFilter ? "Type a house number or address" : "Choose a subdivision, block or street first"}
                        shortcut={false}
                        icon={Home02}
                        isDisabled={!hasFilter}
                        items={propertyItems}
                        selectedKey={currentId ?? null}
                        onSelectionChange={(k) => {
                            if (k === null) return;
                            const r = results[Number(String(k).split("|")[0])];
                            if (r) onSelect(r);
                        }}
                        menuTrigger="focus"
                        hint={hasFilter ? status : undefined}
                    >
                        {(item) => (
                            <Select.Item id={item.id} supportingText={item.supportingText} icon={Home02}>
                                {item.label}
                            </Select.Item>
                        )}
                    </Select.ComboBox>
                </div>
                {hasFilter && (
                    <Button size="md" color="secondary" iconLeading={XClose} onClick={clear} className="sm:mt-[1.625rem]">
                        Clear filters
                    </Button>
                )}
            </div>
            <p role="status" className="sr-only">
                {status}
            </p>
        </div>
    );
}
