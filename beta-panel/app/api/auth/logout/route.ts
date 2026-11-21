import { handleLogoutPost } from "@/lib/bff-handlers";
import { cookiesFromRequest } from "@/lib/request-cookies";

export async function POST(request: Request) {
  return handleLogoutPost(request, cookiesFromRequest(request));
}
