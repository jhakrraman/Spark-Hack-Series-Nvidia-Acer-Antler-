import { NextResponse } from "next/server";

const POI_BRAIN_URL = process.env.POI_BRAIN_URL ?? "http://localhost:8080";

export async function GET() {
  try {
    const res = await fetch(`${POI_BRAIN_URL}/cameras`, { cache: "no-store" });
    if (!res.ok) {
      return NextResponse.json(
        { error: `poi-brain ${res.status}`, detail: await res.text() },
        { status: res.status }
      );
    }
    return NextResponse.json(await res.json(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (err) {
    return NextResponse.json(
      { error: (err as Error).message ?? "proxy failed" },
      { status: 502 }
    );
  }
}
