import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Suspense } from "react";
import { WaitlistView } from "@/features/waitlist/WaitlistView";

export default function WaitlistPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <WaitlistView />
    </Suspense>
  );
}
