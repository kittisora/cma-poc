"use client";

import type { PropsWithChildren } from "react";
import { useEffect, useState } from "react";
import { BarChartSquare02, Calculator, Database02, Moon01, Stars02, Sun, Tool02 } from "@untitledui/icons";
import { useTheme } from "next-themes";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MobileNavigationHeader } from "@/components/application/app-navigation/base-components/mobile-header";
import { NavButton } from "@/components/application/app-navigation/base-components/nav-button";
import { NavList } from "@/components/application/app-navigation/base-components/nav-list";
import type { NavItemType } from "@/components/application/app-navigation/config";
import { BadgeWithDot } from "@/components/base/badges/badges";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { Tooltip, TooltipTrigger } from "@/components/base/tooltip/tooltip";
import { UntitledLogo } from "@/components/foundations/logo/untitledui-logo";
import { PROVIDER_LABEL } from "@/lib/format";
import { useCma } from "@/providers/cma-provider";

const NAV: (NavItemType & { href: string })[] = [
    { label: "CMA", href: "/", icon: BarChartSquare02 },
    { label: "Permits", href: "/permits", icon: Tool02 },
    { label: "Workbook check", href: "/workbook", icon: Calculator },
    { label: "Data & sources", href: "/data", icon: Database02 },
];

const ThemeToggle = () => {
    const { resolvedTheme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    useEffect(() => {
        setMounted(true);
    }, []);
    const dark = mounted && resolvedTheme === "dark";
    return (
        <ButtonUtility
            size="sm"
            color="tertiary"
            icon={dark ? Sun : Moon01}
            tooltip={dark ? "Light mode" : "Dark mode"}
            tooltipPlacement="bottom"
            onClick={() => setTheme(dark ? "light" : "dark")}
        />
    );
};

const StatusBadges = () => {
    const { meta } = useCma();
    if (!meta) return null;
    return (
        <div className="flex flex-wrap items-center gap-2">
            <Tooltip title="Data source" description={meta.provider.attribution} placement="bottom">
                <TooltipTrigger>
                    <BadgeWithDot type="modern" color="brand" size="md">
                        Public records · latest sale {meta.data.latest_sale_date ?? "—"}
                    </BadgeWithDot>
                </TooltipTrigger>
            </Tooltip>
            <BadgeWithDot type="modern" color={meta.ai_enabled ? "success" : "gray"} size="md">
                {meta.ai_enabled ? `AI · ${PROVIDER_LABEL[meta.ai_provider ?? ""] ?? ""} ${meta.ai_model}` : "AI off"}
            </BadgeWithDot>
        </div>
    );
};

const isActive = (href: string, path: string) => (href === "/" ? path === "/" : path === href || path.startsWith(`${href}/`));

export function AppShell({ children }: PropsWithChildren) {
    const pathname = usePathname() || "/";
    const { meta } = useCma();
    const activeHref = NAV.find((n) => isActive(n.href, pathname))?.href;

    return (
        <div className="flex min-h-dvh flex-col bg-secondary">
            <a
                href="#main"
                className="sr-only z-50 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
            >
                Skip to content
            </a>

            <MobileNavigationHeader>
                <aside className="flex h-full max-w-full flex-col gap-5 overflow-auto bg-primary pt-4">
                    <div className="px-4">
                        <UntitledLogo className="h-8" />
                    </div>
                    <NavList activeUrl={activeHref} items={NAV} />
                    <div className="mt-auto flex flex-col gap-3 p-4">
                        <StatusBadges />
                        <ThemeToggle />
                    </div>
                </aside>
            </MobileNavigationHeader>

            <header className="sticky top-0 z-30 border-b border-secondary bg-primary max-lg:hidden">
                <div className="mx-auto flex h-16 w-full max-w-[1760px] items-center gap-6 px-6">
                    <Link href="/" aria-label="CMA home" className="rounded-xs outline-focus-ring focus-visible:outline-2 focus-visible:outline-offset-2">
                        <UntitledLogo className="h-8" />
                    </Link>
                    <nav aria-label="Sections">
                        <ul className="flex items-center gap-0.5">
                            {NAV.map((item) => (
                                <li key={item.href}>
                                    <NavButton current={activeHref === item.href} href={item.href} icon={item.icon} label={item.label}>
                                        {item.label}
                                    </NavButton>
                                </li>
                            ))}
                        </ul>
                    </nav>
                    <div className="ml-auto flex items-center gap-3">
                        <StatusBadges />
                        <ThemeToggle />
                    </div>
                </div>
            </header>

            <div id="main" className="mx-auto flex w-full max-w-[1760px] flex-1 flex-col px-4 py-6 md:px-6">
                {children}
            </div>

            <footer className="border-t border-secondary bg-primary">
                <div className="mx-auto flex w-full max-w-[1760px] flex-wrap items-center gap-x-2 gap-y-1 px-4 py-4 text-xs text-tertiary md:px-6">
                    <span>Data: Fairfax County, Virginia public records via ArcGIS Online.</span>
                    <span>Not MLS data. Not an appraisal.</span>
                    {meta && (
                        <a href={meta.provider.terms_url} target="_blank" rel="noreferrer" className="font-semibold text-brand-secondary hover:underline">
                            County data terms
                        </a>
                    )}
                    <span className="ml-auto inline-flex items-center gap-1">
                        <Stars02 className="size-3.5" aria-hidden="true" />
                        Ranking and pricing run in tested backend code; AI only explains.
                    </span>
                </div>
            </footer>
        </div>
    );
}
