"""
Unit tests for Xiaohongshu HTML parser.
"""

from src.scrapers.xhs_parser import XhsParser


def test_parse_html_with_initial_state():
    parser = XhsParser()
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>愚园路宝藏 Cafe - 小红书</title>
        <meta property="og:title" content="愚园路宝藏 Cafe" />
    </head>
    <body>
        <script>
            window.__INITIAL_STATE__ = {
                "note": {
                    "noteDetailMap": {
                        "note123": {
                            "note": {
                                "title": "愚园路宝藏 BRUT CAFE",
                                "desc": "在静安区愚园路发现一家超棒的复古咖啡馆！#上海美食 #cafe",
                                "user": {"nickname": "小红书达人"},
                                "poi": {"name": "BRUT CAFE (愚园路店)"},
                                "tagList": [{"name": "上海美食"}, {"name": "cafe"}],
                                "imageList": [{"url": "https://img.xhs.com/demo.jpg"}]
                            }
                        }
                    }
                }
            };
        </script>
    </body>
    </html>
    """

    note = parser._extract_from_html(sample_html, "https://www.xiaohongshu.com/explore/note123", "note123")
    assert note.title == "愚园路宝藏 BRUT CAFE"
    assert note.author == "小红书达人"
    assert note.poi_name == "BRUT CAFE (愚园路店)"
    assert "上海美食" in note.tags
    assert len(note.image_urls) == 1


def test_parse_html_opengraph_fallback():
    parser = XhsParser()
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:title" content="武康大楼打卡攻略" />
        <meta property="og:description" content="徐汇区淮海中路1850号武康大楼超适合拍照！ #上海景点" />
        <meta property="og:image" content="https://img.xhs.com/wukang.jpg" />
    </head>
    <body></body>
    </html>
    """

    note = parser._extract_from_html(sample_html, "https://www.xiaohongshu.com/explore/note456", "note456")
    assert note.title == "武康大楼打卡攻略"
    assert "徐汇区" in note.desc
    assert note.image_urls == ["https://img.xhs.com/wukang.jpg"]
    assert "上海景点" in note.tags
