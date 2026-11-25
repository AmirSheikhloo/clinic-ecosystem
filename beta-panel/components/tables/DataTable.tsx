import type { ReactNode } from "react";

export type DataTableColumn<T> = {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  rowTestId?: string;
  empty?: ReactNode;
};

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  rowTestId,
  empty,
}: DataTableProps<T>) {
  if (!rows.length) {
    return <>{empty}</>;
  }

  return (
    <div className="ds-card overflow-x-auto p-0">
      <table className="ds-table min-w-full">
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
