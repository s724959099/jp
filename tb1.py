import justpy as jp
import uvicorn


@jp.SetRoute('/')
def demo():
    wp = jp.WebPage()
    table = jp.MTable(
        columns=['Song', 'Dance'],
        data=[(1, 2), ('yo', 'ok')]
    )
    wp.add(table)
    return wp


app = jp.app

if __name__ == '__main__':
    uvicorn.run('tb1:app', debug=True)
