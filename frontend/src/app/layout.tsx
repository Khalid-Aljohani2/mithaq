import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Sans_Arabic, Noto_Naskh_Arabic } from "next/font/google";
import "./globals.css";

import { Providers } from "./providers";
import { Letterhead, SkipLink } from "@/components/shell/letterhead";
import { PREFS_SCRIPT } from "@/lib/prefs-script";

// The interface face.
const plex = IBM_Plex_Sans_Arabic({
  variable: "--font-ui",
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

// The interface face for English: the Latin cut of the same family.
const plexLatin = IBM_Plex_Sans({
  variable: "--font-ui-latin",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

// The document face: request text, legal text, the seal.
const naskh = Noto_Naskh_Arabic({
  variable: "--font-naskh",
  subsets: ["arabic"],
  weight: ["400", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "MithaqAi",
  description: "عقد واحد، وطرفان، وسجل واحد لكل تغيير.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ar"
      dir="rtl"
      className={`${plex.variable} ${plexLatin.variable} ${naskh.variable} h-full antialiased`}
      // PREFS_SCRIPT sets lang, dir and data-theme before React hydrates.
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: PREFS_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <Providers>
          <SkipLink />
          <div className="print:hidden">
            <Letterhead />
          </div>
          <main id="main" className="flex-1">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
