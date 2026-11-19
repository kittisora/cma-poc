"use client";

import { Mail01, MessageChatCircle, Phone } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { Footer } from "@/components/marketing/footer/footer";
import { Header } from "@/components/marketing/header-navigation/header";

const contactMethods = [
    {
        icon: Mail01,
        title: "Email us",
        description: "Our team is here to help.",
        contact: "hello@mirimera.com",
        href: "mailto:hello@mirimera.com",
    },
    {
        icon: MessageChatCircle,
        title: "Chat with us",
        description: "We respond within 24 hours.",
        contact: "Start a conversation",
        href: "#",
    },
    {
        icon: Phone,
        title: "Call us",
        description: "Mon-Fri from 9am to 6pm.",
        contact: "+1 (555) 000-0000",
        href: "tel:+15550000000",
    },
];

export default function ContactPage() {
    return (
        <div className="bg-primary">
            <Header />

            <section className="bg-primary pt-16 pb-16 md:pt-24 md:pb-24">
                <div className="mx-auto max-w-container px-4 md:px-8">
                    <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16">
                        <div className="flex flex-col gap-6">
                            <div className="flex max-w-xl flex-col gap-4 md:gap-6">
                                <span className="text-sm font-semibold text-brand-secondary md:text-md">Contact us</span>
                                <h1 className="text-display-md font-semibold text-primary md:text-display-lg">Get in touch</h1>
                                <p className="text-lg text-tertiary md:text-xl">
                                    Have a project in mind? Tell us about it and our engineering team will get back to you within 24 hours with a
                                    free assessment.
                                </p>
                            </div>

                            <div className="mt-4 grid grid-cols-1 gap-8 sm:grid-cols-3 lg:grid-cols-1 lg:gap-6">
                                {contactMethods.map((method) => {
                                    const Icon = method.icon;
                                    return (
                                        <div key={method.title} className="flex items-start gap-4">
                                            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-brand-secondary">
                                                <Icon className="size-5 text-fg-white" />
                                            </div>
                                            <div>
                                                <p className="text-sm font-semibold text-primary">{method.title}</p>
                                                <p className="text-sm text-tertiary">{method.description}</p>
                                                <a
                                                    href={method.href}
                                                    className="mt-1 text-sm font-semibold text-brand-secondary transition duration-100 ease-linear hover:text-brand-secondary_hover"
                                                >
                                                    {method.contact}
                                                </a>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="rounded-2xl border border-secondary bg-primary p-6 md:p-8">
                            <form
                                className="flex flex-col gap-5"
                                onSubmit={(e) => {
                                    e.preventDefault();
                                }}
                            >
                                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                                    <Input label="First name" placeholder="First name" size="md" />
                                    <Input label="Last name" placeholder="Last name" size="md" />
                                </div>
                                <Input label="Email" placeholder="you@company.com" size="md" type="email" />
                                <Input label="Company" placeholder="Your company name" size="md" />
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-sm font-medium text-secondary">Tell us about your project</label>
                                    <textarea
                                        placeholder="Describe what you're looking to build, your timeline, and any technical requirements..."
                                        rows={4}
                                        className="w-full resize-none rounded-lg border border-primary bg-primary px-3.5 py-2.5 text-md text-primary shadow-xs outline-none transition duration-100 ease-linear placeholder:text-placeholder focus:border-brand focus:ring-4 focus:ring-brand/12"
                                    />
                                </div>
                                <Button size="xl" type="submit" className="mt-2">
                                    Send message
                                </Button>
                                <p className="text-center text-sm text-tertiary">
                                    We&apos;ll get back to you within 24 hours.
                                </p>
                            </form>
                        </div>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
