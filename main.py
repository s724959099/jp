import justpy as jp


def my_click(self, msg):
    self.text = 'I was clicked'


def event_demo():
    wp = jp.WebPage()
    d = jp.Div(text='Not clicked yet', a=wp, class_='w-48 text-xl m-2 p-1 bg-blue-500 text-white')
    d.add(jp.Div(text='yooo'))
    d.on('click', my_click)
    return wp


# jp.justpy(event_demo, websockets=False)
jp.justpy(event_demo)
