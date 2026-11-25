import { Skeleton, SkeletonRows } from "./Skeleton";

/** Title + toolbar + table placeholder with the same vertical rhythm as a loaded workspace. */
export function PageSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-5" role="status" aria-label="در حال بارگذاری" data-testid="page-skeleton">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-80 max-w-full" />
      </div>
      <Skeleton className="h-16 w-full" />
      <SkeletonRows rows={rows} testId="page-skeleton-rows" />
    </div>
  );
}
