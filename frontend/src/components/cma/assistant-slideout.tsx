"use client";

import { useEffect, useRef, useState } from "react";
import { Send01, Stars02 } from "@untitledui/icons";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { SlideoutMenu } from "@/components/application/slideout-menus/slideout-menu";
import { Avatar } from "@/components/base/avatar/avatar";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { api } from "@/lib/api";
import { PROVIDER_LABEL } from "@/lib/format";
import type { ChatMessage, CMARequest } from "@/lib/types";
import { cx } from "@/utils/cx";
import { Callout } from "./callout";
import { MarkdownMessage } from "./markdown-message";

const SUGGESTIONS = [
    "Why were these comps chosen, and which is the weakest?",
    "Walk me through how the estimate was calculated.",
    "What does the county record say about condition, and what should be inspected?",
    "Did any filter limit the search?",
];

interface Props {
    open: boolean;
    onClose: () => void;
    req: CMARequest | null;
    subjectLabel: string;
    enabled: boolean;
    model: string;
    provider: string | null;
}

/** Chat with the AI assistant about the current CMA. It reads the computed results through tools and cannot change them. */
export function AssistantSlideout({ open, onClose, req, subjectLabel, enabled, model, provider }: Props) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setMessages([]);
    }, [req?.subject_pin]);
    // Block body: scrollIntoView() returns a Promise in recent browsers, and an effect must not return one.
    useEffect(() => {
        endRef.current?.scrollIntoView({ block: "end" });
    }, [messages, busy]);

    const send = async (text: string) => {
        if (!req || !text.trim() || busy) return;
        const next: ChatMessage[] = [...messages, { role: "user", content: text.trim() }];
        setMessages(next);
        setInput("");
        setBusy(true);
        setError("");
        try {
            const r = await api.chat(
                req,
                next.map(({ role, content }) => ({ role, content })),
            );
            setMessages([...next, { role: "assistant", content: r.reply, tool_calls: r.tool_calls }]);
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setBusy(false);
        }
    };

    return (
        <SlideoutMenu isOpen={open} onOpenChange={(o) => !o && onClose()} isDismissable className="max-w-xl">
            <SlideoutMenu.Header onClose={onClose} className="flex items-start gap-3">
                <Avatar size="md" placeholderIcon={Stars02} alt="AI assistant" />
                <div className="flex min-w-0 flex-col gap-0.5 pr-8">
                    <h2 className="text-lg font-semibold text-primary">Ask about this CMA</h2>
                    <p className="truncate text-sm text-tertiary">{subjectLabel}</p>
                    {enabled && (
                        <div className="pt-1">
                            <Badge type="modern" color="gray" size="sm">
                                {PROVIDER_LABEL[provider ?? ""] ?? "AI"} · {model}
                            </Badge>
                        </div>
                    )}
                </div>
            </SlideoutMenu.Header>

            <SlideoutMenu.Content className="gap-4">
                {!enabled ? (
                    <Callout tone="info" title="The AI assistant is not configured">
                        Add <code>OPENAI_API_KEY</code> to the server&apos;s <code>.env</code> and restart. Search, ranking, pricing and reports work without it.
                    </Callout>
                ) : (
                    <>
                        <p className="text-xs text-tertiary">
                            The assistant reads the computed facts, comps and valuation through tools and cites the county records. It cannot change the figures.
                        </p>
                        {messages.length === 0 && (
                            <div className="flex flex-col gap-2">
                                {SUGGESTIONS.map((s) => (
                                    <Button key={s} size="sm" color="secondary" className="justify-start text-left" onClick={() => send(s)}>
                                        {s}
                                    </Button>
                                ))}
                            </div>
                        )}
                        <ol className="flex flex-col gap-4" aria-live="polite">
                            {messages.map((m, i) => (
                                <li key={i} className={cx("flex gap-3", m.role === "user" ? "justify-end pl-10" : "pr-2")}>
                                    {m.role === "assistant" && <Avatar size="sm" placeholderIcon={Stars02} alt="AI assistant" />}
                                    <div className="flex min-w-0 flex-col gap-1">
                                        <div
                                            data-testid={m.role === "assistant" ? "ai-reply" : undefined}
                                            className={cx(
                                                "rounded-lg px-3 py-2 text-sm text-primary ring-1 ring-secondary ring-inset",
                                                m.role === "user" ? "rounded-tr-none bg-brand-primary_alt whitespace-pre-wrap" : "rounded-tl-none bg-secondary",
                                            )}
                                        >
                                            {m.role === "assistant" ? <MarkdownMessage text={m.content} /> : m.content}
                                        </div>
                                        {m.tool_calls && m.tool_calls.length > 0 && (
                                            <div className="flex flex-wrap gap-1">
                                                {m.tool_calls.map((t, j) => (
                                                    <Badge key={j} type="pill-color" color={t.error ? "error" : "gray"} size="sm">
                                                        read {t.tool.replace(/^get_/, "").replace(/_/g, " ")}
                                                    </Badge>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </li>
                            ))}
                        </ol>
                        {busy && <LoadingIndicator type="dot-circle" size="sm" label="Reading the CMA…" />}
                        {error && (
                            <Callout tone="error" title="The assistant could not answer" role="alert">
                                {error}
                            </Callout>
                        )}
                        <div ref={endRef} />
                    </>
                )}
            </SlideoutMenu.Content>

            {enabled && (
                <SlideoutMenu.Footer>
                    <form
                        className="flex items-end gap-2"
                        onSubmit={(e) => {
                            e.preventDefault();
                            send(input);
                        }}
                    >
                        <Input aria-label="Ask about this CMA" placeholder="Ask about this CMA…" className="flex-1" value={input} onChange={setInput} isDisabled={busy} />
                        <Button type="submit" iconLeading={Send01} isDisabled={busy || !input.trim()}>
                            Ask
                        </Button>
                    </form>
                </SlideoutMenu.Footer>
            )}
        </SlideoutMenu>
    );
}
