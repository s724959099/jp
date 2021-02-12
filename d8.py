import jp
import uvicorn


class Card(jp.Div):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inner_html = """
        <div class="w-2/3 bg-white mt-20  rounded-lg shadow p-12" style="min-height: 20rem" name="card">
        <span class="text-green-500 text-5xl">Tom works like a
          <input class="outline-none bg-gray-300" type="text" style="width: 10rem">
          .</span>
        <div class="bg-gray-600 h-px my-6"></div>
        <div class="text-blue-700">
          Tom相當勤奮地工作。
        </div>
      </div>
        """


@jp.SetRoute('/')
async def demo():
    d = 3
    wp = jp.justpy_parser_to_wp("""
    <div class="bg-red-200 h-screen">
    <div class="flex flex-col items-center">
      <Card></Card>
    </div>
  </div>
    """)

    return wp


app = jp.app

if __name__ == '__main__':
    uvicorn.run('d8:app', debug=True)
