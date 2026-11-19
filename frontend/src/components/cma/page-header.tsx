"use client";

import type { ReactNode } from "react";
import { Breadcrumbs } from "@/components/application/breadcrumbs/breadcrumbs";
import { SectionHeader } from "@/components/application/section-headers/section-headers";

interface PageHeaderProps {
    title: string;
    description?: ReactNode;
    crumb?: string;
    actions?: ReactNode;
}

export function PageHeader({ title, description, crumb, actions }: PageHeaderProps) {
    return (
        <SectionHeader.Root className="mb-6">
            {crumb && (
                <Breadcrumbs type="text">
                    <Breadcrumbs.Item href="/">CMA</Breadcrumbs.Item>
                    <Breadcrumbs.Item>{crumb}</Breadcrumbs.Item>
                </Breadcrumbs>
            )}
            <SectionHeader.Group>
                <div className="flex flex-1 flex-col gap-1">
                    <h1 className="text-display-xs font-semibold text-primary">{title}</h1>
                    {description && <SectionHeader.Subheading className="max-w-4xl text-md">{description}</SectionHeader.Subheading>}
                </div>
                {actions && <SectionHeader.Actions>{actions}</SectionHeader.Actions>}
            </SectionHeader.Group>
        </SectionHeader.Root>
    );
}
