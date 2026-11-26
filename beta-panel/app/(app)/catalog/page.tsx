import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Suspense } from "react";
import { CatalogView } from "@/features/catalog/CatalogView";

export default function CatalogPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <CatalogView />
    </Suspense>
  );
}
