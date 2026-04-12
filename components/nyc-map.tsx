"use client";

import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import type { NyctmcCamera } from "@/lib/nyctmc";
import "leaflet/dist/leaflet.css";

/**
 * DECK/01 tactical NYC map. Dark Carto tiles + amber DivIcon markers.
 * Renders a marker for every camera with valid coordinates and fires
 * `onSelect` when the operator clicks one.
 */

interface NycMapProps {
  cameras: NyctmcCamera[];
  selectedId?: string | null;
  onSelect: (camera: NyctmcCamera) => void;
}

// Manhattan centroid — good default view for NYC camera coverage.
const DEFAULT_CENTER: [number, number] = [40.7549, -73.975];
const DEFAULT_ZOOM = 12;

/** Recenter the map on the currently-selected camera without losing zoom. */
function Recenter({ lat, lng }: { lat: number | null; lng: number | null }) {
  const map = useMap();
  useEffect(() => {
    if (lat != null && lng != null && Number.isFinite(lat) && Number.isFinite(lng)) {
      map.flyTo([lat, lng], Math.max(map.getZoom(), 14), { duration: 0.6 });
    }
  }, [lat, lng, map]);
  return null;
}

/** Build a tactical amber dot marker for each camera. */
function buildIcon(active: boolean): L.DivIcon {
  const size = active ? 18 : 12;
  const html = `
    <div style="
      width:${size}px;
      height:${size}px;
      border-radius:999px;
      background:${active ? "#ffb81c" : "rgba(255,184,28,0.85)"};
      box-shadow:
        0 0 0 1.5px rgba(8,8,10,0.9),
        0 0 10px ${active ? "#ffb81c" : "rgba(255,184,28,0.6)"},
        0 0 2px #ffb81c;
      transition: all 160ms ease-out;
    "></div>`;
  return L.divIcon({
    html,
    className: "deck-map-marker",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

export default function NycMap({ cameras, selectedId, onSelect }: NycMapProps) {
  // Only draw markers for cameras that have real coordinates.
  const locatable = useMemo(
    () =>
      cameras.filter(
        (c) =>
          c.latitude != null &&
          c.longitude != null &&
          Number.isFinite(c.latitude) &&
          Number.isFinite(c.longitude)
      ),
    [cameras]
  );

  const selected = selectedId ? locatable.find((c) => c.id === selectedId) : undefined;

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        scrollWheelZoom
        zoomControl={false}
        className="h-full w-full"
        style={{ background: "rgb(8 8 10)" }}
      >
        <TileLayer
          // Carto Dark Matter — no API key, matches DECK aesthetic.
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          subdomains={["a", "b", "c", "d"]}
          maxZoom={19}
        />
        {locatable.map((camera) => {
          const isActive = camera.id === selectedId;
          return (
            <Marker
              key={camera.id}
              position={[camera.latitude as number, camera.longitude as number]}
              icon={buildIcon(isActive)}
              eventHandlers={{
                click: () => onSelect(camera),
              }}
            />
          );
        })}
        <Recenter lat={selected?.latitude ?? null} lng={selected?.longitude ?? null} />
      </MapContainer>
    </div>
  );
}
