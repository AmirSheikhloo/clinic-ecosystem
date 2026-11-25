import { Suspense } from "react";
import { CatalogView } from "@/features/catalog/CatalogView";

export default function CatalogPage() {
  return (
    <Suspense fallback={null}>
      <CatalogView />
    </Suspense>
  );
}
