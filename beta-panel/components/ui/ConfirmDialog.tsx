"use client";

import type { ReactNode } from "react";
import { Button } from "./Button";
import { Dialog } from "./Dialog";

type Props = {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: "primary" | "danger";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  testId?: string;
};

/** Explicit confirmation step for sensitive changes. Confirm is never the initial focus target. */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel = "انصراف",
  tone = "primary",
  busy = false,
  onConfirm,
  onCancel,
  testId = "confirm-dialog",
}: Props) {
  return (
    <Dialog
      open={open}
      title={title}
      onClose={onCancel}
      testId={testId}
      footer={
        <>
          <Button variant="ghost" onClick={onCancel} disabled={busy} data-testid={`${testId}-cancel`}>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === "danger" ? "danger-solid" : "primary"}
            onClick={onConfirm}
            loading={busy}
            data-testid={`${testId}-confirm`}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="space-y-2 text-sm leading-7">{children}</div>
    </Dialog>
  );
}
