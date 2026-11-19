import type { Metadata } from "next";
import { DataView } from "@/components/cma/data-view";

export const metadata: Metadata = { title: "Data & sources" };

export default function Page() {
    return <DataView />;
}
