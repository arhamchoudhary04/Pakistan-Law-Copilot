import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pakistan Law Copilot",
  description:
    "Grounded, citation-first answers about Pakistani law — cites the exact provision and refuses when unsure. Legal information, not legal advice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
