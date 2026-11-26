import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Suspense } from "react";
import { CatalogAdminView } from "@/features/catalog/admin/CatalogAdminView";

export default function CatalogManagePage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <CatalogAdminView />
    </Suspense>
  );
}
