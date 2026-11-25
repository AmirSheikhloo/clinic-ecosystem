import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Suspense } from "react";
import { DeskView } from "@/features/reception/DeskView";

export default function DeskPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <DeskView />
    </Suspense>
  );
}
