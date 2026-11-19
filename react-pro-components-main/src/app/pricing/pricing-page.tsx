"use client";

import { ArrowRight, Check } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { Footer } from "@/components/marketing/footer/footer";
import { Header } from "@/components/marketing/header-navigation/header";

interface PricingTierProps {
    name: string;
    description: string;
    featured?: boolean;
    features: string[];
    cta: string;
}

const PricingTier = ({ name, description, featured, features, cta }: PricingTierProps) => (
    <div
        className={`flex flex-col rounded-2xl border p-6 md:p-8 ${featured ? "border-brand bg-primary ring-1 ring-brand shadow-lg" : "border-secondary bg-primary"}`}
    >
        <h3 className="text-xl font-semibold text-primary">{name}</h3>
        <p className="mt-2 text-md text-tertiary">{description}</p>

        <div className="mt-6 border-t border-secondary pt-6">
            <p className="text-sm font-semibold text-secondary">What&apos;s included:</p>
            <ul className="mt-4 flex flex-col gap-3">
                {features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                        <Check className="mt-0.5 size-5 shrink-0 text-fg-brand-primary" />
                        <span className="text-sm text-tertiary">{feature}</span>
                    </li>
                ))}
            </ul>
        </div>

        <div className="mt-8 flex flex-col">
            <Button size="xl" color={featured ? "primary" : "secondary"} href="/contact" iconTrailing={ArrowRight}>
                {cta}
            </Button>
        </div>
    </div>
);

const tiers: PricingTierProps[] = [
    {
        name: "Project-based",
        description: "Ideal for well-defined projects with clear scope and timeline. Fixed price, predictable delivery.",
        features: [
            "Dedicated project manager",
            "Requirements & architecture phase",
            "Agile 2-week sprint delivery",
            "QA testing & code review",
            "30-day post-launch support",
            "Source code ownership",
        ],
        cta: "Discuss your project",
    },
    {
        name: "Dedicated team",
        description: "A full engineering team embedded with yours. Scale up or down as your product evolves.",
        featured: true,
        features: [
            "Hand-picked engineering team",
            "Full-time dedicated resources",
            "Daily standups & sprint planning",
            "CI/CD pipeline setup",
            "24/7 production monitoring",
            "Flexible team composition",
            "Direct Slack/Teams communication",
        ],
        cta: "Build your team",
    },
    {
        name: "Retainer",
        description: "Ongoing development hours for continuous improvement, maintenance, and feature development.",
        features: [
            "Monthly hour allocation",
            "Priority support queue",
            "Bug fixes & maintenance",
            "Feature development",
            "Performance optimization",
            "Monthly progress reports",
        ],
        cta: "Get started",
    },
];

export default function PricingPage() {
    return (
        <div className="bg-primary">
            <Header />

            <section className="bg-primary pt-16 pb-16 md:pt-24 md:pb-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="flex flex-col items-center text-center">
                        <span className="text-sm font-semibold text-brand-secondary md:text-md">Pricing</span>
                        <h1 className="mt-3 text-display-md font-semibold text-primary md:text-display-lg lg:text-display-xl">
                            Simple, transparent pricing
                        </h1>
                        <p className="mt-4 max-w-3xl text-lg text-tertiary md:mt-6 md:text-xl">
                            Every project is unique. Choose the engagement model that fits your needs, and we&apos;ll provide a custom quote based
                            on your requirements.
                        </p>
                    </div>
                </div>
            </section>

            <section className="bg-secondary py-16 md:py-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-3 md:gap-8">
                        {tiers.map((tier) => (
                            <PricingTier key={tier.name} {...tier} />
                        ))}
                    </div>

                    <div className="mt-12 flex flex-col items-center gap-4 text-center md:mt-16">
                        <p className="text-lg text-tertiary">
                            Not sure which plan is right? Talk to us — we&apos;ll help you find the best fit.
                        </p>
                        <Button size="xl" href="/contact" iconTrailing={ArrowRight}>
                            Schedule a free consultation
                        </Button>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
