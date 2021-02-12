import jp
import uvicorn


@jp.SetRoute('/')
async def demo():
    wp = jp.WebPage()
    c = jp.parse_html("""
    <div class="bg-red-200 h-screen">
        <div class="flex flex-col items-center" name="item">
        yoooo
        </div>
      </div>
    """)
    citem = c.name_dict['item']
    print()
    wp.add_component(c)

    return wp


app = jp.app

if __name__ == '__main__':
    uvicorn.run('d9:app', debug=True)
