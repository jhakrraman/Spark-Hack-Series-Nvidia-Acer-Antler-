import { Suspense } from "react";
import { JetBrains_Mono, Inter } from "next/font/google";
import { ThemeProvider } from "next-themes";
import HomeLink from "@/components/home-link";
import { HeaderNav } from "@/components/header-nav";
import HeaderAuth from "@/components/header-auth";
import { NavigationEvents } from "@/components/navigation-events";
import NProgress from "nprogress";
import "./globals.css";
import "nprogress/nprogress.css";
import "maplibre-gl/dist/maplibre-gl.css";

NProgress.configure({
  showSpinner: false,
  trickleSpeed: 1,
  minimum: 0.99,
  easing: "ease",
  speed: 1,
});

const defaultUrl = process.env.VERCEL_URL
  ? `https://${process.env.VERCEL_URL}`
  : "http://localhost:3000";

export const metadata = {
  metadataBase: new URL(defaultUrl),
  title: "Person of Interest // DECK/01",
  description: "Local on-device surveillance intelligence. Tactical HUD for live city feeds.",
};

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500", "600", "700", "800"],
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${jetbrains.variable} ${inter.variable}`}
      suppressHydrationWarning
    >
      <body
        className="deck-grid deck-vignette min-h-screen font-mono"
        suppressHydrationWarning
      >
        <Suspense fallback={null}>
          <NavigationEvents />
        </Suspense>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          forcedTheme="dark"
          disableTransitionOnChange
        >
          <div className="relative z-10 flex min-h-screen flex-col">
            {/* Top status strip */}
            <div className="border-b border-deck-line bg-deck-bg/80">
              <div className="mx-auto flex max-w-[1600px] items-center justify-between px-6 py-2">
                <div className="flex items-center gap-4 text-[11px] font-bold uppercase tracking-[0.14em] text-deck-dim">
                  <span className="flex items-center gap-2">
                    <span className="deck-dot text-deck-signal deck-blink" />
                    <span className="text-deck-signal">LIVE</span>
                  </span>
                  <span className="hidden md:inline">SYS/DECK-01</span>
                  <span className="hidden md:inline">NODE/NYC-001</span>
                  <span className="hidden lg:inline">VLM/GEMMA-4-26B</span>
                </div>
                <div className="flex items-center gap-4 text-[11px] font-bold uppercase tracking-[0.14em] text-deck-dim">
                  <span className="hidden md:inline">40.7128°N 74.0060°W</span>
                  <span className="text-deck-fg">UTC {new Date().toISOString().slice(11, 16)}</span>
                </div>
              </div>
            </div>

            {/* Primary nav */}
            <header className="border-b border-deck-line bg-deck-bg">
              <div className="mx-auto flex max-w-[1600px] items-center justify-between px-6 py-4">
                <div className="flex items-center gap-10">
                  <HomeLink />
                  <HeaderNav />
                </div>
                <HeaderAuth />
              </div>
            </header>

            {/* Content slot */}
            <main className="relative flex-1">{children}</main>

            {/* Footer strip */}
            <footer className="border-t border-deck-line bg-deck-bg/60">
              <div className="mx-auto flex max-w-[1600px] items-center justify-between px-6 py-2 text-[10px] uppercase tracking-[0.16em] text-deck-faint">
                <span>// PERSON OF INTEREST — DECK/01</span>
                <span>LOCAL INFERENCE · NO DATA LEAVES DEVICE</span>
                <span>BUILD 26.04.11</span>
              </div>
            </footer>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
