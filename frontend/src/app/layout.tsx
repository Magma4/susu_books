import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Susu Books — Your Market Business Copilot",
  description:
    "Offline, voice-first AI business assistant for market vendors and small business owners. Track purchases, sales, and inventory by speaking naturally.",
  keywords: ["business", "vendor", "market", "accounting", "voice", "offline", "Ghana", "Africa"],
  authors: [{ name: "Susu Books" }],
  robots: "noindex, nofollow", // Keep private — offline tool
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#1B5E20",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        {/* Preconnect for Google Fonts */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        {/* Manifest for PWA feel */}
        <link rel="manifest" href="/manifest.json" />
        {/* Apple touch icon */}
        <link rel="apple-touch-icon" href="/icon-192.png" />
      </head>
      <body className="h-full overflow-hidden">{children}</body>
    </html>
  );
}
