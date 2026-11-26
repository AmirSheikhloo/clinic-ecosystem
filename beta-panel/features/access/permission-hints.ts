/** Persian explanations shown under permission labels; the API only carries English descriptions. */
const HINTS: Record<string, string> = {
  BETA02_PATIENTS_SEARCH: "جستجو و دیدن فهرست بیماران",
  BETA02_PATIENTS_REGISTER: "ثبت بیمار تازه با اطلاعات هویتی اولیه",
  BETA02_PATIENTS_VIEW_PROFILE: "باز کردن پروندهٔ اداری بیمار",
  BETA02_PATIENTS_UPDATE: "ویرایش نام، تاریخ تولد و شمارهٔ پرونده",
  BETA02_PATIENTS_SET_ACTIVE: "کنار گذاشتن بیمار از نوبت‌دهی یا بازگرداندن او",
  BETA02_PATIENTS_VIEW_HISTORY: "دیدن سابقهٔ نوبت‌های یک بیمار",
  BETA02_STAFF_VIEW: "دیدن فهرست کارکنان و ارائه‌دهندگان",
  BETA02_STAFF_MANAGE: "افزودن، ویرایش و فعال/غیرفعال کردن پروفایل کارمندی",
  BETA02_STAFF_PROVISION_LOGIN: "ساخت حساب ورود اختیاری برای یک کارمند",
  BETA02_ACCOUNTS_VIEW: "دیدن حساب‌های ورود و وضعیت آن‌ها",
  BETA02_ACCOUNTS_SET_ACTIVE: "معلق کردن یا دوباره فعال کردن یک حساب",
  BETA02_ROLES_VIEW: "دیدن نقش‌ها و دسترسی مؤثر هر حساب",
  BETA02_ROLES_MANAGE: "ساخت نقش و تعیین مجوزهای آن",
  BETA02_USER_ROLES_ASSIGN: "اختصاص نقش به حساب‌ها",
  BETA02_GOVERNANCE_VIEW: "دیدن مالک، مدیر و معاونان",
  BETA02_GOVERNANCE_MANAGE: "تعیین مالک، مدیر و معاون",
  BETA02_CATALOG_SERVICES_READ: "دیدن خدمت‌های فعال",
  BETA02_CATALOG_RESOURCES_READ: "دیدن منابع فعال",
  BETA02_CATALOG_SERVICES_MANAGE: "ساخت و ویرایش خدمت، تعرفه و الزامات",
  BETA02_CATALOG_RESOURCES_MANAGE: "ساخت و ویرایش منابع",
  BETA02_APPOINTMENTS_LIST: "دیدن تقویم و فهرست نوبت‌ها",
  BETA02_APPOINTMENTS_VIEW_DETAILS: "باز کردن جزئیات یک نوبت",
  BETA02_APPOINTMENTS_SCHEDULE_MANUAL: "ثبت نوبت از میز پذیرش",
  ALLOW_MANUAL_OVERBOOKING: "ثبت نوبت دستی با وجود هم‌پوشانی، پس از تأیید آگاهانه",
  BETA02_APPOINTMENTS_CANCEL: "لغو نوبت‌های دستی",
  BETA02_APPOINTMENTS_RESCHEDULE: "تغییر زمان نوبت‌های دستی",
  BETA02_APPOINTMENTS_CHECK_IN: "ثبت حضور بیمار برای نوبت تأییدشده",
  BETA02_APPOINTMENTS_COMPLETE: "اتمام نوبت پس از حضور",
  BETA02_APPOINTMENTS_MARK_NO_SHOW: "ثبت عدم حضور پس از زمان شروع",
  BETA02_AUDIT_VIEW: "مشاهده گزارش حسابرسی عملیات (فقط خواندن، بدون تغییر)",
};

export function permissionHint(code: string): string | undefined {
  return HINTS[code];
}
