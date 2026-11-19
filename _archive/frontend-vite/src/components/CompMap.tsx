import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo } from "react";
import { Circle, CircleMarker, MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import { money } from "../format";
import type { Comp, Property } from "../types";

interface Props {
  subject: Property;
  comps: Comp[];
  radiusMiles: number;
  highlighted: number | null;
  onSelect: (saleId: number) => void;
}

const numberIcon = (n: number, selected: boolean, highlighted: boolean) =>
  L.divIcon({
    className: "",
    html: `<span class="pin ${selected ? "pin-sel" : "pin-cand"} ${highlighted ? "pin-hi" : ""}">${n}</span>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 15);
    else if (points.length > 1) map.fitBounds(L.latLngBounds(points), { padding: [30, 30], maxZoom: 16 });
  }, [map, JSON.stringify(points)]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

export function CompMap({ subject, comps, radiusMiles, highlighted, onSelect }: Props) {
  const located = comps.filter((c) => c.lat !== null && c.lon !== null);
  const selected = located.filter((c) => c.selected);
  const points = useMemo<[number, number][]>(
    () => [[subject.lat!, subject.lon!], ...selected.map((c) => [c.lat!, c.lon!] as [number, number])],
    [subject.lat, subject.lon, selected.map((c) => c.sale_id).join(",")], // eslint-disable-line react-hooks/exhaustive-deps
  );
  if (subject.lat === null || subject.lon === null) {
    return <div className="map map-empty">The subject has no mapped address point.</div>;
  }
  const selIndex = new Map(selected.map((c, i) => [c.sale_id, i + 1]));
  return (
    <div className="map" role="region" aria-label="Map of the subject and comparable sales">
      <MapContainer center={[subject.lat, subject.lon]} zoom={15} scrollWheelZoom={false} style={{ height: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={points} />
        <Circle
          center={[subject.lat, subject.lon]}
          radius={radiusMiles * 1609.34}
          pathOptions={{ color: "#1F4E79", weight: 1, fillOpacity: 0.03, dashArray: "4 4" }}
        />
        {located
          .filter((c) => !c.selected)
          .map((c) => (
            <CircleMarker
              key={c.sale_id}
              center={[c.lat!, c.lon!]}
              radius={highlighted === c.sale_id ? 8 : 5}
              pathOptions={{ color: highlighted === c.sale_id ? "#B45309" : "#6B7280", weight: 2, fillOpacity: 0.5 }}
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
            icon={numberIcon(selIndex.get(c.sale_id)!, true, highlighted === c.sale_id)}
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
        <Marker
          position={[subject.lat, subject.lon]}
          icon={L.divIcon({ className: "", html: '<span class="pin pin-subject">★</span>', iconSize: [30, 30], iconAnchor: [15, 15] })}
          title={`Subject: ${subject.address}`}
          zIndexOffset={2000}
        >
          <Tooltip>Subject · {subject.address}</Tooltip>
        </Marker>
      </MapContainer>
    </div>
  );
}
