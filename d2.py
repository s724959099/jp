import jp


def click_out(self, msg):
    self.text = 'click out'
    self.set_classes('text-blue-500')


def click_in(self, msg):
    self.text = 'click in'
    self.set_classes('text-red-500')


def test_out():
    wp = jp.WebPage()
    for i in range(4):
        d = jp.Div(text=f'{i}) Div', a=wp, classes='m-4 p-4 text-xl border w-32')
        d2 = jp.Div(text=f'{i}) Div', classes='m-4 p-4 text-xl border w-32')
        d3 = jp.Div(text=f'{i}) Div', classes='m-4 p-4 text-xl border w-32',a=d2)
        d4 = jp.Div(text=f'{i}) Div', classes='m-4 p-4 text-xl border w-32')
        d3.add_component(d4)
        wp.add_component(d2)
        d.on('click__out', click_out)
        d.on('click', click_in)
    return wp


jp.justpy(test_out)
