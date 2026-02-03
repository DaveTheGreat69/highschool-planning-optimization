// web/app/api/health/route.ts
import { NextResponse } from "next/server";

export const runtime = "nodejs";

const BACKEND_BASE =
  process.env.API_BASE_INTERNAL?.replace(/\/+$/, "") || "http://127.0.0.1:8000";

export async function GET() {
  try {
    const upstream = await fetch(`${BACKEND_BASE}/health`);
    const data = await upstream.json();
    return NextResponse.json({ ok: true, backend: BACKEND_BASE, upstream: data });
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, backend: BACKEND_BASE, error: e?.message ?? String(e) },
      { status: 502 }
    );
  }
}
