// web/app/api/generate/route.ts
import { NextResponse } from "next/server";

export const runtime = "nodejs";

const BACKEND_BASE =
  process.env.API_BASE_INTERNAL?.replace(/\/+$/, "") || "http://127.0.0.1:8000";

export async function POST(req: Request) {
  try {
    const body = await req.text();

    const upstream = await fetch(`${BACKEND_BASE}/generate`, {
      method: "POST",
      headers: {
        "content-type": req.headers.get("content-type") || "application/json",
      },
      body,
    });

    const text = await upstream.text();

    // Pass through status + body
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") || "application/json",
      },
    });
  } catch (e: any) {
    return NextResponse.json(
      {
        error: "Proxy to backend failed",
        detail: e?.message ?? String(e),
        backend: BACKEND_BASE,
      },
      { status: 502 }
    );
  }
}
