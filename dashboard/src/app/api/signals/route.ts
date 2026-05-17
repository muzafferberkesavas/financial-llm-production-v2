import { NextResponse } from "next/server";
import { MOCK_SIGNALS } from "@/lib/mock-signals";

const BACKEND_URL = process.env.BACKEND_API_URL;

export async function GET() {
  if (BACKEND_URL) {
    try {
      const r = await fetch(`${BACKEND_URL}/signals/latest`, { cache: "no-store" });
      if (r.ok) {
        return NextResponse.json(await r.json());
      }
    } catch (e) {
      console.warn("backend unreachable, falling back to mock", e);
    }
  }
  return NextResponse.json({ signals: MOCK_SIGNALS });
}
