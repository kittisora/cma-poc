import type { Metadata } from "next";
import { PermitsView } from "@/components/cma/permits-view";

export const metadata: Metadata = { title: "Permits" };

export default function Page() {
    return <PermitsView />;
}
