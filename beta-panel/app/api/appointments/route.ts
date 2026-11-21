import { handleAppointmentsGet, handleAppointmentsPost } from "@/lib/bff-handlers";
import { cookiesFromRequest } from "@/lib/request-cookies";

export async function GET(request: Request) {
  return handleAppointmentsGet(request, cookiesFromRequest(request));
}

export async function POST(request: Request) {
  return handleAppointmentsPost(request, cookiesFromRequest(request));
}
