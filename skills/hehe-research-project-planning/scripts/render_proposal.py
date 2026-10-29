"""Assemble explicitly designed slides into a standalone 16:9 presentation."""
import argparse
import html
import json
from pathlib import Path
from urllib.parse import quote

def render(source, target):
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    title = data["title"]
    slides = []
    if not data.get("slides"):
        raise ValueError("需要先设计逐页内容与版式，再生成HTML。")
    for slide in data["slides"]:
        kind = slide.get("kind", "content")
        if kind not in ("content", "cover", "toc", "chapter"):
            raise ValueError("未知页面类型：" + kind)
        section, heading = slide["section"].strip(), slide["title"].strip()
        if section == heading:
            raise ValueError("章节标签与页面标题不能重复：" + heading)
        if kind == "content" and not slide.get("lead", "").strip():
            raise ValueError("正文页副标题不能为空：" + heading)
        if not slide.get("body", "").strip():
            raise ValueError("页面内容为空：" + heading)
        slides.append(
            '<section class="slide ' + ('body-page' if kind == 'content' else kind) + '"><div class="eyebrow">' + html.escape(section)
            + '</div><h1>' + html.escape(heading) + '</h1><p class="lead">'
            + html.escape(slide.get("lead", "")) + '</p><div class="content">'
            + slide["body"] + '</div><footer><span>'
            + html.escape(slide.get("footer", data.get("footer", "研究项目建议书")))
            + '</span><span class="page"></span></footer></section>'
        )
    template = (Path(__file__).resolve().parents[1] / "assets/proposal-slides.html").read_text(encoding="utf-8")
    # body is locally authored presentation markup, never raw third-party HTML.
    result = template.replace("__TITLE__", html.escape(title)).replace("__SLIDES__", "\n".join(slides))
    pdf = data.get("pdf_file")
    link = "<!--PDF_DOWNLOAD-->"
    if pdf:
        if Path(pdf).name != pdf or not pdf.lower().endswith(".pdf"):
            raise ValueError("pdf_file必须是同目录PDF文件名")
        if (target.parent / pdf).is_file():
            link = '<a class="pdf-download" href="' + html.escape(quote(pdf), quote=True) + '" download>下载 PDF（16:9）</a>'
    result = result.replace("__PDF_LINK__", link)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as f:
        f.write(result)
    return target

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(render(args.source, args.target))
