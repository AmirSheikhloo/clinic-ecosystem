import { Suspense } from "react";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { PatientsView } from "@/features/patients/PatientsView";

export default function PatientsPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <PatientsView />
    </Suspense>
  );
}
