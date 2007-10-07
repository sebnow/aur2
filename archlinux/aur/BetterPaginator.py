# BetterPaginator by spankalee
from django.core.paginator import ObjectPaginator, InvalidPage

class BetterPaginator(ObjectPaginator):
    def __init__(self, query_set, page_size, link_template, total='?'):
        self.current_page = 1
        self.page_size = page_size
        self.link_template = link_template
        self.total = total
        ObjectPaginator.__init__(self, query_set, page_size)

    def set_page(self, page_num):
        self.current_page = int(page_num)

    def has_next_page(self, page_num=None):
        if page_num is None:
            return ObjectPaginator.has_next_page(self, self.current_page-1)
        else:
            return ObjectPaginator.has_next_page(self,page_num)

    def has_previous_page(self, page_num=None):
        if page_num is None:
            return ObjectPaginator.has_previous_page(self, self.current_page-1)
        else:
            return ObjectPaginator.has_previous_page(self,page_num)

    def get_page(self, page_num=None):
        if page_num is None:
            return ObjectPaginator.get_page(self, self.current_page-1)
        else:
            return ObjectPaginator.get_page(self, page_num)

    def previous_link(self):
        if ObjectPaginator.has_previous_page(self, self.current_page-1):
            return self.link_template % (self.current_page - 1)
        else:
            return None

    def next_link(self):
        if ObjectPaginator.has_next_page(self, self.current_page-1):
            return self.link_template % (self.current_page + 1)
        else:
            return None

    def start_index(self):
        return (self.current_page-1) * self.page_size + 1

    def end_index(self):
        return min(self.current_page * self.page_size, self.hits)

    def make_page_links (self, start, end):
        return [(p+1, self.link_template % (p+1), (p+1 == self.current_page)) for p in range(start, end)]

    def page_links(self):
        return self.make_page_links(0, self.pages)

    def windowed_page_links(self, window_size=10):
        links = []
        if self.pages <= 12:
            links = [self.page_links()]
        elif self.current_page - window_size/2 <= 3:
            links = [self.make_page_links(0, window_size), self.make_page_links(self.pages-2, self.pages)]
        elif self.current_page + window_size/2 > self.pages - 2:
            links = [self.make_page_links(0, 2), self.make_page_links(self.pages-window_size, self.pages)]
        else:
            links = [self.make_page_links(0, 2),
                             self.make_page_links(self.current_page-window_size/2-1, self.current_page+window_size/2-1),
                             self.make_page_links(self.pages-2, self.pages)]
        return links
