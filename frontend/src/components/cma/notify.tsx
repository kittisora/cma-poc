"use client";

import { AlertTriangle, CheckCircle, InfoCircle } from "@untitledui/icons";
import { toast } from "sonner";
import { IconNotification } from "@/components/application/notifications/notifications";

type Kind = "success" | "error" | "info";

const ICON = { success: CheckCircle, error: AlertTriangle, info: InfoCircle };
const COLOR = { success: "success", error: "error", info: "brand" } as const;

/** Toast using the library's IconNotification card. */
export const notify = (kind: Kind, title: string, description = "") =>
    toast.custom(
        (t) => (
            <IconNotification
                title={title}
                description={description}
                color={COLOR[kind]}
                icon={ICON[kind]}
                hideDismissLabel
                onClose={() => toast.dismiss(t)}
            />
        ),
        { duration: kind === "error" ? 8000 : 4000 },
    );
