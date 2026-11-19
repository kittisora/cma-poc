import { PHASE_DEVELOPMENT_SERVER } from "next/constants.js";

/**
 * Production: a static export (`npm run build` -> out/) that FastAPI serves next to /api,
 * so the whole app runs as one server and provider keys never reach the browser.
 * Development: `next dev` on :3000 proxies /api to FastAPI on :8000 (override with CMA_API_URL).
 */
const shared = {
    reactStrictMode: true,
    images: { unoptimized: true },
    experimental: {
        optimizePackageImports: [
            "@untitledui/icons",
            "react-aria-components",
            "react-aria",
            "@react-aria/utils",
            "@react-stately/utils",
            "recharts",
            "shiki",
            "@tiptap/core",
            "@tiptap/react",
            "@tiptap/starter-kit",
            "@tiptap/pm",
            "motion",
        ],
    },
};

export default function config(phase) {
    if (phase === PHASE_DEVELOPMENT_SERVER) {
        const api = process.env.CMA_API_URL ?? "http://127.0.0.1:8000";
        return {
            ...shared,
            async rewrites() {
                return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
            },
        };
    }
    return { ...shared, output: "export" };
}
