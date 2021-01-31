import justpy as jp
import typing


class MTh(jp.Div):
    html_tag = 'th'

    def __init__(self, **kwargs):
        self.attributes += ['scope']
        kwargs['class_'] = 'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'
        kwargs['scope'] = 'col'
        super().__init__(**kwargs)


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

        c = jp.parse_html(
            """
              <div class="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                <div class="py-2 align-middle inline-block min-w-full sm:px-6 lg:px-8">
                  <div class="shadow overflow-hidden border-b border-gray-200 sm:rounded-lg">
                    <table class="min-w-full divide-y divide-gray-200">
                      <thead class="bg-gray-50">
                        <tr name="tr">
                        </tr>
                      </thead>
                      <tbody class="bg-white divide-y divide-gray-200" name="tbody">
                      
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            """
        )
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
