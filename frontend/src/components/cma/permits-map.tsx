"use client";

import { useEffect } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Tooltip, useMap } from "react-leaflet";
import type { Permit } from "@/lib/types";
import { BasemapLayers } from "./basemap-layers";
import { STAGE_HEX, STAGE_LABEL } from "./permit-badge";

function Fit({ points }: { points: [number, number][] }) {
    const map = useMap();
    const key = JSON.stringify(points.slice(0, 400));
    useEffect(() => {
        if (points.length === 1) map.setView(points[0], 17);
        else if (points.length > 1) map.fitBounds(L.latLngBounds(points), { padding: [30, 30], maxZoom: 17 });
    }, [map, key]); // eslint-disable-line react-hooks/exhaustive-deps
    return null;
}

/** One marker per parcel, coloured by its most significant permit stage. */
export default function PermitsMap({ permits, onSelect }: { permits: Permit[]; onSelect?: (pin: string) => void }) {
    const rank = { active: 0, pending: 1, completed: 2, stale: 3, inactive: 4 } as const;
    const byPin = new Map<string, Permit[]>();
    for (const p of permits) if (p.lat != null && p.lon != null && p.pin) byPin.set(p.pin, [...(byPin.get(p.pin) ?? []), p]);
    const parcels = [...byPin.values()].map((ps) => [...ps].sort((a, b) => rank[a.stage] - rank[b.stage]));
    const points = parcels.map((ps) => [ps[0].lat!, ps[0].lon!] as [number, number]);

    return (
        <div
            className="isolate h-[28rem] overflow-hidden rounded-xl shadow-xs ring-1 ring-secondary"
            role="region"
            aria-label="Map of permits"
            data-testid="permits-map"
        >
            <MapContainer center={[38.74, -77.06]} zoom={13} scrollWheelZoom={false} style={{ height: "100%" }}>
                <BasemapLayers />
                <Fit points={points} />
                {parcels
                    .slice()
                    .reverse()
                    .map((ps) => {
                        const top = ps[0];
                        return (
                            <CircleMarker
                                key={top.pin}
                                center={[top.lat!, top.lon!]}
                                radius={top.new_construction ? 8 : 6}
                                pathOptions={{ color: "#fff", weight: 1.5, fillColor: STAGE_HEX[top.stage], fillOpacity: 0.9 }}
                                eventHandlers={{ click: () => top.pin && onSelect?.(top.pin) }}
                            >
                                <Tooltip>
                                    <strong>{top.site_address ?? top.address}</strong>
                                    {ps.slice(0, 4).map((p) => (
                                        <div key={p.record_id}>
                                            {p.type} · {STAGE_LABEL[p.stage]}
                                            {p.issued
                                                ? ` · ${p.kind === "site" ? "approved" : "issued"} ${p.issued}`
                                                : p.submitted
                                                  ? ` · submitted ${p.submitted}`
                                                  : ""}
                                        </div>
                                    ))}
                                    {ps.length > 4 && <div>+{ps.length - 4} more</div>}
                                </Tooltip>
                            </CircleMarker>
                        );
                    })}
            </MapContainer>
        </div>
    );
}
