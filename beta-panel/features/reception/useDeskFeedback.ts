"use client";

import { useState } from "react";

/** Status/error banners shared by the desk's patient and booking flows. */
export function useDeskFeedback() {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  return { message, error, setMessage, setError };
}

export type DeskFeedback = ReturnType<typeof useDeskFeedback>;
