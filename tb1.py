import justpy as jp
import uvicorn


@jp.SetRoute('/')
def demo():
    wp = jp.WebPage()
    table = jp.MTable()
    wp.add(table)
    return wp


app = jp.app

if __name__ == '__main__':
    uvicorn.run('tb1:app', debug=True)
