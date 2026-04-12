"use client";

import { useEffect, useState } from "react";
import { fetchCategories } from "@/lib/risk/client";
import type { HazardCategory } from "@/types";

const FALLBACK: HazardCategory[] = [
  { id: "all", label: "All hazards", description: "Aggregate risk layer" },
  { id: "violent", label: "Violent", description: "Murder, assault, robbery, weapons" },
  { id: "property", label: "Property", description: "Theft, burglary, larceny" },
  { id: "public_order", label: "Public order", description: "Harassment, trespass" },
  { id: "traffic_hazard", label: "Traffic", description: "Vision Zero + violations" },
  { id: "environmental", label: "Env", description: "311 streetlights, signals, noise" },
];

export function useCategories() {
  const [categories, setCategories] = useState<HazardCategory[]>(FALLBACK);

  useEffect(() => {
    let cancelled = false;
    fetchCategories()
      .then((data) => {
        if (!cancelled && Array.isArray(data) && data.length > 0) {
          setCategories(data as HazardCategory[]);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return categories;
}
