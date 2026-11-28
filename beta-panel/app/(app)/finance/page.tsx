import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Suspense } from "react";
import { FinanceView } from "@/features/finance/FinanceView";

export default function FinancePage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <FinanceView />
    </Suspense>
  );
}
