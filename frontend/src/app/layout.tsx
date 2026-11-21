import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "@/components/application/notifications/toaster";
import { AppShell } from "@/components/cma/app-shell";
import { CmaProvider } from "@/providers/cma-provider";
import { RouteProvider } from "@/providers/router-provider";
import { Theme } from "@/providers/theme";
import "@/styles/globals.css";
import { cx } from "@/utils/cx";

const inter = Inter({ subsets: ["latin"], display: "swap", variable: "--font-inter" });

export const metadata: Metadata = {
    title: { default: "CMA · Fairfax County 22308 / 22309", template: "%s · CMA" },
    description: "Comparative market analysis from Fairfax County public records: comps, pricing and branded reports.",
    robots: { index: false, follow: false },
};

export const viewport: Viewport = {
    themeColor: "#206cdc",
    colorScheme: "light dark",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={cx(inter.variable, "bg-primary antialiased")}>
                <RouteProvider>
                    <Theme>
                        <CmaProvider>
                            <AppShell>{children}</AppShell>
                            <Toaster />
                        </CmaProvider>
                    </Theme>
                </RouteProvider>
            </body>
        </html>
    );
}
