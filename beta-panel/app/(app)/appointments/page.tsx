import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Suspense } from "react";
import { AppointmentsView } from "@/features/appointments/AppointmentsView";

export default function AppointmentsPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <AppointmentsView />
    </Suspense>
  );
}
