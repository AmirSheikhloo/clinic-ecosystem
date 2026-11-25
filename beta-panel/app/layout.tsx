import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/feedback/ThemeProvider";
import { ToastProvider } from "@/components/feedback/Toast";
import { DEFAULT_PREFERENCES, PREFERENCES_BOOT_SCRIPT } from "@/config/preferences";

export const metadata: Metadata = {
  title: "کلینیک اکوسیستم — پنل کارکنان",
  description: "پنل مدیریت عملیات کلینیک — نسخهٔ توسعه",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="fa"
      dir="rtl"
      data-theme={DEFAULT_PREFERENCES.theme}
      data-appearance="light"
      data-density={DEFAULT_PREFERENCES.density}
      data-sidebar={DEFAULT_PREFERENCES.sidebar}
      data-motion={DEFAULT_PREFERENCES.motion}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: PREFERENCES_BOOT_SCRIPT }} />
      </head>
      <body className="font-sans antialiased">
        <ThemeProvider>
          <ToastProvider>{children}</ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
