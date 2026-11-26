/** Latin digit display and controlled Persian/Arabic-Indic input normalization. */

const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";

/** Ensure a display string uses only ASCII Latin digits 0–9. */
export function toLatinDigits(value: string): string {
  let out = "";
  for (const ch of value) {
    const p = PERSIAN_DIGITS.indexOf(ch);
    if (p >= 0) {
      out += String(p);
      continue;
    }
    const a = ARABIC_INDIC_DIGITS.indexOf(ch);
    if (a >= 0) {
      out += String(a);
      continue;
    }
    out += ch;
  }
  return out;
}

/** Normalize user input that may contain Persian/Arabic-Indic digits to Latin. */
export function normalizeInputDigits(value: string): string {
  return toLatinDigits(value);
}

/** True when the string still contains Persian or Arabic-Indic digits. */
export function containsNonLatinDigits(value: string): boolean {
  for (const ch of value) {
    if (PERSIAN_DIGITS.includes(ch) || ARABIC_INDIC_DIGITS.includes(ch)) {
      return true;
    }
  }
  return false;
}
