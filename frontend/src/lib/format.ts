const usd0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const usd2 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
const int = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

export const money = (v: number | null | undefined, cents = false) => (v === null || v === undefined ? "—" : (cents ? usd2 : usd0).format(v));
export const num = (v: number | null | undefined) => (v === null || v === undefined ? "—" : int.format(v));
export const sf = (v: number | null | undefined) => (v ? `${int.format(v)} sf` : "—");
export const signedMoney = (v: number) => `${v >= 0 ? "+" : "-"}${usd0.format(Math.abs(v))}`;
export const pct = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
export const ppsf = (v: number | null | undefined) => (v ? `$${v.toFixed(0)}` : "—");

export const PROPERTY_TYPES: Record<string, string> = {
    DETACHED: "Single-family detached",
    TOWNHOUSE: "Townhouse",
    CONDO: "Condominium",
    DUPLEX: "Duplex",
    OTHER: "Other",
};

export const PROVIDER_LABEL: Record<string, string> = { openai: "OpenAI", anthropic: "Anthropic" };
