import type { Metadata } from "next";
import ServicesPage from "./services-page";

export const metadata: Metadata = {
    title: "Services",
    description:
        "Mirimera offers end-to-end software development services including custom web applications, mobile apps, AI & ML solutions, cloud infrastructure, API development, and UI/UX design.",
    alternates: {
        canonical: "/services",
    },
    openGraph: {
        title: "Mirimera Services — Custom Software Development",
        description:
            "From web and mobile development to AI solutions and cloud infrastructure — explore the full range of Mirimera tech services.",
        url: "/services",
    },
};

const jsonLd = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    "@id": "https://mirimera.com/services#webpage",
    url: "https://mirimera.com/services",
    name: "Mirimera Services — Custom Software Development",
    isPartOf: { "@id": "https://mirimera.com/#website" },
    about: { "@id": "https://mirimera.com/#service" },
    description:
        "Mirimera offers end-to-end software development services including custom web applications, mobile apps, AI & ML solutions, cloud infrastructure, API development, and UI/UX design.",
};

export default function Page() {
    return (
        <>
            <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
            <ServicesPage />
        </>
    );
}
