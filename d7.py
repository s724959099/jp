import jp
import uvicorn


@jp.SetRoute('/')
async def demo():
    wp = jp.WebPage()
    pagination = jp.Pagination(10, 15)
    await wp.run_javascript(f'console.log("yooo {wp.page_id}");')
    wp.add(pagination)
    return wp


app = jp.app

if __name__ == '__main__':
    uvicorn.run('d7:app', debug=True)
