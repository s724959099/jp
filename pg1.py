import jp
import uvicorn


@jp.SetRoute('/')
def demo():
    wp = jp.WebPage()
    pagination = jp.Pagination(10, 15)
    wp.add(pagination)
    return wp


app = jp.app

if __name__ == '__main__':
    jp.WebPage.use_websockets = False
    uvicorn.run('pg1:app', debug=True)
