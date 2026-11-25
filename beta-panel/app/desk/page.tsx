import { Suspense } from "react";
import { DeskView } from "@/features/reception/DeskView";

export default function DeskPage() {
  return (
    <Suspense fallback={null}>
      <DeskView />
    </Suspense>
  );
}
