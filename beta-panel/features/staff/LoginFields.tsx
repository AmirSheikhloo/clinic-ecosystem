import { TextField } from "@/components/forms/TextField";
import { MIN_PASSWORD_LENGTH } from "./types";

type Props = {
  login: string;
  password: string;
  onLoginChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  idPrefix: string;
};

export function LoginFields({ login, password, onLoginChange, onPasswordChange, idPrefix }: Props) {
  return (
    <div className="grid gap-3 sm:grid-cols-2" data-testid="login-fields">
      <TextField
        id={`${idPrefix}-login`}
        label="شناسهٔ ورود"
        value={login}
        onChange={(e) => onLoginChange(e.target.value)}
        autoComplete="off"
        maxLength={254}
        required
        data-testid="staff-login-identifier"
      />
      <TextField
        id={`${idPrefix}-password`}
        label={`گذرواژهٔ اولیه (حداقل ${MIN_PASSWORD_LENGTH} نویسه)`}
        type="password"
        value={password}
        onChange={(e) => onPasswordChange(e.target.value)}
        autoComplete="new-password"
        minLength={MIN_PASSWORD_LENGTH}
        maxLength={128}
        required
        data-testid="staff-login-password"
      />
      <p className="text-xs text-[var(--ds-text-muted)] sm:col-span-2">
        حساب ورود بدون هیچ نقشی ساخته می‌شود؛ دسترسی فقط از بخش «کاربران و دسترسی» تخصیص داده می‌شود.
      </p>
    </div>
  );
}
