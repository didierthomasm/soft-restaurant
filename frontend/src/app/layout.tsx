import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Toaster } from "@/components/ui/sonner";

import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tabernas Cerveceras",
  description: "Asistencia y reportes sobre SoftRestaurant",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
        <Toaster richColors />
      </body>
    </html>
  );
}
