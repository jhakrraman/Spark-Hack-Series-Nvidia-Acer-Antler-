import { NextRequest, NextResponse } from "next/server";

const POI_BRAIN_URL = process.env.POI_BRAIN_URL ?? "http://localhost:8080";

const FORWARD_PARAMS = ["resolution", "category", "hour_of_week", "top"] as const;

export async function GET(req: NextRequest) {
  const params = new URLSearchParams();
  for (const key of FORWARD_PARAMS) {
    const val = req.nextUrl.searchParams.get(key);
    if (val !== null) params.set(key, val);
  }
  if (!params.has("resolution")) params.set("resolution", "9");
  try {
    const res = await fetch(
      `${POI_BRAIN_URL}/risk/heatmap?${params.toString()}`,
      { cache: "no-store" }
    );
    if (!res.ok) {
      return NextResponse.json(
        { error: `poi-brain ${res.status}`, detail: await res.text() },
        { status: res.status }
      );
    }
    const data = await res.json();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (err) {
    return NextResponse.json(
      { error: (err as Error).message ?? "proxy failed" },
      { status: 502 }
    );
  }
}
