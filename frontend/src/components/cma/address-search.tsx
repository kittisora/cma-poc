"use client";

import { useEffect, useRef, useState } from "react";
import { MarkerPin02 } from "@untitledui/icons";
import { useHotkeys } from "react-hotkeys-hook";
import { Select } from "@/components/base/select/select";
import { api } from "@/lib/api";
import { PROPERTY_TYPES } from "@/lib/format";
import type { SearchResult } from "@/lib/types";

interface Props {
    zips: string[];
    /** The subject currently analysed (also when chosen elsewhere, e.g. an example button). */
    current: SearchResult | null;
    onSelect: (r: SearchResult) => void;
}

const ALL = "all";

/** Address search: library ComboBox with server-side matching, plus a ZIP filter Select. ⌘K / Ctrl+K focuses it. */
export function AddressSearch({ zips, current, onSelect }: Props) {
    const [text, setText] = useState("");
    const [zip, setZip] = useState<string>(ALL);
    // Results are tagged with the text they answer, so stale results are never shown for new text.
    const [found, setFound] = useState<{ q: string; zip: string; results: SearchResult[] }>({ q: "", zip: ALL, results: [] });
    const results = found.q === text.trim() && found.zip === zip ? found.results : [];
    const [status, setStatus] = useState("");
    const skipNext = useRef(false);
    const wrapRef = useRef<HTMLDivElement>(null);

    // Show the current subject in the box when it was chosen outside the combobox (or after navigating back).
    const shownPin = useRef<string | null>(null);
    useEffect(() => {
        if (!current || shownPin.current === current.pin) return;
        shownPin.current = current.pin;
        const label = `${current.address}, ${current.zip}`;
        if (!text.toUpperCase().startsWith(current.address.toUpperCase())) {
            skipNext.current = true;
            setText(label);
        }
    }, [current]); // eslint-disable-line react-hooks/exhaustive-deps

    useHotkeys("mod+k", (e) => {
        e.preventDefault();
        wrapRef.current?.querySelector("input")?.focus();
    }, { enableOnFormTags: true });

    useEffect(() => {
        if (skipNext.current) {
            // The text was just filled in by choosing an option: keep that option's list current, don't search again.
            skipNext.current = false;
            setFound((f) => ({ ...f, q: text.trim() }));
            return;
        }
        const q = text.trim();
        if (q.length < 2) {
            setStatus("");
            return;
        }
        const ctrl = new AbortController();
        const t = setTimeout(() => {
            api.search(q, zip === ALL ? "" : zip, ctrl.signal)
                .then((r) => {
                    setFound({ q, zip, results: r.results });
                    setStatus(r.results.length ? `${r.results.length} addresses found` : "No matching address in the loaded ZIP codes");
                })
                .catch((e: Error) => {
                    if (e.name !== "AbortError") setStatus(`Search failed: ${e.message}`);
                });
        }, 180);
        return () => {
            clearTimeout(t);
            ctrl.abort();
        };
    }, [text, zip]);

    const items = results.map((r, i) => ({
        id: `${i}|${r.pin}`,
        label: r.address,
        supportingText: `${r.zip} · ${PROPERTY_TYPES[r.property_type ?? "OTHER"] ?? r.land_use ?? ""}`,
    }));

    return (
        <div className="flex w-full flex-col gap-1.5 sm:flex-row sm:items-end">
            <div ref={wrapRef} className="min-w-0 flex-1" data-testid="address-search">
                <Select.ComboBox
                    label="Subject address"
                    placeholder="e.g. 8069 Fairfax Rd"
                    items={items}
                    inputValue={text}
                    onInputChange={setText}
                    defaultFilter={() => true}
                    menuTrigger="input"
                    allowsCustomValue
                    allowsEmptyCollection
                    onSelectionChange={(key) => {
                        if (key === null) return;
                        const idx = Number(String(key).split("|")[0]);
                        const r = results[idx];
                        if (!r) return;
                        skipNext.current = true;
                        shownPin.current = r.pin; // the combobox already shows this choice
                        onSelect(r);
                    }}
                    hint={status && results.length === 0 && text.trim().length >= 2 ? status : undefined}
                >
                    {(item) => (
                        <Select.Item id={item.id} supportingText={item.supportingText} icon={MarkerPin02}>
                            {item.label}
                        </Select.Item>
                    )}
                </Select.ComboBox>
            </div>
            <Select
                label="ZIP"
                aria-label="ZIP code filter"
                className="sm:w-36"
                selectedKey={zip}
                onSelectionChange={(k) => setZip(String(k ?? ALL))}
                items={[{ id: ALL, label: "All ZIPs" }, ...zips.map((z) => ({ id: z, label: z }))]}
            >
                {(item) => <Select.Item id={item.id}>{item.label}</Select.Item>}
            </Select>
            <p role="status" className="sr-only">
                {status}
            </p>
        </div>
    );
}
