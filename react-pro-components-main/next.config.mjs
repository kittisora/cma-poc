/** @type {import('next').NextConfig} */
const nextConfig = {
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

export default nextConfig;
