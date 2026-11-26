import { toLatinDigits } from "./format/digits";

/** Normalize Persian/Arabic digits and keep at most 10 ASCII digits (leading zeros preserved via pad on validate). */
export function normalizeNationalIdInput(value: string): string {
  return toLatinDigits(value).replace(/\D/g, "").slice(0, 10);
}

export function isValidNationalIdChecksum(value: string): boolean {
  const digits = normalizeNationalIdInput(value).padStart(10, "0");
  if (digits.length !== 10 || /^(\d)\1{9}$/.test(digits)) return false;
  let total = 0;
  for (let i = 0; i < 9; i++) total += Number(digits[i]) * (10 - i);
  const rem = total % 11;
  const check = Number(digits[9]);
  return rem < 2 ? check === rem : check === 11 - rem;
}
