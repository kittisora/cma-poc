import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api";
import { PROPERTY_TYPES } from "../format";
import type { SearchResult } from "../types";

interface Props {
  zips: string[];
  onSelect: (r: SearchResult) => void;
}

export function SearchBar({ zips, onSelect }: Props) {
  const [q, setQ] = useState("");
  const [zip, setZip] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [status, setStatus] = useState("");
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const skipNext = useRef(false);

  useEffect(() => {
    if (skipNext.current) {
      // the text was just filled in by choosing an option; don't search again
      skipNext.current = false;
      return;
    }
    if (q.trim().length < 2) {
      setResults([]);
      setStatus("");
      return;
    }
    const ctrl = new AbortController();
    const t = setTimeout(() => {
      api
        .search(q, zip, ctrl.signal)
        .then((r) => {
          setResults(r.results);
          setActive(r.results.length ? 0 : -1);
          setOpen(true);
          setStatus(r.results.length ? `${r.results.length} addresses found` : "No matching address in the loaded ZIP codes");
        })
        .catch((e) => {
          if (e.name !== "AbortError") setStatus(`Search failed: ${e.message}`);
        });
    }, 180);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [q, zip]);

  const choose = (r: SearchResult) => {
    onSelect(r);
    skipNext.current = true;
    setQ(`${r.address}, ${r.zip}`);
    setResults([]);
    setOpen(false);
  };

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((a) => Math.min(results.length - 1, a + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === "Enter" && open && results[active]) {
      e.preventDefault();
      choose(results[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="search">
      <label className="search-label" htmlFor="addr">
        Subject address
      </label>
      <div className="search-row">
        <div className="combo">
          <input
            id="addr"
            ref={inputRef}
            type="search"
            role="combobox"
            aria-expanded={open && results.length > 0}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
            autoComplete="off"
            placeholder="e.g. 8069 Fairfax Rd"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKey}
            onFocus={() => results.length && setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 150)}
          />
          {open && results.length > 0 && (
            <ul id={listId} role="listbox" className="combo-list" aria-label="Matching addresses">
              {results.map((r, i) => (
                <li
                  key={`${r.pin}-${r.address}`}
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={i === active}
                  className={i === active ? "active" : ""}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    choose(r);
                  }}
                  onMouseEnter={() => setActive(i)}
                >
                  <span className="opt-addr">{r.address}</span>
                  <span className="opt-meta">
                    {r.zip} · {PROPERTY_TYPES[r.property_type ?? "OTHER"] ?? r.land_use ?? "—"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <label className="sr-only" htmlFor="zipf">
          ZIP code filter
        </label>
        <select id="zipf" value={zip} onChange={(e) => setZip(e.target.value)} aria-label="ZIP code filter">
          <option value="">All ZIPs</option>
          {zips.map((z) => (
            <option key={z} value={z}>
              {z}
            </option>
          ))}
        </select>
      </div>
      <p role="status" className="sr-only">
        {status}
      </p>
      {status && !open && results.length === 0 && q.trim().length >= 2 && <p className="hint">{status}</p>}
    </div>
  );
}
