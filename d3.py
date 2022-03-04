import jp

wp = jp.WebPage(data={'text': 'Initial text'})


async def click(self, msg):
    print('done')
    await wp.run_javascript('console.log("test");')


async def input_demo():
    input_classes = "m-2 bg-gray-200 appearance-none border-2 border-gray-200 rounded xtw-64 py-2 px-4 text-gray-700 focus:outline-none focus:bg-white focus:border-purple-500"
    jp.Input(a=wp, classes=input_classes, placeholder='Please type here',
             model=[wp, 'text'])
    jp.Div(model=[wp, 'text'],
           classes='m-2 p-2 h-32 text-xl border-2 overflow-auto', a=wp,
           click=click)
    return wp


jp.justpy(input_demo)
