import type { Metadata } from "next";
import { Vazirmatn } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";
import { ThemeProvider } from "@/components/feedback/ThemeProvider";
import { ToastProvider } from "@/components/feedback/Toast";

const vazirmatn = Vazirmatn({
  subsets: ["arabic", "latin"],
  variable: "--font-vazirmatn",
  display: "swap",
});

export const metadata: Metadata = {
  title: "کلینیک اکوسیستم — پنل کارکنان",
  description: "پنل پذیرش و نوبت‌دهی توسعهٔ BETA",
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
      className={vazirmatn.variable}
    >
      <body className="font-sans antialiased text-[var(--ds-font-size-md)] leading-7">
        <ThemeProvider>
          <ToastProvider>
            <AppShell>{children}</AppShell>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
