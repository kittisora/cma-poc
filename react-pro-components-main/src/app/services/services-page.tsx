"use client";

import type { FC } from "react";
import { ArrowRight, Cloud01, Code01, CpuChip01, LayoutAlt03, Phone01, Palette } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { Footer } from "@/components/marketing/footer/footer";
import { Header } from "@/components/marketing/header-navigation/header";

interface ServiceCardProps {
    icon: FC<{ className?: string }>;
    title: string;
    description: string;
    capabilities: string[];
}

const ServiceCard = ({ icon: Icon, title, description, capabilities }: ServiceCardProps) => (
    <div className="flex flex-col gap-5 rounded-2xl border border-secondary bg-primary p-6 md:p-8">
        <div className="flex size-12 items-center justify-center rounded-xl bg-brand-secondary">
            <Icon className="size-6 text-fg-white" />
        </div>
        <div>
            <h3 className="text-xl font-semibold text-primary">{title}</h3>
            <p className="mt-2 text-md text-tertiary">{description}</p>
        </div>
        <ul className="flex flex-col gap-2">
            {capabilities.map((cap) => (
                <li key={cap} className="flex items-start gap-2 text-sm text-tertiary">
                    <span className="mt-1 size-1.5 shrink-0 rounded-full bg-brand-solid" />
                    {cap}
                </li>
            ))}
        </ul>
    </div>
);

const services: ServiceCardProps[] = [
    {
        icon: Code01,
        title: "Web development",
        description: "Custom web applications built with modern frameworks like React, Next.js, and Node.js — optimized for performance and SEO.",
        capabilities: ["Single-page applications (SPA)", "Server-side rendered apps", "Progressive web apps (PWA)", "E-commerce platforms", "Admin dashboards & portals"],
    },
    {
        icon: Phone01,
        title: "Mobile app development",
        description: "Native and cross-platform mobile applications for iOS and Android that users love to use.",
        capabilities: ["React Native & Flutter", "Native iOS (Swift) & Android (Kotlin)", "App Store optimization", "Push notifications & real-time sync", "Offline-first architecture"],
    },
    {
        icon: CpuChip01,
        title: "AI & ML solutions",
        description: "Intelligent software powered by machine learning, natural language processing, and computer vision to automate and optimize.",
        capabilities: ["Custom ML model development", "Natural language processing", "Computer vision systems", "Recommendation engines", "AI-powered automation"],
    },
    {
        icon: Cloud01,
        title: "Cloud & DevOps",
        description: "Scalable cloud infrastructure with automated CI/CD pipelines, monitoring, and zero-downtime deployments.",
        capabilities: ["AWS, GCP & Azure architecture", "Kubernetes & containerization", "CI/CD pipeline automation", "Infrastructure as Code (Terraform)", "24/7 monitoring & alerting"],
    },
    {
        icon: LayoutAlt03,
        title: "API development",
        description: "Robust, well-documented APIs that connect your systems and enable third-party integrations at scale.",
        capabilities: ["RESTful & GraphQL APIs", "Microservices architecture", "API gateway & rate limiting", "Webhook integrations", "Real-time WebSocket APIs"],
    },
    {
        icon: Palette,
        title: "UI/UX design",
        description: "User-centered design that turns complex workflows into intuitive interfaces your customers will enjoy using.",
        capabilities: ["User research & testing", "Wireframing & prototyping", "Design systems & component libraries", "Accessibility (WCAG) compliance", "Responsive & adaptive design"],
    },
];

export default function ServicesPage() {
    return (
        <div className="bg-primary">
            <Header />

            <section className="bg-primary pt-16 pb-16 md:pt-24 md:pb-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="flex max-w-3xl flex-col gap-4 md:gap-6">
                        <span className="text-sm font-semibold text-brand-secondary md:text-md">Our services</span>
                        <h1 className="text-display-md font-semibold text-primary md:text-display-lg lg:text-display-xl">
                            End-to-end software development
                        </h1>
                        <p className="text-lg text-tertiary md:text-xl">
                            Mirimera delivers full-cycle software engineering — from architecture and design through development, testing, deployment,
                            and ongoing support. Whatever you need to build, our team has the expertise to ship it.
                        </p>
                    </div>
                </div>
            </section>

            <section className="bg-secondary py-16 md:py-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 md:gap-8">
                        {services.map((service) => (
                            <ServiceCard key={service.title} {...service} />
                        ))}
                    </div>
                </div>
            </section>

            <section className="bg-primary py-16 md:py-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="max-w-3xl">
                        <span className="text-sm font-semibold text-brand-secondary md:text-md">Our process</span>
                        <h2 className="mt-3 text-display-sm font-semibold text-primary md:text-display-md">How we work</h2>
                        <p className="mt-4 text-lg text-tertiary md:mt-5 md:text-xl">
                            Every Mirimera engagement follows a proven process designed to minimize risk and maximize quality.
                        </p>
                    </div>

                    <div className="mt-12 grid grid-cols-1 gap-8 md:mt-16 md:grid-cols-3 md:gap-12">
                        {[
                            {
                                step: "01",
                                title: "Discovery & architecture",
                                description:
                                    "We map your requirements, define the technical architecture, and create a detailed roadmap aligned with your business goals and timeline.",
                            },
                            {
                                step: "02",
                                title: "Agile development",
                                description:
                                    "Our engineers build in 2-week sprints with full transparency. You see progress every sprint — not just at launch.",
                            },
                            {
                                step: "03",
                                title: "Deployment & support",
                                description:
                                    "We handle CI/CD, cloud infrastructure, and post-launch monitoring to keep your software running flawlessly at scale.",
                            },
                        ].map((phase) => (
                            <div key={phase.step} className="flex flex-col gap-4">
                                <span className="text-display-sm font-semibold text-brand-tertiary">{phase.step}</span>
                                <h3 className="text-lg font-semibold text-primary">{phase.title}</h3>
                                <p className="text-md text-tertiary">{phase.description}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <section className="bg-secondary py-16 md:py-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="flex flex-col items-center text-center">
                        <h2 className="text-display-sm font-semibold text-primary md:text-display-md">
                            Let&apos;s build something extraordinary
                        </h2>
                        <p className="mt-4 text-lg text-tertiary md:mt-5 md:text-xl">
                            Tell us about your project and get a free technical assessment from our engineering team.
                        </p>
                        <div className="mt-8 flex flex-col-reverse gap-3 self-stretch sm:flex-row sm:self-center md:mt-12">
                            <Button color="secondary" size="xl" href="/pricing">
                                View pricing
                            </Button>
                            <Button size="xl" href="/contact" iconTrailing={ArrowRight}>
                                Start a project
                            </Button>
                        </div>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
