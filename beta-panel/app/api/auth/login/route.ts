import { handleLoginPost } from "@/lib/bff-handlers";
import { cookiesFromRequest } from "@/lib/request-cookies";

export async function POST(request: Request) {
  return handleLoginPost(request, cookiesFromRequest(request));
}
