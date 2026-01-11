import textwrap

from scrape_1point3acres import (
    ApplicationCase,
    build_page_url,
    extract_thread_links,
    parse_application_data,
)


def test_build_page_url_discuz_style():
    base = "https://www.1point3acres.com/bbs/forum-71-1.html"
    assert build_page_url(base, 1) == base
    assert build_page_url(base, 2) == "https://www.1point3acres.com/bbs/forum-71-2.html"


def test_build_page_url_query_style():
    base = "https://www.1point3acres.com/bbs/thread.php?fid=80"
    assert build_page_url(base, 3) == "https://www.1point3acres.com/bbs/thread.php?fid=80&page=3"


def test_extract_thread_links_from_listing():
    listing_html = textwrap.dedent(
        """
        <html>
            <body>
                <tbody id="normalthread_1"><tr><th><a class="s xst" href="thread-1-1-1.html">Case A</a></th></tr></tbody>
                <tbody id="normalthread_2"><tr><th><a class="s xst" href="thread-2-1-1.html">Case B</a></th></tr></tbody>
            </body>
        </html>
        """
    )
    threads = extract_thread_links(listing_html, "https://www.1point3acres.com/bbs/forum-71-1.html")
    assert threads == [
        ("Case A", "https://www.1point3acres.com/bbs/thread-1-1-1.html"),
        ("Case B", "https://www.1point3acres.com/bbs/thread-2-1-1.html"),
    ]


def test_parse_application_data_extracts_fields():
    thread_html = textwrap.dedent(
        """
        <html>
            <div id="postlist">
                <div id="post_123">
                    <div class="authi">
                        <a class="xw1" href="space">applicant01</a>
                        <em>发表于 2024-03-01</em>
                    </div>
                    <table>
                        <tr>
                            <td id="postmessage_123">
                                申请季：2024 Fall\n
                                学校：Stanford University\n
                                学位/学程：MS\n
                                专业：Computer Science\n
                                GPA：3.9/4.0\n
                                GRE/GMAT：330\n
                                TOEFL：110\n
                                背景：两段实习和一篇论文
                            </td>
                        </tr>
                    </table>
                </div>
            </div>
        </html>
        """
    )

    case = parse_application_data(thread_html, "https://example.com/thread-1", "Case A")
    assert isinstance(case, ApplicationCase)
    assert case.author == "applicant01"
    assert case.posted_at == "2024-03-01"
    assert case.application_term == "2024 Fall"
    assert case.school == "Stanford University"
    assert case.degree == "MS"
    assert case.major == "Computer Science"
    assert case.gpa == "3.9/4.0"
    assert case.gre == "330"
    assert case.toefl == "110"
    assert case.background.startswith("两段实习")
