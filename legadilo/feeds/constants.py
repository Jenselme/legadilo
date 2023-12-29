from django.db.models import TextChoices


class SupportedFeedType(TextChoices):
    rss090 = "rss090", "RSS 0.90"
    rss091n = "rss091n", "RSS 0.91 (Netscape)"
    rss091u = "rss091u", "RSS 0.91 (Userland)"
    rss092 = "rss092", "RSS 0.92"
    rss093 = "rss093", "RSS 0.93"
    rss094 = "rss094", "RSS 0.94"
    rss20 = "rss20", "RSS 2.0"
    rss10 = "rss10", "RSS 1.0"
    rss = "rss", "RSS (unknown version)"
    atom01 = "atom01", "Atom 0.1"
    atom02 = "atom02", "Atom 0.2"
    atom03 = "atom03", "Atom 0.3"
    atom10 = "atom10", "Atom 1.0"
    atom = "atom", "Atom (unknown version)"
    cdf = "cdf", "CDF"
