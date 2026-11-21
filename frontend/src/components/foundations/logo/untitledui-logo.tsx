"use client";

import type { HTMLAttributes } from "react";
import { cx } from "@/utils/cx";
import { CmaMark } from "./untitledui-logo-minimal";

/** App logo used by the navigation components. */
export const UntitledLogo = (props: HTMLAttributes<HTMLDivElement>) => {
    return (
        <div {...props} className={cx("flex h-8 w-max items-center gap-2", props.className)}>
            <CmaMark className="aspect-square h-full shrink-0" />
            <span className="text-md font-semibold whitespace-nowrap text-primary">
                CMA <span className="font-medium text-tertiary">Fairfax</span>
            </span>
        </div>
    );
};
