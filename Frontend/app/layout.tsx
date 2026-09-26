import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "StrokeGuard AI — Clinical Dashboard",
  description: "AI-assisted stroke imaging analysis dashboard"
};

export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
