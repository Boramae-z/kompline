
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { MainNav } from "@/components/main-nav";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Kompline",
    description: "Compliance Management Platform",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={inter.className}>
                <div className="flex min-h-screen flex-col lg:flex-row">
                    <aside className="w-full lg:w-64 border-r bg-muted/40 p-6 hidden lg:block">
                        <div className="flex items-center gap-2 font-semibold text-lg mb-8">
                            <span>🛡️ Kompline</span>
                        </div>
                        <MainNav />
                    </aside>
                    <div className="block lg:hidden p-4 border-b">
                        <div className="flex items-center justify-between">
                            <span className="font-semibold text-lg">🛡️ Kompline</span>
                            {/* Mobile Menu Trigger would go here */}
                        </div>
                        <div className="mt-4">
                            <MainNav />
                        </div>
                    </div>
                    <main className="flex-1 p-6 lg:p-8 w-full min-w-0">
                        {children}
                    </main>
                </div>
            </body>
        </html>
    );
}
