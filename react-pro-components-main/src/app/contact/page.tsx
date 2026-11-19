import type { Metadata } from "next";
import ContactPage from "./contact-page";

export const metadata: Metadata = {
    title: "Contact",
    description:
        "Get in touch with Mirimera's engineering team. Schedule a free consultation, request a quote for custom software development, or ask us anything.",
    alternates: {
        canonical: "/contact",
    },
    openGraph: {
        title: "Contact Mirimera — Start Your Project",
        description: "Talk to our engineering team about your next software project. Free consultation and project assessment.",
        url: "/contact",
    },
};

const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ContactPage",
    "@id": "https://mirimera.com/contact#webpage",
    url: "https://mirimera.com/contact",
    name: "Contact Mirimera",
    isPartOf: { "@id": "https://mirimera.com/#website" },
    about: { "@id": "https://mirimera.com/#organization" },
    description: "Get in touch with Mirimera's engineering team for a free consultation and project assessment.",
};

export default function Page() {
    return (
        <>
            <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
            <ContactPage />
        </>
    );
}
