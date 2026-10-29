"""Export an authored proposal to a color 16:9 PDF without browser headers."""
import argparse
import html
import os
import re
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright

def export(source, target, browser_path=None):
    if target.exists():
        raise FileExistsError(target)
    try:
        relative = Path(os.path.relpath(target.resolve(), source.resolve().parent)).as_posix()
        href = quote(relative, safe="/")
    except ValueError:  # Different Windows drives cannot use a relative path.
        href = target.resolve().as_uri()
    link = '<a class="pdf-download" href="' + html.escape(href, quote=True) + '" download>下载 PDF（16:9）</a>'
    original = source.read_text(encoding="utf-8-sig")
    updated, count = re.subn(
        r'<a\b[^>]*\bclass="pdf-download"[^>]*>.*?</a>|<!--PDF_DOWNLOAD-->',
        lambda _: link, original, count=1, flags=re.DOTALL,
    )
    if not count:
        updated, count = re.subn(r'</nav>', lambda _: link + '</nav>', original, count=1)
    if not count:
        raise ValueError("HTML缺少PDF下载入口及导航栏，请使用随包模板生成。")
    with sync_playwright() as p:
        options = {"headless": True}
        if browser_path:
            options["executable_path"] = str(browser_path)
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.context.set_offline(True)
        page.goto(source.resolve().as_uri())
        page.wait_for_function("document.documentElement.dataset.ready === 'true'")
        page.evaluate("document.fonts.ready")
        page.emulate_media(media="print")
        target.parent.mkdir(parents=True, exist_ok=True)
        page.pdf(path=str(target), width="1280px", height="720px",
                 prefer_css_page_size=True, print_background=True,
                 display_header_footer=False,
                 margin={"top":"0","right":"0","bottom":"0","left":"0"})
        browser.close()
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError("PDF未成功生成，HTML下载入口保持不变。")
    source.write_text(updated, encoding="utf-8")
    return target

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    print(export(args.source, args.target, args.browser))
