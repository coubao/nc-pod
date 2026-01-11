#!/usr/bin/env python3
"""Lightweight scraper for 1point3acres application case posts.

The script collects application case posts from a forum list such as
https://www.1point3acres.com/bbs/forum-71-1.html.  It walks one or more
pages, extracts thread links, fetches each thread, and parses the first
post for common application fields like school, degree, and scores.

Usage example:
    python scrape_1point3acres.py \
        --forum-url https://www.1point3acres.com/bbs/forum-71-1.html \
        --pages 3 --output cases.json
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urljoin
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass
class ApplicationCase:
    """Normalized details scraped from an application case thread."""

    title: str
    url: str
    author: Optional[str] = None
    posted_at: Optional[str] = None
    application_term: Optional[str] = None
    school: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    gpa: Optional[str] = None
    gre: Optional[str] = None
    toefl: Optional[str] = None
    background: Optional[str] = None
    raw_content: str = field(default="")


class ListingParser(HTMLParser):
    """Extract thread titles and URLs from a listing page."""

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.results: List[Tuple[str, str]] = []
        self._in_thread_tbody = False
        self._capture_text = False
        self._current_href: Optional[str] = None
        self._text_chunks: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attrs_dict = dict(attrs)
        if tag == "tbody":
            tbody_id = attrs_dict.get("id", "")
            self._in_thread_tbody = tbody_id.startswith("normalthread")
        if not self._in_thread_tbody:
            return
        if tag == "a":
            classes = attrs_dict.get("class", "")
            if "s" in classes.split() and "xst" in classes.split():
                href = attrs_dict.get("href")
                if href:
                    self._capture_text = True
                    self._current_href = urljoin(self.base_url, href)
                    self._text_chunks = []

    def handle_endtag(self, tag: str):
        if tag == "tbody" and self._in_thread_tbody:
            self._in_thread_tbody = False
        if tag == "a" and self._capture_text:
            title = "".join(self._text_chunks).strip()
            if title and self._current_href:
                self.results.append((html.unescape(title), self._current_href))
            self._capture_text = False
            self._current_href = None
            self._text_chunks = []

    def handle_data(self, data: str):
        if self._capture_text:
            self._text_chunks.append(data)


def extract_thread_links(list_html: str, base_url: str) -> List[tuple[str, str]]:
    parser = ListingParser(base_url)
    parser.feed(list_html)
    return parser.results


class PostParser(HTMLParser):
    """Extract first-post content and metadata from a thread page."""

    def __init__(self):
        super().__init__()
        self.author: Optional[str] = None
        self.posted_at: Optional[str] = None
        self.raw_chunks: List[str] = []
        self._capture_post = False
        self._capture_author = False
        self._capture_time = False
        self._seen_post = False
        self._in_authi = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attrs_dict = dict(attrs)
        if tag == "td" and not self._seen_post:
            element_id = attrs_dict.get("id", "")
            if element_id.startswith("postmessage"):
                self._capture_post = True
                self._seen_post = True
        if tag == "div":
            classes = attrs_dict.get("class", "")
            if "authi" in classes.split():
                self._in_authi = True
        if self._in_authi and tag == "a":
            self._capture_author = True
        if self._in_authi and tag == "em":
            self._capture_time = True
        if self._capture_post and tag in {"br", "p", "div"}:
            self.raw_chunks.append("\n")

    def handle_endtag(self, tag: str):
        if tag == "td" and self._capture_post:
            self._capture_post = False
        if tag == "div" and self._in_authi:
            self._in_authi = False
        if tag == "a" and self._capture_author:
            self._capture_author = False
        if tag == "em" and self._capture_time:
            self._capture_time = False

    def handle_data(self, data: str):
        if self._capture_author and not self.author:
            self.author = data.strip()
        elif self._capture_time and not self.posted_at:
            self.posted_at = data.replace("发表于", "").strip()
        if self._capture_post:
            self.raw_chunks.append(data)

    @property
    def text(self) -> str:
        return "".join(self.raw_chunks).strip()


FIELD_PATTERNS = {
    "application_term": [r"申请季[:：]\s*([^\n]+)", r"申请时间[:：]\s*([^\n]+)"],
    "school": [r"学校[:：]\s*([^\n]+)", r"院校[:：]\s*([^\n]+)"],
    "degree": [r"学位[:：]\s*([^\n]+)", r"学位/学程[:：]\s*([^\n]+)", r"项目[:：]\s*([^\n]+)"],
    "major": [r"专业[:：]\s*([^\n]+)"],
    "gpa": [r"GPA[:：]\s*([^\n]+)", r"绩点[:：]\s*([^\n]+)"],
    "gre": [r"GRE[:：]\s*([^\n]+)", r"GRE/GMAT[:：]\s*([^\n]+)"],
    "toefl": [r"TOEFL[:：]\s*([^\n]+)", r"雅思[:：]\s*([^\n]+)", r"语言[:：]\s*([^\n]+)"],
    "background": [r"背景[:：]\s*([^\n]+)", r"实验/实习[:：]\s*([^\n]+)", r"工作[:：]\s*([^\n]+)", r"科研[:：]\s*([^\n]+)"],
}


def build_page_url(base_url: str, page: int) -> str:
    """Return the URL for a specific page number."""

    if page == 1:
        return base_url

    match = re.search(r"-(\d+)\.html$", base_url)
    if match:
        return re.sub(r"-\d+\.html$", f"-{page}.html", base_url)

    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}page={page}"


def fetch(url: str) -> str:
    """Fetch a URL with a browser-like User-Agent."""

    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:  # nosec: trusted domain provided by user
        encoding = response.headers.get_content_charset("utf-8")
        return response.read().decode(encoding, errors="replace")


def parse_application_data(thread_html: str, url: str, title: str) -> ApplicationCase:
    parser = PostParser()
    parser.feed(thread_html)

    case = ApplicationCase(title=title, url=url)
    case.author = parser.author
    case.posted_at = parser.posted_at
    case.raw_content = parser.text

    for field_name, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, case.raw_content, flags=re.IGNORECASE)
            if match:
                setattr(case, field_name, match.group(1).strip())
                break

    return case


def scrape_forum(forum_url: str, pages: int, delay: float, limit: Optional[int] = None) -> List[ApplicationCase]:
    cases: List[ApplicationCase] = []
    for page in range(1, pages + 1):
        page_url = build_page_url(forum_url, page)
        html_body = fetch(page_url)
        thread_links = extract_thread_links(html_body, page_url)
        for title, link in thread_links:
            if limit is not None and len(cases) >= limit:
                return cases
            thread_html = fetch(link)
            case = parse_application_data(thread_html, link, title=title)
            cases.append(case)
            time.sleep(delay)
        time.sleep(delay)
    return cases


def save_cases(cases: Iterable[ApplicationCase], output_path: str) -> None:
    if output_path.lower().endswith(".json"):
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump([asdict(case) for case in cases], fh, ensure_ascii=False, indent=2)
    elif output_path.lower().endswith(".csv"):
        cases_list = list(cases)
        fieldnames = list(asdict(cases_list[0]).keys()) if cases_list else list(ApplicationCase.__annotations__.keys())
        with open(output_path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for case in cases_list:
                writer.writerow(asdict(case))
    else:
        raise ValueError("Output file must end with .json or .csv")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape 1point3acres application cases")
    parser.add_argument("--forum-url", required=True, help="Forum list URL (e.g. https://www.1point3acres.com/bbs/forum-71-1.html)")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to scrape")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds")
    parser.add_argument("--limit", type=int, help="Stop after scraping N threads")
    parser.add_argument("--output", default="cases.json", help="Path to write .json or .csv results")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        cases = scrape_forum(args.forum_url, args.pages, args.delay, args.limit)
        save_cases(cases, args.output)
    except Exception as exc:  # pragma: no cover - safety net for CLI
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    print(f"Scraped {len(cases)} threads into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
