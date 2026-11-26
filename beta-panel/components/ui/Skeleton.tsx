export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`ds-skeleton ${className}`.trim()} aria-hidden="true" />;
}

/** Table/list placeholder that keeps layout stable while data loads. */
export function SkeletonRows({ rows = 5, testId = "skeleton" }: { rows?: number; testId?: string }) {
  return (
    <div className="ds-card space-y-3 p-4" role="status" aria-label="در حال بارگذاری" data-testid={testId}>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-9 w-full" />
      ))}
    </div>
  );
}
