"""Browser end-to-end check of the full workflow on the Next.js UI, timed.

    python scripts/e2e_ui.py [--base http://127.0.0.1:8000] [--out reports_dir] [--channel msedge|chrome] [--screenshots dir]

For each address: type it, pick the match, wait for comps and pricing, click a
map marker and confirm its table row highlights, open the comp detail panel,
exclude a comp and confirm the estimate changes, reset, draft the narrative,
preview, then download the PDF and Word reports. Also opens the AI panel (with
--ask-ai, asks one question), the
Workbook check and Data pages, and dark mode. Prints timings and any page or
console errors. Requires `pip install playwright` and a local Edge or Chrome.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ADDRESSES = [("8069 fairfax rd", "22308"), ("7910 martha washington", "22309")]
NOT_BUSY = "!document.querySelector('[aria-busy=true]')"


def clear_toasts(page) -> None:
    """Wait for transient notifications to close so they cannot cover what is clicked next."""
    expect(page.locator("[data-sonner-toast]")).to_have_count(0, timeout=15_000)


def run(base: str, out: Path, channel: str, shots: Path | None, ask_ai: bool = False) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=channel, headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, accept_downloads=True, color_scheme="light")
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
        page.goto(base)
        box = page.get_by_role("combobox", name="Subject address")
        expect(box).to_be_visible(timeout=20_000)
        if shots:
            page.screenshot(path=str(shots / "start.png"))

        for query, zip_code in ADDRESSES:
            r: dict = {"query": query, "zip": zip_code}
            t0 = time.perf_counter()
            box.click()
            box.fill(query)
            option = page.get_by_role("option", name=query.split()[0]).first
            expect(option).to_be_visible(timeout=10_000)
            r["search_s"] = round(time.perf_counter() - t0, 2)
            option.click()
            est = page.get_by_test_id("estimate-value")
            heading = page.locator("#subject-heading")
            expect(heading).to_contain_text(query.split()[0], timeout=20_000, ignore_case=True)
            expect(est).to_be_visible(timeout=20_000)
            page.wait_for_function(NOT_BUSY, timeout=20_000)
            r["comps_and_pricing_s"] = round(time.perf_counter() - t0, 2)
            r["estimate"] = est.inner_text()
            r["subject"] = heading.inner_text()
            table = page.get_by_test_id("comp-table")
            r["selected_comps"] = table.locator("[role=row][aria-selected=true]").count()
            if shots:
                page.screenshot(path=str(shots / f"cma_{zip_code}.png"))
                if zip_code == "22308":
                    table.screenshot(path=str(shots / "comp_table.png"))

            # map -> table: clicking comp marker 2 highlights its table row
            clear_toasts(page)
            page.locator(".leaflet-marker-icon [data-comp-pin='2']").click()
            hi = table.locator("[role=row][data-highlighted]")
            expect(hi).to_have_count(1)
            r["map_click_highlights_row"] = hi.get_attribute("data-comp-no") == "2"

            # comp detail slide-out
            hi.get_by_role("button", name="Details for").click()
            panel = page.get_by_role("dialog")
            expect(panel.get_by_text("Similarity factors")).to_be_visible()
            r["comp_detail_opens"] = True
            if shots and zip_code == "22308":
                page.wait_for_timeout(700)  # let the slide-in animation finish
                page.screenshot(path=str(shots / "comp_detail.png"))
            page.keyboard.press("Escape")
            expect(panel).to_have_count(0)

            # exclude comp 1 (uncheck its row), the estimate changes; then reset to the automatic top 5
            before = est.inner_text()
            table.locator("[role=row][data-comp-no='1']").get_by_role("checkbox").click(force=True)
            page.wait_for_function(NOT_BUSY, timeout=20_000)
            expect(est).not_to_have_text(before, timeout=10_000)
            r["exclude_changes_estimate"] = True
            page.get_by_role("button", name="Reset to the top 5").click()
            expect(est).to_have_text(before, timeout=10_000)

            # report: draft the narrative, preview, export PDF and Word
            page.get_by_role("tab", name="Report").click()
            page.get_by_role("button", name="Draft narrative").or_(page.get_by_role("button", name="Draft with AI")).click()
            expect(page.get_by_role("textbox", name="Narrative text")).not_to_have_value("", timeout=90_000)
            page.get_by_role("button", name="Preview").click()
            preview = page.get_by_role("dialog", name="Report preview")
            expect(preview).to_be_visible(timeout=20_000)
            if shots:
                clear_toasts(page)
                page.screenshot(path=str(shots / f"report_{zip_code}.png"))
            page.keyboard.press("Escape")
            expect(preview).to_have_count(0)
            for fmt, label in (("pdf", "Export PDF"), ("docx", "Export Word")):
                with page.expect_download(timeout=60_000) as dl:
                    page.get_by_role("button", name=label).click()
                d = dl.value
                target = out / d.suggested_filename
                d.save_as(target)
                r[f"{fmt}_file"] = str(target)
                r[f"{fmt}_bytes"] = target.stat().st_size
            r["total_s"] = round(time.perf_counter() - t0, 2)
            page.get_by_role("tab", name="Pricing").click()
            results.append(r)

        # AI assistant panel opens (shows setup help when no key is configured)
        clear_toasts(page)
        # the side panel scrolls independently; bring its top (the estimate card) back into view
        page.locator("aside[aria-label='Valuation and report']").evaluate("el => el.scrollTo(0, 0)")
        page.get_by_role("button", name="Ask AI").click()
        ai = page.get_by_role("dialog")
        expect(ai.get_by_text("Ask about this CMA").first).to_be_visible()
        if ask_ai:
            # one real question (costs one AI call); the reply must cite a county record
            t_ai = time.perf_counter()
            ai.get_by_role("button", name="Why were these comps chosen, and which is the weakest?").click()
            reply = ai.get_by_test_id("ai-reply").first
            expect(reply).to_be_visible(timeout=180_000)
            results.append({"ai_reply_s": round(time.perf_counter() - t_ai, 1),
                            "ai_reply_cites_record": "PARID" in reply.inner_text(),
                            "ai_reply_start": reply.inner_text()[:160]})
        if shots:
            page.wait_for_timeout(700)
            page.screenshot(path=str(shots / "ask_ai.png"))
        page.keyboard.press("Escape")

        # other pages
        page.get_by_role("link", name="Workbook check").first.click()
        # the saved subject is either a workbook example (regression badge) or a county property (facts strip)
        expect(page.get_by_text("Regression passed").or_(page.get_by_test_id("workbook-subject-facts"))).to_be_visible(timeout=20_000)
        if shots:
            page.screenshot(path=str(shots / "workbook_check.png"))
        page.get_by_role("link", name="Data & sources").first.click()
        expect(page.get_by_text("Workbook fields and where they come from")).to_be_visible(timeout=20_000)
        if shots:
            page.screenshot(path=str(shots / "data_sources.png"))
        page.get_by_role("link", name="CMA", exact=True).first.click()
        expect(page.get_by_test_id("estimate-value")).to_be_visible(timeout=20_000)
        results.append({"navigation_keeps_cma_state": True})

        # dark mode
        page.get_by_role("button", name="Dark mode").click()
        expect(page.locator("html.dark-mode")).to_have_count(1)
        if shots:
            page.wait_for_timeout(800)  # let colour transitions finish
            page.screenshot(path=str(shots / "cma_dark.png"))
        page.get_by_role("button", name="Light mode").click()

        results.append({"page_errors": errors})
        browser.close()
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default="e2e_output")
    ap.add_argument("--channel", default="msedge")
    ap.add_argument("--screenshots", default="")
    ap.add_argument("--ask-ai", action="store_true", help="also ask the AI one question (one paid AI call)")
    a = ap.parse_args()
    shots = Path(a.screenshots) if a.screenshots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(a.base, Path(a.out), a.channel, shots, a.ask_ai), indent=2))
