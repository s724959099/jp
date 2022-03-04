import jp
import uvicorn


@jp.SetRoute('/')
def demo():
    wp = jp.WebPage()
    return wp


app = jp.app

if __name__ == '__main__':
    jp.WebPage.use_websockets = False
    uvicorn.run('pg1:app', debug=True)
