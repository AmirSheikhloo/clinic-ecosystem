import { proxyV1 } from "@/lib/bff-proxy";

type Context = { params: Promise<{ path?: string[] }> };

async function handle(request: Request, context: Context) {
  const { path } = await context.params;
  return proxyV1(request, path);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
