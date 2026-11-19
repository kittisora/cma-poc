"use client";

import type { HTMLAttributes } from "react";
import { cx } from "@/utils/cx";

/** App mark: a house with a rising price line, in the brand color. */
export const CmaMark = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
        <rect width="32" height="32" rx="7" className="fill-brand-solid" />
        <path d="M7 15.5 16 8l9 7.5V24a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1z" fill="none" stroke="white" strokeWidth="2" strokeLinejoin="round" />
        <path d="m10.5 21 3.5-3.5 2.5 2 4.5-4.5" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
);

export const UntitledLogoMinimal = (props: HTMLAttributes<HTMLDivElement>) => {
    return (
        <div {...props} role="img" aria-label="CMA" className={cx("size-8 shrink-0", props.className)}>
            <CmaMark className="size-full" />
        </div>
    );
};
