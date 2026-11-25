import { Suspense } from "react";
import { AppointmentsView } from "@/features/appointments/AppointmentsView";

export default function AppointmentsPage() {
  return (
    <Suspense fallback={null}>
      <AppointmentsView />
    </Suspense>
  );
}
