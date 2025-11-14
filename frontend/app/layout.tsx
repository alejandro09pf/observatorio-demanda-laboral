import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Observatorio de Demanda Laboral",
  description: "Análisis del mercado laboral y extracción de habilidades potenciado por IA",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-white`}
      >
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <aside className="w-64 bg-white border-r border-gray-200 p-6 flex flex-col shadow-sm">
            <div className="mb-8">
              <h1 className="text-2xl font-bold mb-2 text-gray-900">Observatorio Laboral</h1>
              <p className="text-sm text-gray-600">Análisis con IA</p>
            </div>

            <nav className="flex-1 space-y-2">
              <Link
                href="/"
                className="block px-4 py-2 rounded hover:bg-blue-50 text-gray-700 hover:text-blue-700 transition"
              >
                Panel Principal
              </Link>
              <Link
                href="/jobs"
                className="block px-4 py-2 rounded hover:bg-blue-50 text-gray-700 hover:text-blue-700 transition"
              >
                Empleos
              </Link>
              <Link
                href="/skills"
                className="block px-4 py-2 rounded hover:bg-blue-50 text-gray-700 hover:text-blue-700 transition"
              >
                Habilidades
              </Link>
              <Link
                href="/clusters"
                className="block px-4 py-2 rounded hover:bg-blue-50 text-gray-700 hover:text-blue-700 transition"
              >
                Clusters
              </Link>
              <Link
                href="/admin"
                className="block px-4 py-2 rounded hover:bg-blue-50 text-gray-700 hover:text-blue-700 transition"
              >
                Administración
              </Link>
            </nav>

            <div className="pt-6 border-t border-gray-200 text-xs text-gray-500">
              <p>Versión 1.0</p>
              <p className="mt-1">Tesis de Ingeniería de Sistemas</p>
            </div>
          </aside>

          {/* Main content */}
          <main className="flex-1 p-8 bg-gray-50">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
