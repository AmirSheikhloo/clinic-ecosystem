import { EmptyState } from "./EmptyState";

export function AccessDenied({ what }: { what?: string }) {
  return (
    <div data-testid="access-denied" role="alert">
      <EmptyState
        icon="lock"
        title="دسترسی به این بخش مجاز نیست"
        description={
          what
            ? `برای ${what} مجوز لازم را ندارید. در صورت نیاز با مدیر کلینیک تماس بگیرید.`
            : "در صورت نیاز با مدیر کلینیک تماس بگیرید."
        }
      />
    </div>
  );
}
