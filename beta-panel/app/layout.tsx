import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";
import { ThemeProvider } from "@/components/feedback/ThemeProvider";
import { ToastProvider } from "@/components/feedback/Toast";

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
      data-theme="ocean"
      data-appearance="light"
    >
      <body className="font-sans antialiased">
        <ThemeProvider>
          <ToastProvider>
            <AppShell>{children}</AppShell>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
