/** Configurable Persian insurance catalog for reception identity (PAT-02 / Task 34 §13). */

export type InsuranceCatalogEntry = {
  code: string;
  nameFa: string;
  coverageKind: "BASIC" | "SUPPLEMENTARY" | "NONE" | "UNKNOWN";
  clinicContractActive: boolean;
};

/** Seed catalog — replaceable by GET insurance catalog when disposable schema is wired. */
export const PERSIAN_INSURANCE_CATALOG: InsuranceCatalogEntry[] = [
  { code: "NONE", nameFa: "بدون بیمه / آزاد", coverageKind: "NONE", clinicContractActive: true },
  { code: "TAMIN", nameFa: "تأمین اجتماعی", coverageKind: "BASIC", clinicContractActive: true },
  { code: "SALAMAT", nameFa: "بیمه سلامت ایرانیان", coverageKind: "BASIC", clinicContractActive: true },
  { code: "NIROO", nameFa: "نیروهای مسلح", coverageKind: "BASIC", clinicContractActive: true },
  { code: "BANK_MELLI", nameFa: "بیمه بانک ملی", coverageKind: "SUPPLEMENTARY", clinicContractActive: true },
  { code: "ASIA", nameFa: "بیمه آسیا (تکمیلی)", coverageKind: "SUPPLEMENTARY", clinicContractActive: true },
  { code: "DANA", nameFa: "بیمه دانا (تکمیلی)", coverageKind: "SUPPLEMENTARY", clinicContractActive: false },
  { code: "ALBORZ", nameFa: "بیمه البرز (تکمیلی)", coverageKind: "SUPPLEMENTARY", clinicContractActive: true },
  { code: "OTHER", nameFa: "سایر / نامشخص", coverageKind: "UNKNOWN", clinicContractActive: false },
];

export function insuranceLabel(code: string | null | undefined): string {
  if (!code) return "بیمه نامشخص";
  return PERSIAN_INSURANCE_CATALOG.find((e) => e.code === code)?.nameFa ?? code;
}
