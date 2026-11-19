"use client";

import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle, InfoCircle, XCircle } from "@untitledui/icons";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { cx } from "@/utils/cx";

type Tone = "info" | "warning" | "error" | "success";

const ICONS = { info: InfoCircle, warning: AlertTriangle, error: XCircle, success: CheckCircle };
const COLORS = { info: "brand", warning: "warning", error: "error", success: "success" } as const;
const BG = {
    info: "bg-primary ring-secondary",
    warning: "bg-warning-primary ring-secondary",
    error: "bg-error-primary ring-error_subtle",
    success: "bg-success-primary ring-secondary",
};

interface CalloutProps {
    tone?: Tone;
    title?: ReactNode;
    children?: ReactNode;
    actions?: ReactNode;
    className?: string;
    role?: "status" | "alert";
}

/** Inline notice built from the library's FeaturedIcon and semantic color tokens. */
export function Callout({ tone = "info", title, children, actions, className, role }: CalloutProps) {
    return (
        <div role={role} className={cx("flex gap-3 rounded-xl p-4 ring-1 ring-inset", BG[tone], className)}>
            <FeaturedIcon icon={ICONS[tone]} color={COLORS[tone]} theme="outline" size="sm" className="mt-0.5 ml-1 shrink-0" />
            <div className="flex min-w-0 flex-1 flex-col gap-1 pl-1">
                {title && <p className="text-sm font-semibold text-secondary">{title}</p>}
                {children && <div className="text-sm text-tertiary">{children}</div>}
                {actions && <div className="mt-2 flex flex-wrap gap-2">{actions}</div>}
            </div>
        </div>
    );
}
