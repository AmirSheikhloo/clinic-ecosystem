import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Suspense } from "react";
import { OpsConfigView } from "@/features/ops/OpsConfigView";

export default function OpsPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <OpsConfigView />
    </Suspense>
  );
}
