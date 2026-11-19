"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo } from "react";
import { Circle, CircleMarker, MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import { money } from "@/lib/format";
import type { Comp, Property } from "@/lib/types";

interface Props {
    subject: Property;
    comps: Comp[];
    radiusMiles: number;
    highlighted: number | null;
    onSelect: (saleId: number) => void;
}

const PIN = "flex items-center justify-center rounded-full font-bold text-white shadow-md ring-2 ring-white transition-transform";

const numberIcon = (n: number, highlighted: boolean) =>
    L.divIcon({
        className: "",
        html: `<span data-comp-pin="${n}" class="${PIN} size-[26px] text-xs ${highlighted ? "scale-125 bg-warning-solid" : "bg-brand-solid"}">${n}</span>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
    });

const subjectIcon = L.divIcon({
    className: "",
    html: `<span class="${PIN} size-[30px] bg-error-solid text-md">★</span>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
});

function FitBounds({ points }: { points: [number, number][] }) {
    const map = useMap();
    const key = JSON.stringify(points);
    useEffect(() => {
        if (points.length === 1) map.setView(points[0], 15);
        else if (points.length > 1) map.fitBounds(L.latLngBounds(points), { padding: [30, 30], maxZoom: 16 });
    }, [map, key]); // eslint-disable-line react-hooks/exhaustive-deps
    return null;
}

export default function CompMap({ subject, comps, radiusMiles, highlighted, onSelect }: Props) {
    const located = comps.filter((c) => c.lat !== null && c.lon !== null);
    const selected = located.filter((c) => c.selected);
    const selKey = selected.map((c) => c.sale_id).join(",");
    const points = useMemo<[number, number][]>(
        () => [[subject.lat!, subject.lon!], ...selected.map((c) => [c.lat!, c.lon!] as [number, number])],
        [subject.lat, subject.lon, selKey], // eslint-disable-line react-hooks/exhaustive-deps
    );

    if (subject.lat === null || subject.lon === null) {
        return (
            <div className="flex h-80 items-center justify-center rounded-xl bg-secondary text-sm text-tertiary ring-1 ring-secondary">
                The subject has no mapped address point.
            </div>
        );
    }
    const selIndex = new Map(selected.map((c, i) => [c.sale_id, i + 1]));

    return (
        <div
            className="isolate h-96 overflow-hidden rounded-xl shadow-xs ring-1 ring-secondary"
            role="region"
            aria-label="Map of the subject and comparable sales"
            data-testid="comp-map"
        >
            <MapContainer center={[subject.lat, subject.lon]} zoom={15} scrollWheelZoom={false} style={{ height: "100%" }}>
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <FitBounds points={points} />
                <Circle
                    center={[subject.lat, subject.lon]}
                    radius={radiusMiles * 1609.34}
                    pathOptions={{ color: "#206cdc", weight: 1, fillOpacity: 0.03, dashArray: "4 4" }}
                />
                {located
                    .filter((c) => !c.selected)
                    .map((c) => (
                        <CircleMarker
                            key={c.sale_id}
                            center={[c.lat!, c.lon!]}
                            radius={highlighted === c.sale_id ? 8 : 5}
                            pathOptions={{ color: highlighted === c.sale_id ? "#dc6803" : "#667085", weight: 2, fillOpacity: 0.5 }}
                            eventHandlers={{ click: () => onSelect(c.sale_id) }}
                        >
                            <Tooltip>
                                #{c.rank} {c.address} · {money(c.sale.price)} · {c.sale.sale_date} (not selected)
                            </Tooltip>
                        </CircleMarker>
                    ))}
                {selected.map((c) => (
                    <Marker
                        key={c.sale_id}
                        position={[c.lat!, c.lon!]}
                        icon={numberIcon(selIndex.get(c.sale_id)!, highlighted === c.sale_id)}
                        eventHandlers={{ click: () => onSelect(c.sale_id) }}
                        keyboard
                        title={`Comp ${selIndex.get(c.sale_id)}: ${c.address}`}
                        zIndexOffset={highlighted === c.sale_id ? 1000 : 0}
                    >
                        <Tooltip>
                            Comp {selIndex.get(c.sale_id)} · {c.address} · {money(c.sale.price)} · {c.sale.sale_date}
                        </Tooltip>
                    </Marker>
                ))}
                <Marker position={[subject.lat, subject.lon]} icon={subjectIcon} title={`Subject: ${subject.address}`} zIndexOffset={2000}>
                    <Tooltip>Subject · {subject.address}</Tooltip>
                </Marker>
            </MapContainer>
        </div>
    );
}
