import { NextResponse, type NextRequest } from "next/server";

// Pure pass-through middleware. DECK/01 is a single-tenant local-inference
// build — every route is public.
export async function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
