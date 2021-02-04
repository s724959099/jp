import jp
import uvicorn
import re
import random
import asyncio


class Word(jp.Span):
    def __init__(self, **kwargs):
        kwargs['class_'] = 'text-green-500 text-5xl'
        super().__init__(**kwargs)


class WordInput(jp.InputChangeOnly):
    def __init__(self, length=1, **kwargs):
        kwargs['class_'] = 'outline-none bg-gray-300 text-green-500 text-5xl'
        kwargs['style'] = f'width: {length * 2}rem;'
        self.placeholder = kwargs.get('placeholder')
        self.wp = None
        super().__init__(**kwargs)

    async def wait_to_clear(self):
        await asyncio.sleep(3)
        self.placeholder = ''
        await self.wp.update()

    async def temp_placeholder(self, text):
        self.placeholder = text
        jp.run_task(self.wait_to_clear())


class WatchCard(jp.Div):
    def __init__(self, **kwargs):
        self.wp = None
        self.citem = None
        kwargs['class_'] = 'w-2/3 bg-white mt-20  rounded-lg shadow p-12'
        kwargs['style'] = 'min-height: 20rem;'
        super().__init__(**kwargs)
        input_ = WordInput(length=10)
        input_.wp = self.wp
        button = jp.Button(
            class_='text-5xl px-6 m-2 text-lg text-indigo-100 transition-colors duration-150 bg-indigo-700 rounded-lg focus:shadow-outline hover:bg-indigo-80',
            text='送出', click=self.click)
        self.add_component(input_)
        self.add_component(button)
        self.input = input_

    async def click(self, _):
        await self.input.temp_placeholder('demo')

    # async def click(self, _):
    #     if self.input.value:
    #         self.wp.watch = self.input.value
    #         crawler = SubTitleCrawler(self.input.value)
    #         crawler.init()
    #         self.citem.delete()
    #         card = Card(wp=self.wp, crawler=crawler)
    #         await card.build()
    #         self.citem.add_component(card)


class Card(jp.Div):
    def __init__(self, wp, crawler, **kwargs):
        self.wp = wp
        self.answer = None
        self.en = None
        self.tw = None
        self.crawler = crawler
        self.total_count = len(self.crawler.en_subtitles)
        self.count_index = 0
        kwargs['class_'] = 'w-2/3 bg-white mt-20  rounded-lg shadow p-12'
        kwargs['style'] = 'min-height: 20rem;'
        super().__init__(**kwargs)

    def get_word(self, words):
        count = 0
        while True:
            count += 1
            word = random.choice(words)
            if len(word) >= 2 or count > 3:
                return word

    async def change(self, msg):
        if msg.value.lower() == self.answer.lower():
            await self.build()
        elif msg.value:
            msg.target.value = ''
            await msg.target.temp_placeholder(self.answer)
            await self.make_sound()

    async def make_sound(self):
        eval_text = f"""
            let utterance = new window.SpeechSynthesisUtterance('{self.en}');
            utterance.lang = 'en-US';
            window.speechSynthesis.speak(utterance)
            """
        await self.wp.run_javascript(eval_text)

    async def build(self):
        self.delete_components()
        en = self.crawler.en_subtitles[self.count_index]
        tw = self.crawler.zh_subtitles[self.count_index]
        self.en = en
        self.tw = tw
        words = re.findall(r'\w+', en)
        word = self.get_word(words)
        self.answer = word
        st_index = en.index(word)
        ed_index = st_index + len(word)
        prefix_s = en[:st_index]
        suffix_s = en[ed_index:]
        self.add_component(Word(text=prefix_s))
        self.add_component(
            WordInput(length=len(word), change=self.change)
        )
        self.add_component(Word(text=suffix_s))
        self.add_component(jp.Div(class_='bg-gray-600 h-px my-6'))
        self.add_component(jp.Div(class_='text-blue-700', text=self.tw))

        self.count_index += 1
        print('prefix_s:', prefix_s)
        print('word:', word)
        print('suffix_s:', suffix_s)
        await self.make_sound()


@jp.SetRoute('/')
async def demo():
    wp = jp.WebPage()
    c = jp.parse_html("""
    <div class="bg-red-200 h-screen">
        <div class="flex flex-col items-center" name="item">
        </div>
      </div>
    """)
    citem = c.name_dict['item']
    watchcard = WatchCard(wp=wp, citem=citem)
    citem.add_component(watchcard)
    # card = Card(sentence='Tom works like a horse.')
    # citem.add_component(card)
    wp.add_component(c)

    return wp


app = jp.app

if __name__ == '__main__':
    uvicorn.run('d8:app', debug=True)
