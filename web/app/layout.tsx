import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import AssistantBubble from "@/components/AssistantBubble";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Fin de Mes",
  description: "¿Llego a fin de mes? Proyección de saldo y plan de rescate financiero.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
        <AssistantBubble />
      </body>
    </html>
  );
}
