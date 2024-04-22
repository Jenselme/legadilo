from django.conf import settings

SAMPLE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta name="HandheldFriendly" content="True" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="robots" content="index, follow" />

  <link rel="stylesheet" type="text/css" href="//www.jujens.eu/theme/stylesheet/style.min.css">

    {{PLACEHOLDER}}

    <link rel="shortcut icon" href="/images/favicon.png" type="image/x-icon">
<meta property="og:description" content="Programming blog, mostly about Python and JS."/>
<meta property="og:locale" content="en_US"/>
<meta property="og:url" content="//www.jujens.eu"/>
<meta property="og:image" content="/images/profile.png">

</head>
<body class="light-theme">
    <p>Hello world!</p>
</body>
"""


SAMPLE_RSS_FEED = """
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
<channel>
<title>Sample Feed</title>
<description>For documentation &lt;em&gt;only&lt;/em&gt;</description>
<link>http://example.org/</link>
<pubDate>Sat, 07 Sep 2002 00:00:01 GMT</pubDate>
<!-- other elements omitted from this example -->
<item>
<title>First entry title</title>
<link>http://example.org/entry/3</link>
<description>Watch out for &lt;span style="background-image:
url(javascript:window.location='http://example.org/')"&gt;nasty
tricks&lt;/span&gt;</description>
<pubDate>Thu, 05 Sep 2002 00:00:01 GMT</pubDate>
<guid>http://example.org/entry/3</guid>
<!-- other elements omitted from this example -->
</item>
</channel>
</rss>
"""

SAMPLE_ATOM_FEED = """
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
xml:base="http://example.org/"
xml:lang="en">
<title type="text">Sample Feed</title>
<subtitle type="html">
For documentation &lt;em&gt;only&lt;/em&gt;
</subtitle>
<link rel="alternate" href="/"/>
<link rel="self"
type="application/atom+xml"
href="http://www.example.org/atom10.xml"/>
<rights type="html">
&lt;p>Copyright 2005, Mark Pilgrim&lt;/p>&lt;
</rights>
<id>tag:feedparser.org,2005-11-09:/docs/examples/atom10.xml</id>
<generator
uri="http://example.org/generator/"
version="4.0">
Sample Toolkit
</generator>
<updated>2005-11-09T11:56:34Z</updated>
<entry>
<title>First entry title</title>
<link rel="alternate"
href="/entry/3"/>
<link rel="related"
type="text/html"
href="http://search.example.com/"/>
<link rel="via"
type="text/html"
href="http://toby.example.com/examples/atom10"/>
<link rel="enclosure"
type="video/mpeg4"
href="http://www.example.com/movie.mp4"
length="42301"/>
<id>tag:feedparser.org,2005-11-09:/docs/examples/atom10.xml:3</id>
<published>2005-11-09T00:23:47Z</published>
<updated>2005-11-09T11:56:34Z</updated>
<summary type="text/plain" mode="escaped">Watch out for nasty tricks</summary>
<content type="application/xhtml+xml" mode="xml"
xml:base="http://example.org/entry/3" xml:lang="en-US">
<div xmlns="http://www.w3.org/1999/xhtml">Watch out for
<span style="background: url(javascript:window.location='http://example.org/')">
nasty tricks</span></div>
</content>
</entry>
</feed>
"""


def get_fixture_file_content(name: str):
    with open(settings.APPS_DIR / "feeds/tests/fixtures" / name) as f:
        return f.read()
