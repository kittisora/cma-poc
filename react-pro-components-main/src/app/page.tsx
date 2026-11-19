import type { Metadata } from "next";
import LandingPage17 from "./landing-page-17";

export const metadata: Metadata = {
    title: "Mirimera — Custom Software Development & Tech Solutions",
    description:
        "Mirimera is a software development company building custom web apps, mobile applications, AI solutions, and scalable cloud infrastructure. Partner with Mirimera tech experts to ship better software, faster.",
    alternates: {
        canonical: "/",
    },
};

const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "Organization",
            "@id": "https://mirimera.com/#organization",
            name: "Mirimera",
            alternateName: ["Mirimera Tech", "Mirimera Software"],
            url: "https://mirimera.com",
            logo: {
                "@type": "ImageObject",
                url: "https://mirimera.com/icon.png",
            },
            description:
                "Mirimera is a software development company that engineers custom web apps, mobile applications, AI solutions, and scalable cloud infrastructure for businesses worldwide.",
            sameAs: [
                // Add your real profile URLs here once created:
                // "https://www.linkedin.com/company/mirimera",
                // "https://github.com/mirimera",
                // "https://x.com/mirimera",
            ],
            contactPoint: {
                "@type": "ContactPoint",
                contactType: "sales",
                url: "https://mirimera.com",
            },
            knowsAbout: [
                "Custom Software Development",
                "Web Application Development",
                "Mobile App Development",
                "AI & Machine Learning Solutions",
                "Cloud Infrastructure & DevOps",
                "API Development",
                "UI/UX Design",
            ],
        },
        {
            "@type": "WebSite",
            "@id": "https://mirimera.com/#website",
            url: "https://mirimera.com",
            name: "Mirimera",
            publisher: { "@id": "https://mirimera.com/#organization" },
            description:
                "From custom web and mobile applications to scalable cloud solutions, Mirimera engineers the software your business needs to thrive.",
        },
        {
            "@type": "WebPage",
            "@id": "https://mirimera.com/#webpage",
            url: "https://mirimera.com",
            name: "Mirimera — Custom Software Development & Tech Solutions",
            isPartOf: { "@id": "https://mirimera.com/#website" },
            about: { "@id": "https://mirimera.com/#organization" },
            description:
                "Mirimera is a software development company building custom web apps, mobile applications, AI solutions, and scalable cloud infrastructure.",
        },
        {
            "@type": "ProfessionalService",
            "@id": "https://mirimera.com/#service",
            name: "Mirimera",
            url: "https://mirimera.com",
            description: "End-to-end custom software development services — from discovery and architecture to deployment and ongoing support.",
            provider: { "@id": "https://mirimera.com/#organization" },
            serviceType: [
                "Web Development",
                "Mobile App Development",
                "AI & ML Solutions",
                "Cloud & DevOps",
                "API Development",
                "UI/UX Design",
            ],
        },
    ],
};

export default function Page() {
    return (
        <>
            <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
            <LandingPage17 />
        </>
    );
}
