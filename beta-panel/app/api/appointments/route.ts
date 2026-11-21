import { cookies } from "next/headers";
import { handleAppointmentsGet, handleAppointmentsPost } from "@/lib/bff-handlers";

export async function GET(request: Request) {
  const jar = await cookies();
  return handleAppointmentsGet(request, jar);
}

export async function POST(request: Request) {
  const jar = await cookies();
  return handleAppointmentsPost(request, jar);
}
