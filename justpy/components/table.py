import justpy as jp
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        html = read_html('pagination.html')
        c = jp.parse_html(html)
        self.add_component(c)


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
