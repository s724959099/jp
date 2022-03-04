import jp
import uvicorn


@jp.SetRoute('/')
async def demo():
    wp = jp.WebPage()
    # await wp.run_javascript(f'console.log("yooo {wp.page_id}");')
    return wp


app = jp.app

if __name__ == '__main__':
    uvicorn.run('d7:app', debug=True)
