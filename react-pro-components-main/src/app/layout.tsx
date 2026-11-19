import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { RouteProvider } from "@/providers/router-provider";
import { Theme } from "@/providers/theme";
import "@/styles/globals.css";
import { cx } from "@/utils/cx";

const SITE_URL = "https://mirimera.com";
const SITE_NAME = "Mirimera";

const inter = Inter({
    subsets: ["latin"],
    display: "swap",
    variable: "--font-inter",
});

export const metadata: Metadata = {
    metadataBase: new URL(SITE_URL),
    title: {
        default: "Mirimera — Custom Software Development & Tech Solutions",
        template: "%s | Mirimera",
    },
    description:
        "Mirimera is a software development company that engineers custom web apps, mobile applications, AI solutions, and scalable cloud infrastructure for businesses worldwide.",
    keywords: [
        "Mirimera",
        "Mirimera tech",
        "Mirimera software",
        "custom software development",
        "web application development",
        "mobile app development",
        "AI solutions",
        "cloud infrastructure",
        "software engineering company",
        "tech consulting",
        "scalable software solutions",
    ],
    authors: [{ name: "Mirimera", url: SITE_URL }],
    creator: "Mirimera",
    publisher: "Mirimera",
    robots: {
        index: true,
        follow: true,
        googleBot: {
            index: true,
            follow: true,
            "max-video-preview": -1,
            "max-image-preview": "large",
            "max-snippet": -1,
        },
    },
    alternates: {
        canonical: SITE_URL,
    },
    openGraph: {
        type: "website",
        locale: "en_US",
        url: SITE_URL,
        siteName: SITE_NAME,
        title: "Mirimera — Custom Software Development & Tech Solutions",
        description:
            "From custom web and mobile applications to scalable cloud solutions, Mirimera engineers the software your business needs to thrive.",
        images: [
            {
                url: "/og-image.png",
                width: 1200,
                height: 630,
                alt: "Mirimera — Software that drives growth",
            },
        ],
    },
    twitter: {
        card: "summary_large_image",
        title: "Mirimera — Custom Software Development & Tech Solutions",
        description:
            "From custom web and mobile applications to scalable cloud solutions, Mirimera engineers the software your business needs to thrive.",
        images: ["/og-image.png"],
    },
    icons: {
        icon: [
            { url: "/favicon.ico", sizes: "any" },
            { url: "/icon.png", type: "image/png", sizes: "1024x1024" },
        ],
        apple: { url: "/icon.png", type: "image/png", sizes: "1024x1024" },
    },
};

export const viewport: Viewport = {
    themeColor: "#2f84f8",
    colorScheme: "light dark",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={cx(inter.variable, "bg-primary antialiased")}>
                <RouteProvider>
                    <Theme>{children}</Theme>
                </RouteProvider>
            </body>
        </html>
    );
}
