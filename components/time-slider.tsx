"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface TimeSliderProps {
  /** 0-167 (Mon 00:00 .. Sun 23:00). undefined = use wall-clock / live mode. */
  value: number | undefined;
  onChange: (hourOfWeek: number | undefined) => void;
  className?: string;
}

const DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

function formatHour(hourOfWeek: number): { day: string; hour: string; label: string } {
  const h = ((hourOfWeek % 168) + 168) % 168;
  const day = DAYS[Math.floor(h / 24)];
  const hour = h % 24;
  const hourStr = `${String(hour).padStart(2, "0")}:00`;
  const ampm =
    hour === 0 ? "12 AM" : hour < 12 ? `${hour} AM` : hour === 12 ? "12 PM" : `${hour - 12} PM`;
  return { day, hour: hourStr, label: `${day} ${ampm}` };
}

function currentHourOfWeek(): number {
  const d = new Date();
  // JS: Sunday=0, Monday=1 … but our DAYS array is Mon-first.
  const jsDay = d.getDay();
  const monFirst = (jsDay + 6) % 7;
  return monFirst * 24 + d.getHours();
}

export function TimeSlider({ value, onChange, className }: TimeSliderProps) {
  const isLive = value === undefined;
  const displayValue = value ?? currentHourOfWeek();
  const { label } = useMemo(() => formatHour(displayValue), [displayValue]);

  return (
    <div
      className={cn(
        "pointer-events-auto flex flex-col gap-1 rounded-md border border-white/10 bg-black/70 px-3 py-2 backdrop-blur-md",
        className
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.18em] text-white/50">
          <span>when</span>
          <span
            className={cn(
              "text-[11px] font-bold tabular-nums",
              isLive ? "text-emerald-400" : "text-cyan-300"
            )}
          >
            {isLive ? "LIVE · NOW" : label}
          </span>
        </div>
        <button
          type="button"
          onClick={() => onChange(isLive ? currentHourOfWeek() : undefined)}
          className={cn(
            "rounded-sm border px-2 py-0.5 text-[8px] font-bold uppercase tracking-[0.16em] transition-colors",
            isLive
              ? "border-cyan-400/60 text-cyan-300 hover:bg-cyan-400/10"
              : "border-emerald-400/60 text-emerald-400 hover:bg-emerald-400/10"
          )}
        >
          {isLive ? "scrub" : "go live"}
        </button>
      </div>
      <input
        type="range"
        min={0}
        max={167}
        step={1}
        value={displayValue}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={isLive}
        className={cn(
          "h-1 w-full appearance-none rounded-full bg-white/10",
          "[&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3",
          "[&::-webkit-slider-thumb]:appearance-none",
          "[&::-webkit-slider-thumb]:rounded-full",
          "[&::-webkit-slider-thumb]:border [&::-webkit-slider-thumb]:border-cyan-300",
          "[&::-webkit-slider-thumb]:bg-cyan-300",
          "[&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(103,232,249,0.8)]",
          "[&::-webkit-slider-thumb]:cursor-pointer",
          isLive && "opacity-40"
        )}
      />
      <div className="flex justify-between text-[7px] font-bold uppercase tracking-widest text-white/30">
        {DAYS.map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>
    </div>
  );
}
