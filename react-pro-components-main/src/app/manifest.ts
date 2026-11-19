import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
    return {
        name: "Mirimera — Custom Software Development & Tech Solutions",
        short_name: "Mirimera",
        description:
            "Mirimera engineers custom web apps, mobile applications, AI solutions, and scalable cloud infrastructure for businesses worldwide.",
        start_url: "/",
        display: "standalone",
        background_color: "#ffffff",
        theme_color: "#2f84f8",
        icons: [
            {
                src: "/icon.png",
                sizes: "any",
                type: "image/png",
            },
        ],
    };
}
