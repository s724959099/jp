import justpy as jp
import uvicorn


@jp.SetRoute('/')
def demo():
    wp = jp.WebPage()
    pagination = jp.Pagination()
    wp.add(pagination)
    return wp


app = jp.app

if __name__ == '__main__':
    uvicorn.run('pg1:app', debug=True)
