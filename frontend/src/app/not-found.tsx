"use client";

import { ArrowLeft, SearchLg } from "@untitledui/icons";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { Button } from "@/components/base/buttons/button";

export default function NotFound() {
    return (
        <EmptyState size="lg" className="py-20">
            <EmptyState.Header pattern="circle">
                <EmptyState.FeaturedIcon icon={SearchLg} color="gray" theme="modern" />
            </EmptyState.Header>
            <EmptyState.Content>
                <EmptyState.Title>Page not found</EmptyState.Title>
                <EmptyState.Description>This page does not exist in the CMA app.</EmptyState.Description>
            </EmptyState.Content>
            <EmptyState.Footer>
                <Button href="/" iconLeading={ArrowLeft}>
                    Back to the CMA
                </Button>
            </EmptyState.Footer>
        </EmptyState>
    );
}
