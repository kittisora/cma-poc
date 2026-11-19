import type { Metadata } from "next";
import { WorkbookView } from "@/components/cma/workbook-view";

export const metadata: Metadata = { title: "Workbook check" };

export default function Page() {
    return <WorkbookView />;
}
