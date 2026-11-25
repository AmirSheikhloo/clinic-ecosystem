/**
 * Operations admin workflows (staff, access, catalog) against real BFF + API + PG15.
 * Synthetic data only; no mocked responses.
 */
import { expect, test } from "@playwright/test";
import { assertNoNonLatinDigits } from "./helpers";
import { RUN, credsFromEnv, expectToast, gotoNav, loginAs } from "./ops-helpers";

test.describe.configure({ mode: "serial" });

const staffLast = `Ops${RUN}`;
const loginName = `ops.user.${RUN}`;
const roleCode = `E2E_ROLE_${RUN}`;

test("manager: staff directory create, login provisioning is opt-in, edit, deactivate", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await gotoNav(page, "کارکنان", "staff-page");

  await page.getByTestId("staff-add").click();
  await expect(page.getByTestId("staff-form-dialog")).toBeVisible();
  await expect(page.getByTestId("staff-create-login")).not.toBeChecked();
  await expect(page.getByTestId("login-fields")).toHaveCount(0);
  await page.getByTestId("staff-first-name").fill("Synthetic");
  await page.getByTestId("staff-last-name").fill(staffLast);
  await page.getByTestId("staff-kind").selectOption("DOCTOR");
  await page.getByTestId("staff-council").fill(`MC${RUN}`);
  await page.getByTestId("staff-submit").click();
  await expectToast(page, "عضو جدید ثبت شد");

  await page.getByTestId("staff-search").fill(staffLast);
  await page.getByTestId("staff-search-submit").click();
  const row = page.getByTestId("staff-row").filter({ hasText: staffLast });
  await expect(row).toHaveCount(1);
  await expect(row).toContainText("پزشک");
  await expect(row).toContainText("ندارد");

  await row.getByTestId("staff-provision").click();
  await page.getByTestId("staff-login-identifier").fill(loginName);
  await page.getByTestId("staff-login-password").fill(`Synthetic-Pass-${RUN}!!`);
  await page.getByTestId("provision-submit").click();
  await expectToast(page, "حساب ورود بدون نقش ایجاد شد");
  await expect(row).not.toContainText("ندارد");
  await expect(row).toContainText(loginName);

  await row.getByTestId("staff-edit").click();
  await page.getByTestId("staff-council").fill(`MCX${RUN}`);
  await page.getByTestId("staff-submit").click();
  await expectToast(page, "اطلاعات عضو به‌روزرسانی شد");
  await expect(row).toContainText(`MCX${RUN}`);

  await row.getByTestId("staff-toggle").click();
  await expectToast(page, "عضو غیرفعال شد");
  await expect(row).toContainText("غیرفعال");
  await assertNoNonLatinDigits(page);
});

test("manager: roles, assignment, effective permissions, account suspension", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await gotoNav(page, "کاربران و دسترسی", "access-page");

  await page.getByTestId("tab-roles").click();
  await page.getByTestId("role-add").click();
  await page.getByTestId("role-code").fill(roleCode);
  await page.getByTestId("role-name").fill(`Synthetic role ${RUN}`);
  await page.getByTestId("perm-BETA02_STAFF_VIEW").check();
  await page.getByTestId("role-submit").click();
  await expectToast(page, "نقش جدید ایجاد شد");
  await expect(page.getByTestId("role-row").filter({ hasText: roleCode })).toHaveCount(1);

  await page.getByTestId("tab-accounts").click();
  await page.getByTestId("accounts-search").fill(loginName);
  await page.getByTestId("accounts-search-submit").click();
  const account = page.getByTestId("account-row").filter({ hasText: loginName });
  await expect(account).toHaveCount(1);
  await expect(account).toContainText("بدون نقش");

  await account.getByTestId("account-roles").click();
  await page.getByTestId(`assign-role-${roleCode}`).check();
  await page.getByTestId("account-roles-save").click();
  await expectToast(page, "نقش‌های کاربر به‌روزرسانی شد");
  await expect(account).toContainText(roleCode);

  await account.getByTestId("account-effective").click();
  const effective = page.getByTestId("effective-dialog");
  await expect(effective.getByTestId("effective-row")).toHaveCount(1);
  await expect(effective).toContainText("BETA02_STAFF_VIEW");
  await page.keyboard.press("Escape");
  await expect(effective).toHaveCount(0);

  await account.getByTestId("account-status").click();
  await page.getByTestId("account-status-confirm").click();
  await expectToast(page, "حساب معلق شد");
  await expect(account).toContainText("معلق");

  await page.getByTestId("tab-governance").click();
  await expect(page.getByTestId("governance-row").first()).toBeVisible();
  await expect(page.getByTestId("governance-edit")).toHaveCount(0);
  await assertNoNonLatinDigits(page);
});

test("owner: governance editing is available only with the manage permission", async ({ page }) => {
  await loginAs(page, credsFromEnv("OWNER"), "owner");
  await gotoNav(page, "کاربران و دسترسی", "access-page");
  await page.getByTestId("tab-governance").click();
  await expect(page.getByTestId("governance-edit").first()).toBeVisible();
});

test("manager: services and resources admin with requirements", async ({ page }) => {
  await loginAs(page, credsFromEnv("MANAGER"), "manager");
  await gotoNav(page, "فهرست خدمات", "catalog-page");
  await page.getByTestId("catalog-manage-link").click();
  await expect(page.getByTestId("catalog-admin-page")).toBeVisible();

  await page.getByTestId("tab-resources").click();
  await page.getByTestId("resource-add").click();
  await page.getByTestId("resource-name").fill(`E2E Room ${RUN}`);
  await page.getByTestId("resource-type").selectOption("ROOM");
  await page.getByTestId("resource-submit").click();
  await expectToast(page, "منبع جدید ایجاد شد");
  await page.getByTestId("resources-search").fill(`E2E Room ${RUN}`);
  await page.getByRole("button", { name: "اعمال" }).click();
  await expect(page.getByTestId("resource-row").filter({ hasText: `E2E Room ${RUN}` })).toHaveCount(1);

  await page.getByTestId("tab-services").click();
  await page.getByTestId("service-add").click();
  await page.getByTestId("service-name").fill(`E2E Service ${RUN}`);
  await page.getByTestId("service-duration").fill("20");
  await page.getByTestId("service-price").fill("1500000");
  await page.getByTestId("service-submit").click();
  await expectToast(page, "خدمت جدید ایجاد شد");

  await page.getByTestId("services-search").fill(`E2E Service ${RUN}`);
  await page.getByRole("button", { name: "اعمال" }).click();
  const row = page.getByTestId("service-row").filter({ hasText: `E2E Service ${RUN}` });
  await expect(row).toHaveCount(1);
  await expect(row).toContainText(/1.500.000/);

  await row.getByTestId("service-requirements").click();
  await expect(page.getByTestId("requirements-empty")).toBeVisible();
  await page.getByTestId("requirement-add").click();
  await page.getByTestId("requirements-save").click();
  await expectToast(page, "الزامات منابع خدمت به‌روزرسانی شد");
  await expect(row).toContainText("1");

  await row.getByTestId("service-edit").click();
  await page.getByTestId("service-duration").fill("45");
  await page.getByTestId("service-submit").click();
  await expectToast(page, "خدمت به‌روزرسانی شد");
  await expect(row).toContainText("45");

  await row.getByTestId("service-toggle").click();
  await expectToast(page, "خدمت غیرفعال شد");
  await expect(row).toContainText("غیرفعال");
  await assertNoNonLatinDigits(page);
});
