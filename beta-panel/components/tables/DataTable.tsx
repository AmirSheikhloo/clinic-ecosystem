import type { ReactNode } from "react";

export type DataTableColumn<T> = {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
  /** CSS width for the fixed table layout (e.g. "9rem"); unset columns share the remaining space. */
  width?: string;
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  rowTestId?: string;
  empty?: ReactNode;
  /** Rows are being refreshed or belong to a previous filter: dim them and mark the region busy. */
  busy?: boolean;
  /** Minimum table width before the card scrolls horizontally. */
  minWidth?: string;
};

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  rowTestId,
  empty,
  busy = false,
  minWidth = "40rem",
}: DataTableProps<T>) {
  if (!rows.length) {
    return <>{empty}</>;
  }
  const fixed = columns.some((column) => column.width);

  return (
    <div className="ds-card ds-table-wrap p-0" aria-busy={busy || undefined} data-busy={busy || undefined}>
      <table className={`ds-table ${fixed ? "ds-table-fixed" : ""}`.trim()} style={{ minWidth }}>
        <colgroup>
          {columns.map((column) => (
            <col key={column.key} style={column.width ? { width: column.width } : undefined} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} data-testid={rowTestId}>
              {columns.map((column) => (
                <td key={column.key} className={column.className}>
                  {column.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
