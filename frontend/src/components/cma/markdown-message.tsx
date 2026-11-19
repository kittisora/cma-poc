"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renders an AI reply (Markdown: bold, lists, tables). Raw HTML in the reply is not rendered. */
const components: Components = {
    p: ({ children }) => <p className="my-1.5 first:mt-0 last:mb-0">{children}</p>,
    strong: ({ children }) => <strong className="font-semibold text-primary">{children}</strong>,
    ul: ({ children }) => <ul className="my-1.5 flex list-disc flex-col gap-1 pl-5">{children}</ul>,
    ol: ({ children }) => <ol className="my-1.5 flex list-decimal flex-col gap-1 pl-5">{children}</ol>,
    h1: ({ children }) => <p className="mt-3 mb-1 font-semibold text-primary first:mt-0">{children}</p>,
    h2: ({ children }) => <p className="mt-3 mb-1 font-semibold text-primary first:mt-0">{children}</p>,
    h3: ({ children }) => <p className="mt-3 mb-1 font-semibold text-primary first:mt-0">{children}</p>,
    a: ({ href, children }) => (
        <a href={href} target="_blank" rel="noreferrer" className="text-brand-secondary underline underline-offset-2">
            {children}
        </a>
    ),
    code: ({ children }) => <code className="rounded bg-tertiary px-1 text-xs">{children}</code>,
    table: ({ children }) => (
        <div className="my-2 overflow-x-auto rounded-lg ring-1 ring-secondary">
            <table className="w-full text-left text-xs">{children}</table>
        </div>
    ),
    thead: ({ children }) => <thead className="bg-secondary text-quaternary">{children}</thead>,
    th: ({ children }) => <th className="px-2 py-1.5 font-semibold">{children}</th>,
    td: ({ children }) => <td className="border-t border-secondary px-2 py-1.5 align-top">{children}</td>,
};

export function MarkdownMessage({ text }: { text: string }) {
    return (
        <div className="text-sm text-secondary">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                {text}
            </ReactMarkdown>
        </div>
    );
}
