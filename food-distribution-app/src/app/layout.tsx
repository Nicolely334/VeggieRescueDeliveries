import type { Metadata } from "next";
import { Figtree, Inter } from "next/font/google";
import { Sidebar } from "@/src/components/ui/Sidebar";
import "./globals.css";

const figtree = Figtree({
  subsets: ["latin"],
  variable: "--font-figtree",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Veggie Rescue Delivery",
  description: "Food rescue delivery dashboard",
};

export default function RootLayout({ 
  children 
}: { 
  children: React.ReactNode 
}) {
  return (
    <html
      lang="en"
      className={`${figtree.variable} ${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-row">
        <Sidebar />
        <main className="min-w-0 flex-1 overflow-auto">{children}</main>
      </body>
    </html>
  );
}
