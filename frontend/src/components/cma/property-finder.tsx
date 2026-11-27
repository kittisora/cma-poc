"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Home02, List, XClose } from "@untitledui/icons";
import { useHotkeys } from "react-hotkeys-hook";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { Select } from "@/components/base/select/select";
import { type AreaFilter, api } from "@/lib/api";
import { PROPERTY_TYPES } from "@/lib/format";
import type { SearchResult } from "@/lib/types";
import { cx } from "@/utils/cx";
import { AreaFilters, hasAreaFilter } from "./area-filters";
import { PermitStageBadge } from "./permit-badge";

interface Props {
    /** The subject currently analysed (also when chosen elsewhere, e.g. an example button). */
    current: SearchResult | null;
    onSelect: (r: SearchResult) => void;
}

const typeLabel = (r: SearchResult) => PROPERTY_TYPES[r.property_type ?? "OTHER"] ?? r.land_use ?? "";

/**
 * Find the subject by Subdivision → Block → Streets (several at once), then pick the property from the
 * box or from the full list of addresses. ⌘K / Ctrl+K focuses the subdivision box.
 */
export function PropertyFinder({ current, onSelect }: Props) {
    const [area, setArea] = useState<AreaFilter>({ subdivision: null, block: null, streets: [] });
    const [found, setFound] = useState<{ key: string; total: number; results: SearchResult[] }>({ key: "", total: 0, results: [] });
    const [status, setStatus] = useState("");
    const [showList, setShowList] = useState(false);
    const [resetKey, setResetKey] = useState(0);
    const wrapRef = useRef<HTMLDivElement>(null);

    useHotkeys(
        "mod+k",
        (e) => {
            e.preventDefault();
            wrapRef.current?.querySelector("input")?.focus();
        },
        { enableOnFormTags: true },
    );

    const key = JSON.stringify(area);
    const hasFilter = hasAreaFilter(area);
    useEffect(() => {
        if (!hasFilter) {
            setStatus("");
            return;
        }
        const ctrl = new AbortController();
        api.properties(area, ctrl.signal)
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

    const results = useMemo(() => (found.key === key ? found.results : []), [found, key]);
    const multiStreet = (area.streets?.length ?? 0) !== 1;
    const propertyItems = useMemo(
        () =>
            results.map((r, i) => ({
                id: `${i}|${r.pin}`,
                label: r.address,
                supportingText: [
                    r.zip,
                    typeLabel(r),
                    r.lot ? `Lot ${r.lot}` : "",
                    r.block ? `Blk ${r.block}` : "",
                    !area.subdivision && r.subdivision ? r.subdivision : "",
                    r.permit_stage === "active" ? "permit issued" : r.permit_stage === "pending" ? "permit in review" : "",
                ]
                    .filter(Boolean)
                    .join(" · "),
            })),
        [results, area.subdivision],
    );
    const currentId = current ? propertyItems.find((it) => it.id.endsWith(`|${current.pin}`))?.id : undefined;
    const withPermits = results.filter((r) => r.permit_stage === "active" || r.permit_stage === "pending").length;

    const clear = () => {
        setArea({ subdivision: null, block: null, streets: [] });
        setResetKey((k) => k + 1);
        setShowList(false);
    };

    return (
        <div ref={wrapRef} className="flex w-full flex-col gap-3" data-testid="property-finder">
            <AreaFilters value={area} onChange={setArea} resetKey={resetKey} />
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
                    <div className="flex gap-2 sm:mt-[1.625rem]">
                        <Button
                            size="md"
                            color="secondary"
                            iconLeading={List}
                            iconTrailing={showList ? ChevronUp : ChevronDown}
                            aria-expanded={showList}
                            isDisabled={results.length === 0}
                            onClick={() => setShowList(!showList)}
                        >
                            {showList ? "Hide addresses" : `List all ${results.length.toLocaleString()}`}
                        </Button>
                        <Button size="md" color="secondary" iconLeading={XClose} onClick={clear}>
                            Clear filters
                        </Button>
                    </div>
                )}
            </div>
            {showList && results.length > 0 && (
                <div className="flex flex-col gap-2">
                    <p className="text-xs text-tertiary">
                        {results.length.toLocaleString()} addresses
                        {withPermits > 0 && ` · ${withPermits} with an open permit (issued or in review)`}. Click one to analyse it.
                    </p>
                    <div className="max-h-80 overflow-auto rounded-lg ring-1 ring-secondary" data-testid="address-list">
                        <table className="w-full text-sm">
                            <caption className="sr-only">Addresses matching the filters</caption>
                            <thead className="sticky top-0 z-10 bg-secondary text-xs text-tertiary">
                                <tr>
                                    <th scope="col" className="px-3 py-2 text-left font-medium">
                                        Address
                                    </th>
                                    {multiStreet && (
                                        <th scope="col" className="px-3 py-2 text-left font-medium max-md:hidden">
                                            Street
                                        </th>
                                    )}
                                    <th scope="col" className="px-3 py-2 text-left font-medium">
                                        Lot / block
                                    </th>
                                    <th scope="col" className="px-3 py-2 text-left font-medium max-sm:hidden">
                                        Type
                                    </th>
                                    <th scope="col" className="px-3 py-2 text-left font-medium">
                                        Permits
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-secondary">
                                {results.map((r) => (
                                    <tr
                                        key={`${r.pin}-${r.address}`}
                                        className={cx("cursor-pointer hover:bg-primary_hover", current?.pin === r.pin && "bg-brand-primary_alt")}
                                        onClick={() => onSelect(r)}
                                    >
                                        <th scope="row" className="px-3 py-1.5 text-left font-medium text-primary">
                                            <button
                                                type="button"
                                                className="text-left outline-focus-ring hover:underline focus-visible:outline-2"
                                                onClick={() => onSelect(r)}
                                            >
                                                {r.address}
                                            </button>
                                            {current?.pin === r.pin && (
                                                <Badge type="pill-color" color="brand" size="sm" className="ml-2">
                                                    Subject
                                                </Badge>
                                            )}
                                        </th>
                                        {multiStreet && <td className="px-3 py-1.5 text-tertiary max-md:hidden">{r.street}</td>}
                                        <td className="px-3 py-1.5 whitespace-nowrap text-tertiary">
                                            {[r.lot && `Lot ${r.lot}`, r.block && `Blk ${r.block}`].filter(Boolean).join(" · ") || "—"}
                                        </td>
                                        <td className="px-3 py-1.5 text-tertiary max-sm:hidden">{typeLabel(r)}</td>
                                        <td className="px-3 py-1.5">
                                            {r.permit_stage ? <PermitStageBadge stage={r.permit_stage} /> : <span className="text-quaternary">—</span>}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
            <p role="status" className="sr-only">
                {status}
            </p>
        </div>
    );
}
