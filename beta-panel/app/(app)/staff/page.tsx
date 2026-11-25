import { Suspense } from "react";
import { StaffView } from "@/features/staff/StaffView";

export default function StaffPage() {
  return (
    <Suspense fallback={null}>
      <StaffView />
    </Suspense>
  );
}
