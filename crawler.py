import requests
import re
from addict import Dict


class SubTitleCrawler:

    def __init__(self, v: str):
        self.en_url = None
        self.zh_url = None
        self.url = f'https://www.youtube.com/watch?v={v}'
        self.en_subtitles = []
        self.zh_subtitles = []

    def init(self):
        self.get_api_urls()
        self.get_subtitle()
        self.process_subtitle()

    def get_api_urls(self):
        url = self.url
        r = requests.get(url)
        content = r.text
        api = re.findall(r'"(https://www.youtube.com/api/timedtext.+?)"', content)[-1]
        base = re.sub(r'\\u0026', '&', api)
        self.en_url = base + '&tlang=en'
        self.zh_url = base + '&tlang=zh-Hant'

    def get_list(self, content):
        content = re.sub(r'&amp;#39;', '\'', content)
        pattern = re.compile('<text start="(.+?)" dur="(.+?)">(.+?)</text>')
        ret = []
        for match in pattern.finditer(content):
            start, duration, text = match.groups()
            ret.append(Dict(start=float(start), duration=float(duration), text=text))
        return ret

    def get_subtitle(self):
        r = requests.get(self.en_url)
        self.en_subtitles = self.get_list(r.text)

        r = requests.get(self.zh_url)
        self.zh_subtitles = self.get_list(r.text)

    def process_subtitle(self):
        en_list = []
        zh_list = []
        en_subtitles = self.en_subtitles[:]
        zh_subtitles = self.zh_subtitles[:]
        while len(en_subtitles) and len(zh_subtitles):
            en_dict = en_subtitles.pop(0)
            zh_dict = zh_subtitles.pop(0)
            while len(en_subtitles) and len(zh_subtitles):
                next_en_dict = en_subtitles[0]
                next_zh_dict = zh_subtitles[0]
                if en_dict.start == zh_dict.start and next_en_dict.start == next_zh_dict.start:
                    en_list.append(en_dict.text)
                    zh_list.append(zh_dict.text)
                    break
                if next_en_dict.start < next_zh_dict.start:
                    en_dict.duration += next_en_dict.duration
                    en_dict.text += ' ' + next_en_dict.text
                    en_subtitles.pop(0)
                else:
                    zh_dict.duration += next_zh_dict.duration
                    zh_dict.text += ' ' + next_zh_dict.text
                    zh_subtitles.pop(0)

        self.en_subtitles = en_list
        self.zh_subtitles = zh_list


if __name__ == '__main__':
    v = 'wCGsLqHOT2I'
    crawler = SubTitleCrawler(v)
    crawler.init()
    for en, zh in zip(crawler.en_subtitles, crawler.zh_subtitles):
        print(en.text, zh.text)
    print()
