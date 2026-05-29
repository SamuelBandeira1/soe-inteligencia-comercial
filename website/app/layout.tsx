import type { Metadata } from "next";
import { Syne, Space_Grotesk } from "next/font/google";
import "./globals.css";
import ClientLayout from "@/components/ClientLayout";

const syne = Syne({
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"],
  variable: "--font-syne",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Comaf Portas | Madeireira em Fortaleza - CE",
  description:
    "Há 20 anos especialistas em portas de madeira, virgas, tábuas, ripas e madeiras para construção em Fortaleza. Qualidade, variedade e atendimento exclusivo.",
  keywords: ["madeireira", "portas de madeira", "Fortaleza", "virgas", "tábuas", "Comaf"],
  openGraph: {
    title: "Comaf Portas | Madeireira em Fortaleza",
    description: "Especialistas em madeiras e portas há 20 anos em Fortaleza - CE.",
    locale: "pt_BR",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${syne.variable} ${spaceGrotesk.variable}`}>
      <body>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
