import justpy as jp


class MTh(jp.Div):
    html_tag = 'th'

    def __init__(self, **kwargs):
        self.attributes += ['scope']
        kwargs['class_'] = 'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'
        kwargs['scope'] = 'col'
        super().__init__(**kwargs)


class MTable(jp.Div):

    def __init__(self, **kwargs):
        self.class_ = 'flex flex-col'
        super().__init__(**kwargs)

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
                      <tbody class="bg-white divide-y divide-gray-200" nmae="tbody">
                      
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            """
        )
        self.c = c
        tr = c.name_dict['tr']
        tr.add(MTh(text='Name'))
        tr.add(MTh(text='Title'))
        tr.add(MTh(text='Status'))
        tr.add(MTh(text='Role'))
        self.add_component(c)

    def react(self):
        """
        <tr>
          <td class="px-6 py-4 whitespace-nowrap">
            <div class="flex items-center">
              <div class="flex-shrink-0 h-10 w-10">
                <img class="h-10 w-10 rounded-full" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?ixlib=rb-1.2.1&amp;ixid=eyJhcHBfaWQiOjEyMDd9&amp;auto=format&amp;fit=facearea&amp;facepad=4&amp;w=256&amp;h=256&amp;q=60" alt="">
              </div>
              <div class="ml-4">
                <div class="text-sm font-medium text-gray-900">
                  Jane Cooper
                </div>
                <div class="text-sm text-gray-500">
                  jane.cooper@example.com
                </div>
              </div>
            </div>
          </td>
          <td class="px-6 py-4 whitespace-nowrap">
            <div class="text-sm text-gray-900">Regional Paradigm Technician</div>
            <div class="text-sm text-gray-500">Optimization</div>
          </td>
          <td class="px-6 py-4 whitespace-nowrap">
            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
              Active
            </span>
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            Admin
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
            <a href="#" class="text-indigo-600 hover:text-indigo-900">Edit</a>
          </td>
        </tr>
        """
