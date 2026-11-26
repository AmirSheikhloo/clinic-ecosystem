import { handleCsrfGet } from "@/lib/bff-handlers";

export async function GET(request: Request) {
  return handleCsrfGet(request);
}
