import { cookies } from "next/headers";
import { handleLogoutPost } from "@/lib/bff-handlers";

export async function POST(request: Request) {
  const jar = await cookies();
  return handleLogoutPost(request, jar);
}
