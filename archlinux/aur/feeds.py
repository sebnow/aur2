from django.contrib.syndication.feeds import Feed
from aur.models import Package
from django.utils.feedgenerator import Atom1Feed

class RssLatestPackages(Feed):
    title = "AUR Newest Packages"
    link = "/feeds/rss"
    description = "The latest and greatest packages in the AUR"

    # title_template = latest_title.html
    # description_template = latest_describtion.html

    author_name = 'Laszlo Papp'
    author_email = 'djszapi@archlinux.us'
    author_link = 'http://djszapi.homelinux.net/'
    # ttl = 600

    def item_pubdate(self, item):
        """
        Takes an item, as returned by items(), and returns the item's
        pubdate.
        """

    def items(self):
        return Package.objects.all()[:20]


class AtomLatestPackages(RssLatestPackages):
    feed_type = Atom1Feed
    subtitle = RssLatestPackages.description

