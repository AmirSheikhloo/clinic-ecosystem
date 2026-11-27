import { backendFetch } from "@/lib/session";

/** Proxies isolated-preview demo role catalog (empty when aliases disabled). */
export async function GET(request: Request) {
  const upstream = await backendFetch("/api/v1/auth/demo-aliases", {}, request);
  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") || "application/json" },
  });
}
