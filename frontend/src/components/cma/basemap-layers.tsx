"use client";

import { LayersControl, TileLayer, useMapEvents } from "react-leaflet";

/**
 * Base maps offered on every map, including Fairfax County's zoning maps (the same tile services as the
 * county's "Infill & Conservation Plan Viewer"). The choice is remembered in this browser.
 */
const FAIRFAX = "https://www.fairfaxcounty.gov/gispub2/rest/services/GIS";
const FAIRFAX_ATTRIBUTION = 'Zoning &amp; property: <a href="https://www.fairfaxcounty.gov/maps/" target="_blank" rel="noreferrer">Fairfax County GIS</a>';

export const BASEMAPS = [
    {
        name: "Street map",
        url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxNativeZoom: 19,
    },
    {
        name: "Fairfax zoning (fill) with property",
        url: `${FAIRFAX}/ZoningFillwithProperty_Basemap/MapServer/tile/{z}/{y}/{x}`,
        attribution: FAIRFAX_ATTRIBUTION,
        maxNativeZoom: 19,
    },
    {
        name: "Fairfax zoning (edge) with property",
        url: `${FAIRFAX}/ZoningEdgewithProperty_Basemap/MapServer/tile/{z}/{y}/{x}`,
        attribution: FAIRFAX_ATTRIBUTION,
        maxNativeZoom: 19,
    },
    {
        name: "Aerial imagery",
        url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics",
        maxNativeZoom: 19,
    },
] as const;

const KEY = "cma.basemap";

function readChoice(): string {
    try {
        const v = window.localStorage.getItem(KEY);
        if (v && BASEMAPS.some((b) => b.name === v)) return v;
    } catch {
        /* storage unavailable */
    }
    return BASEMAPS[0].name;
}

function RememberChoice() {
    useMapEvents({
        baselayerchange: (e) => {
            try {
                window.localStorage.setItem(KEY, e.name);
            } catch {
                /* storage unavailable */
            }
        },
    });
    return null;
}

/** Drop inside a <MapContainer>: a layer switcher (top right) with the base maps above. */
export function BasemapLayers() {
    const chosen = readChoice();
    return (
        <>
            <LayersControl position="topright">
                {BASEMAPS.map((b) => (
                    <LayersControl.BaseLayer key={b.name} name={b.name} checked={b.name === chosen}>
                        <TileLayer url={b.url} attribution={b.attribution} maxNativeZoom={b.maxNativeZoom} maxZoom={21} />
                    </LayersControl.BaseLayer>
                ))}
            </LayersControl>
            <RememberChoice />
        </>
    );
}
