import { cookies } from "next/headers";
import { handleLoginPost } from "@/lib/bff-handlers";

export async function POST(request: Request) {
  const jar = await cookies();
  return handleLoginPost(request, jar);
}
