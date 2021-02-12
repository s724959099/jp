import jp
import uvicorn
import re
import random
import asyncio
from crawler import SubTitleCrawler


class Word(jp.Span):
    def __init__(self, **kwargs):
        kwargs['class_'] = 'text-green-500 text-5xl'
        super().__init__(**kwargs)


class WordInput(jp.InputChangeOnly):
    def __init__(self, length=1, **kwargs):
        kwargs['class_'] = 'outline-none bg-gray-300 text-green-500 text-5xl'
        kwargs['style'] = f'width: {length * 2}rem;'
        self.placeholder = kwargs.get('placeholder')
        super().__init__(**kwargs)

    async def temp_placeholder(self, text):
        self.placeholder = text


class Watchcard(jp.Div):
    def __init__(self, **kwargs):
        self.citem = None
        kwargs['class_'] = 'w-2/3 bg-white mt-20  rounded-lg shadow p-12'
        kwargs['style'] = 'min-height: 20rem;'
        super().__init__(**kwargs)
        input_ = WordInput(length=10)
        button = jp.Button(
            class_='text-5xl px-6 m-2 text-lg text-indigo-100 transition-colors duration-150 bg-indigo-700 rounded-lg focus:shadow-outline hover:bg-indigo-80',
            text='送出', click=self.click)
        self.add_component(input_)
        self.add_component(button)
        self.input = input_

    async def click(self, _):
        if self.input.value:
            self.page.watch = self.input.value
            crawler = SubTitleCrawler(self.input.value)
            crawler.init()
            item = self.page.name_dict['item']
            item.delete()
            card = Card(crawler=crawler)
            item.add_component(card)
            await card.build()


class Card(jp.Div):
    def __init__(self, crawler: SubTitleCrawler, **kwargs):
        self.answer = None
        self.en = None
        self.tw = None
        self.crawler = crawler
        self.total_count = len(self.crawler.en_subtitles)
        self.count_index = 0
        self.answer_list = []
        kwargs['class_'] = 'w-2/3 bg-white mt-20  rounded-lg shadow p-12'
        kwargs['style'] = 'min-height: 20rem;'
        super().__init__(**kwargs)

    def get_word(self, words):
        exclude = ['in', 'at', 'that', 'the', 'it', 'music', 'then', 'will',
                   'have', 'been', 'this', 'they', 'your', 'what', 'there',
                   'were', 'here',
                   'would', 'could', 'while', 'when', 'where']
        count = 0
        while True:
            count += 1
            ret = word = random.choice(words)
            word = word.lower()
            if count > len(words):
                return ret
            after_word_index = self.en.index(ret) + len(ret)
            if after_word_index < len(self.en) and self.en[after_word_index] == '\'':
                continue

            if len(word) >= 4 and word not in exclude and word not in self.answer_list:
                self.answer_list.append(word)
                return ret

    async def change(self, msg):
        if msg.value.lower() == self.answer.lower():
            await self.build()
        elif msg.value:
            msg.target.value = ''
            await self.make_sound()
            await msg.target.temp_placeholder(self.answer)

    async def make_sound(self):
        eval_text = f"""
            let utterance = new window.SpeechSynthesisUtterance("{self.en}");
            utterance.lang = 'en-US';
            window.speechSynthesis.speak(utterance)
            console.log("{self.en}")
            """
        await self.page.run_javascript(eval_text)

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
    wp = jp.justpy_parser_to_wp("""
    <div class="bg-red-200 h-screen">
        <div class="flex flex-col items-center" name="item">
        <WatchCard></WatchCard>
        </div>
      </div>
    """)

    return wp


app = jp.app

if __name__ == '__main__':
    uvicorn.run('main:app', debug=True)
