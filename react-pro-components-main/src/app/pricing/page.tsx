import type { Metadata } from "next";
import PricingPage from "./pricing-page";

export const metadata: Metadata = {
    title: "Pricing",
    description:
        "Explore Mirimera's flexible pricing for custom software development. From project-based engagements to dedicated engineering teams — find the right plan for your business.",
    alternates: {
        canonical: "/pricing",
    },
    openGraph: {
        title: "Mirimera Pricing — Software Development Plans",
        description:
            "Flexible pricing for custom software development. Project-based, retainer, or dedicated team — Mirimera has a plan that fits your needs.",
        url: "/pricing",
    },
};

export default function Page() {
    return <PricingPage />;
}
