import type { Metadata } from "next";
import { Vazirmatn } from "next/font/google";
import "./globals.css";
import { AppShell } from "./_components/AppShell";

const vazirmatn = Vazirmatn({
  subsets: ["arabic", "latin"],
  variable: "--font-vazirmatn",
  display: "swap",
});

export const metadata: Metadata = {
  title: "کلینیک اکوسیستم — پذیرش آزمایشی",
  description: "میز پذیرش توسعهٔ BETA-01B",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl" className={vazirmatn.variable}>
      <body className="font-sans antialiased text-[15px] leading-7">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
