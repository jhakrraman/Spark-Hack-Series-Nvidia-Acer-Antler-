import { NextRequest, NextResponse } from "next/server";

const POI_BRAIN_URL = process.env.POI_BRAIN_URL ?? "http://localhost:8080";

export const dynamic = "force-dynamic";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const res = await fetch(
      `${POI_BRAIN_URL}/risk/camera/${encodeURIComponent(id)}`,
      { cache: "no-store" }
    );
    if (!res.ok) {
      return NextResponse.json(
        { error: `poi-brain ${res.status}` },
        { status: res.status }
      );
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    return NextResponse.json(
      { error: (err as Error).message ?? "proxy failed" },
      { status: 502 }
    );
  }
}
