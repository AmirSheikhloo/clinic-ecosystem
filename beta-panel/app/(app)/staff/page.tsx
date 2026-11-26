import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Suspense } from "react";
import { StaffView } from "@/features/staff/StaffView";

export default function StaffPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <StaffView />
    </Suspense>
  );
}
