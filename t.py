import requests
import re


class SubTitleCralwer:

    def __init__(self, v: str):
        self.en_url = None
        self.zh_url = None
        self.url = f'https://www.youtube.com/watch?v={v}'
        self.en_subtitles = []
        self.zh_subtitles = []

    def init(self):
        self.get_api_urls()

    def get_api_urls(self):
        url = self.url
        r = requests.get(url)
        content = r.text
        api = re.findall(r'"(https://www.youtube.com/api/timedtext.+?)"', content)[-1]
        self.en_url = re.sub(r'\\u0026', '&', api)
        self.zh_url = self.en_url + '&tlang=zh-Hant'

    def get_list(self, content):
        content = re.sub(r'&amp;#39;', '\'', content)
        return re.findall(r'<.+?">(.+?)</text', content)

    def get_subtitle(self):
        r = requests.get(self.en_url)
        self.en_subtitles = self.get_list(r.text)

        r = requests.get(self.zh_url)
        self.zh_subtitles = self.get_list(r.text)


if __name__ == '__main__':
    cralwer = SubTitleCralwer('aoQ6S1a32j8')
    cralwer.init()
    cralwer.get_subtitle()
print()
