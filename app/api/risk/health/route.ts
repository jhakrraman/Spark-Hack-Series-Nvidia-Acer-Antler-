import { NextResponse } from "next/server";

const POI_BRAIN_URL = process.env.POI_BRAIN_URL ?? "http://localhost:8080";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch(`${POI_BRAIN_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, status: res.status },
        { status: 200 }
      );
    }
    return NextResponse.json({ ok: true, ...(await res.json()) });
  } catch (err) {
    return NextResponse.json(
      { ok: false, error: (err as Error).message ?? "unreachable" },
      { status: 200 }
    );
  }
}
