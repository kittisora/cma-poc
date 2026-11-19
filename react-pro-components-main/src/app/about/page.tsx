import type { Metadata } from "next";
import AboutPage from "./about-page";

export const metadata: Metadata = {
    title: "About Mirimera",
    description:
        "Mirimera is a software development company that partners with businesses to build custom web apps, mobile applications, AI solutions, and scalable cloud infrastructure. Learn about our mission, values, and engineering team.",
    alternates: {
        canonical: "/about",
    },
    openGraph: {
        title: "About Mirimera — Our Mission & Team",
        description:
            "Learn about Mirimera, the software development company behind custom web apps, mobile applications, and AI-powered solutions for businesses worldwide.",
        url: "/about",
    },
};

const jsonLd = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    "@id": "https://mirimera.com/about#webpage",
    url: "https://mirimera.com/about",
    name: "About Mirimera",
    isPartOf: { "@id": "https://mirimera.com/#website" },
    about: { "@id": "https://mirimera.com/#organization" },
    description:
        "Mirimera is a software development company that partners with businesses to build custom web apps, mobile applications, AI solutions, and scalable cloud infrastructure.",
};

export default function Page() {
    return (
        <>
            <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
            <AboutPage />
        </>
    );
}
