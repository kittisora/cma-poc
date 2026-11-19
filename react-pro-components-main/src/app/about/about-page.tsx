"use client";

import { ArrowRight, CheckCircle, Target04, Users01, Zap } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { Footer } from "@/components/marketing/footer/footer";
import { Header } from "@/components/marketing/header-navigation/header";

const values = [
    {
        icon: Zap,
        title: "Engineering excellence",
        description: "We write clean, maintainable code and follow industry best practices — from CI/CD pipelines to automated testing.",
    },
    {
        icon: Users01,
        title: "Client partnership",
        description: "We embed with your team, not just deliver code. Every sprint is transparent, and every decision is collaborative.",
    },
    {
        icon: Target04,
        title: "Business impact",
        description: "Technology is a means, not the goal. We measure success by the business outcomes our software enables.",
    },
    {
        icon: CheckCircle,
        title: "Reliable delivery",
        description: "On time, on budget, on spec. We use agile methodologies to ship iteratively and adapt to changing requirements.",
    },
];

export default function AboutPage() {
    return (
        <div className="bg-primary">
            <Header />

            <section className="bg-primary pt-16 pb-16 md:pt-24 md:pb-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="flex max-w-3xl flex-col gap-4 md:gap-6">
                        <span className="text-sm font-semibold text-brand-secondary md:text-md">About Mirimera</span>
                        <h1 className="text-display-md font-semibold text-primary md:text-display-lg lg:text-display-xl">
                            We build the software that powers your business
                        </h1>
                        <p className="text-lg text-tertiary md:text-xl">
                            Mirimera is a software development company that partners with startups and enterprises to design, build, and scale
                            custom digital products. From web and mobile applications to AI-powered platforms and cloud infrastructure, our
                            engineering teams deliver production-ready solutions that drive real business growth.
                        </p>
                    </div>
                </div>
            </section>

            <section className="bg-secondary py-16 md:py-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="max-w-3xl">
                        <span className="text-sm font-semibold text-brand-secondary md:text-md">Our mission</span>
                        <h2 className="mt-3 text-display-sm font-semibold text-primary md:text-display-md">
                            Making world-class software engineering accessible
                        </h2>
                        <p className="mt-4 text-lg text-tertiary md:mt-5 md:text-xl">
                            Great software shouldn&apos;t be a bottleneck. Mirimera exists to give every company access to the caliber of
                            engineering talent and processes that were once reserved for Big Tech. We bring Silicon Valley-grade development
                            practices to businesses of every size, everywhere.
                        </p>
                    </div>
                </div>
            </section>

            <section className="bg-primary py-16 md:py-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="max-w-3xl">
                        <span className="text-sm font-semibold text-brand-secondary md:text-md">Our values</span>
                        <h2 className="mt-3 text-display-sm font-semibold text-primary md:text-display-md">What we stand for</h2>
                        <p className="mt-4 text-lg text-tertiary md:mt-5 md:text-xl">
                            These principles guide every project we take on and every line of code we write at Mirimera.
                        </p>
                    </div>

                    <div className="mt-12 grid grid-cols-1 gap-8 md:mt-16 md:grid-cols-2 md:gap-12">
                        {values.map((value) => {
                            const Icon = value.icon;
                            return (
                                <div key={value.title} className="flex flex-col gap-4">
                                    <div className="flex size-12 items-center justify-center rounded-xl bg-brand-secondary">
                                        <Icon className="size-6 text-fg-white" />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-semibold text-primary">{value.title}</h3>
                                        <p className="mt-1 text-md text-tertiary">{value.description}</p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </section>

            <section className="bg-secondary py-16 md:py-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="flex flex-col items-center text-center">
                        <h2 className="text-display-sm font-semibold text-primary md:text-display-md">Ready to work with us?</h2>
                        <p className="mt-4 text-lg text-tertiary md:mt-5 md:text-xl">
                            Let&apos;s discuss your next project and see how Mirimera can help.
                        </p>
                        <div className="mt-8 flex flex-col-reverse gap-3 self-stretch sm:flex-row sm:self-center md:mt-12">
                            <Button color="secondary" size="xl" href="/services">
                                Our services
                            </Button>
                            <Button size="xl" href="/contact" iconTrailing={ArrowRight}>
                                Get in touch
                            </Button>
                        </div>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
