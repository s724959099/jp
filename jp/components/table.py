import jp
import typing
import os


def read_html(file_name):
    join_path = os.path.join(os.path.dirname(__file__), file_name)
    with open(join_path, 'r') as f:
        return f.read()


class MTh(jp.Div):
    html_tag = 'th'

    def __init__(self, **kwargs):
        self.attributes += ['scope']
        kwargs['class_'] = 'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'
        kwargs['scope'] = 'col'
        super().__init__(**kwargs)


class Pagination(jp.Div):
    def __init__(self, page_current: int = 1, page_count: int = 1, **kwargs):
        self.page_current = page_current
        self.page_count = page_count
        super().__init__(**kwargs)
        html = read_html('pagination.html')
        c = jp.parse_html(html)
        nav = c.name_dict['nav']
        self.nav = nav
        self.add_component(c)

    def page_list(self):
        page_current = self.page_current
        page_count = self.page_count
        # 小於10 全部都要
        if page_count <= 10:
            ret = [x for x in range(1, page_count + 1)]
            return ret
        prefix_index_list = [x for x in range(1, 3 + 1) if x <= page_count]
        suffix_index_list = [x for x in range(page_count - 3 + 1, page_count + 1) if x > 3]
        if page_current in prefix_index_list + suffix_index_list:
            middle_index_list = [None]
            if len(prefix_index_list) == 3 and page_current == prefix_index_list[-1]:
                middle_index_list.insert(0, page_current + 1)
            if len(suffix_index_list) == 3 and page_current == suffix_index_list[0]:
                middle_index_list.append(page_current - 1)
            ret = prefix_index_list + middle_index_list + suffix_index_list
            return ret
        middle_index_list = [page_current]
        if page_current - 1 not in prefix_index_list:
            middle_index_list.insert(0, page_current - 1)
            if page_current - 2 not in prefix_index_list:
                middle_index_list.insert(0, None)
        if page_current + 1 not in suffix_index_list:
            middle_index_list.append(page_current + 1)
            if page_current + 2 not in suffix_index_list:
                middle_index_list.append(None)
        ret = prefix_index_list + middle_index_list + suffix_index_list
        return ret

    def react(self):
        self.nav.delete_components()
        self.build_left_arrow()
        self.build_page_buttons()
        self.build_right_arrow()

    def build_page_buttons(self):
        page_list = self.page_list()

        def click_wrapper(page):
            def click(target, msg):
                self.page_current = page

            return click

        for page in page_list:
            class_ = 'relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium hover:bg-gray-50'
            if page is None:
                el = jp.Span(class_=class_, text='...')
                self.nav.add_component(el)
                continue

            if page != self.page_current:
                class_ += ' text-gray-500'

            el = jp.A(
                href='#',
                class_=class_,
                text=page,
                click=click_wrapper(page)
            )
            self.nav.add_component(el)

    def build_left_arrow(self):
        class_suffix = ''
        if self.page_current == 1:
            class_suffix += 'cursor-not-allowed'
        el = jp.parse_html(f"""
        <a href="#"
           class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 {class_suffix}">
          <!-- Heroicon name: chevron-left -->
          <svg name="left" class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"
               aria-hidden="true">
            <path fill-rule="evenodd"
                  d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
                  clip-rule="evenodd"/>
          </svg>
        </a>
        """)

        def click(target, msg):
            if self.page_current > 1:
                self.page_current -= 1

        el.on('click', click)
        self.nav.add_component(el)

    def build_right_arrow(self):
        class_suffix = ''
        if self.page_current == self.page_count:
            class_suffix += 'cursor-not-allowed'
        el = jp.parse_html(f"""
        <a href="#"
           class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 {class_suffix}">
          <!-- Heroicon name: chevron-right -->
          <svg name="right" class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"
               aria-hidden="true">
            <path fill-rule="evenodd"
                  d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                  clip-rule="evenodd"/>
          </svg>
        </a>
        """)

        def click(target, msg):
            if self.page_current < self.page_count:
                self.page_current += 1

        el.on('click', click)
        self.nav.add_component(el)


class MRow(jp.Tr):

    def __init__(self, data: typing.List = None, **kwargs):
        super().__init__(**kwargs)
        [self.add_component(
            jp.Td(class_="px-6 py-4 whitespace-nowrap", text=text)
        ) for text in data]


class MTable(jp.Div):

    def __init__(self, columns: typing.List = None, data: typing.List = None, **kwargs):
        self.class_ = 'flex flex-col'
        super().__init__(**kwargs)
        self.data = data

        html = read_html('table.html')
        c = jp.parse_html(html)
        self.c = c
        tr = c.name_dict['tr']
        [
            tr.add_component(MTh(text=col))
            for col in columns
        ]
        self.tr = tr
        tbody = c.name_dict['tbody']
        self.tbody = tbody
        self.add_component(c)

    def react(self):
        tbody = self.tbody
        tbody.delete_components()
        for row in self.data:
            tbody.add_component(MRow(data=row))
