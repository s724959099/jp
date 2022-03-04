# todo remove startlette
import json
from contextlib import asynccontextmanager
from fastapi.responses import Response

import fnmatch
import os
import sys
import traceback
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.config import Config
from starlette.endpoints import HTTPEndpoint
from starlette.endpoints import WebSocketEndpoint
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse
from html.parser import HTMLParser
# todo remove
from .pandas import *
import re
from .routing import Route
from .htmlcomponents import HTMLBaseComponent

current_module = sys.modules[__name__]
current_dir = os.path.dirname(current_module.__file__)
print(current_dir.replace('\\', '/'))
print(f'Module directory: {current_dir}, Application directory: {os.getcwd()}')

config = Config('justpy.env')
DEBUG = config('DEBUG', cast=bool, default=True)

TEMPLATES_DIRECTORY = config('TEMPLATES_DIRECTORY', cast=str,
                             default=current_dir + '/templates')
STATIC_DIRECTORY = config('STATIC_DIRECTORY', cast=str, default=os.getcwd())
STATIC_ROUTE = config('STATIC_MOUNT', cast=str, default='/static')
STATIC_NAME = config('STATIC_NAME', cast=str, default='static')
TAILWIND = config('TAILWIND', cast=bool, default=True)

templates = Jinja2Templates(directory=TEMPLATES_DIRECTORY)

template_options = {
    'tailwind': TAILWIND,
    # static_name:
    'static_name': STATIC_NAME,
    # script file name list
}

app = FastAPI(debug=DEBUG)
app.mount(STATIC_ROUTE, StaticFiles(directory=STATIC_DIRECTORY),
          name=STATIC_NAME)
app.mount('/templates', StaticFiles(directory=current_dir + '/templates'),
          name='templates')
app.add_middleware(GZipMiddleware)


def initial_func(request):
    wp = WebPage()
    Div(text='JustPy says: Page not found',
        classes='inline-block text-5xl m-3 p-3 text-white bg-blue-600', a=wp)
    return wp


func_to_run = initial_func
startup_func = None


def server_error_func(request):
    wp = WebPage()
    Div(text='JustPy says: 500 - Server Error',
        classes='inline-block text-5xl m-3 p-3 text-white bg-red-600', a=wp)
    return wp


@app.on_event('startup')
async def justpy_startup():
    WebPage.loop = asyncio.get_event_loop()
    JustPy.loop = WebPage.loop
    if startup_func and callable(startup_func):
        if inspect.iscoroutinefunction(startup_func):
            await startup_func()
        else:
            startup_func()


@app.route("/{path:path}")
class AllPathRouter(HTTPEndpoint):
    """
    監聽所有的route
    """

    def _get_route_func_paramter_arg(self, route_target_func, paramter_arg):
        # get paramter count
        func_parameters = len(inspect.signature(route_target_func).parameters)
        assert func_parameters < 2, f"Function {route_target_func.__name__} cannot have more than one parameter"
        return () if not func_parameters else paramter_arg

    def _check_response(self, func_response_wp):
        # 確認 func response 是不是WebPage
        assert issubclass(type(func_response_wp),
                          WebPage), 'Function did not return a web page'
        assert \
            len(func_response_wp) > 0 or func_response_wp.html, \
            '\u001b[47;1m\033[93mWeb page is empty, add components\033[0m'

    async def _get_func_response_wp(self, route_func_arg, route_target_func):
        if inspect.iscoroutinefunction(route_target_func):
            func_response_wp = await route_target_func(*route_func_arg)
        else:
            func_response_wp = route_target_func(*route_func_arg)

        self._check_response(func_response_wp)
        return func_response_wp

    def _get_route_target_func(self, request):
        for route in Route.instances:
            func = route.matches(request['path'], request)
            if func:
                return func
        raise Exception(f'not found route: {request["path"]}')

    async def _get_context(self, func_response_wp, request):
        """
        reload_interval: None or sec reload by ajax
        body_style: 在#components 之外的body tag style
        body_classes: 在#components 之外的body tag class
        css: raw css string in style tag
        head_html: raw head tag string in head tag
        body_html: raw body html tag string before div#components
        display_url: set url in history state
        title: web site title
        redirect: redirct url
        debug: debug message
        events: page events
        """
        page_options = {'reload_interval': func_response_wp.reload_interval,
                        'body_style': func_response_wp.body_style,
                        'body_classes': func_response_wp.body_classes,
                        'css': func_response_wp.css,
                        'head_html': func_response_wp.head_html,
                        'body_html': func_response_wp.body_html,
                        'display_url': func_response_wp.display_url,
                        'title': func_response_wp.title,
                        'redirect': func_response_wp.redirect,
                        'debug': func_response_wp.debug,
                        'events': func_response_wp.events,
                        }
        # todo
        page_dict = func_response_wp.cache if func_response_wp.use_cache else func_response_wp.build_list()
        """
        template context
        request: for render template
        page_id: 給前後端知道 是哪一個WebPage
        justpy_dict: wp.build_list 是vue 的data，render 長dom 用 
            也會轉成child 的html_component.$props.jp_props，在長出更子層
        use_websockets: 如果不是使用websockets 就是使用ajax
        page_options:
        html: 如果html 有，就改使用html tag string
        """
        context = {
            'request': request,  # for template
            'page_id': func_response_wp.page_id,
            # 轉成json 是為了給前端再把它json.parse 一次
            'justpy_dict': json.dumps(page_dict, default=str),
            'use_websockets': json.dumps(WebPage.use_websockets),
            'template_options': template_options,
            'page_options': page_options,
        }
        return context

    async def get(self, request):
        """get router"""
        # 使用自己寫的Route 取得mapping 的 route & function
        if request['path'] == '/favicon.ico':
            return Response(status_code=404)
        route_target_func = self._get_route_target_func(request)

        # 確認func 參數 以及是否async
        route_func_arg = self._get_route_func_paramter_arg(route_target_func,
                                                           paramter_arg=(
                                                               request,))
        func_response_wp = await self._get_func_response_wp(route_func_arg,
                                                            route_target_func)

        context = await self._get_context(func_response_wp, request)
        # 轉成template resposne
        response = templates.TemplateResponse(func_response_wp.template_file,
                                              context)

        return response

    async def post(self, request):
        """post router"""
        # Handles post method. Used in Ajax mode for events when websockets disabled
        if request['path'] != '/zzz_justpy_ajax':
            return
        data_dict = await request.json()
        if data_dict['event_data']['event_type'] == 'beforeunload':
            return await self.on_disconnect(data_dict['event_data']['page_id'])

        msg_type = data_dict['type']
        page_event = msg_type == 'page_event'
        result = await handle_event(data_dict, com_type=1,
                                    page_event=page_event)
        if not result:
            return JSONResponse(False)
        return JSONResponse(result)

    @staticmethod
    async def on_disconnect(page_id):
        """disconnect remove"""
        logger.info(f'In disconnect AllPathRouter')
        if page_id in WebPage.instances:
            await WebPage.instances[
                page_id].on_disconnect()  # Run the specific page disconnect function
        return JSONResponse(False)


@app.websocket_route("/")
class JustpyEvents(WebSocketEndpoint):

    async def on_connect(self, websocket):
        # todo 其實不用這邊給websocket
        """
        在connect 的時候傳送websocket_id 讓前端知道現在是哪一個websocket 並且在讓前端船page_ready 將page_id 與websocket 綁在一起
        """
        await websocket.accept()

    # noinspection PyUnresolvedReferences
    async def on_receive(self, websocket, data):
        """
        Method to accept and act on data received from websocket
        """
        websocket_id = id(websocket)
        logger.debug(f'Socket {websocket_id} data received: {data}')
        data_dict = json.loads(data)
        event_type = data_dict['event_type']
        assert event_type in ['connect', 'event',
                              'page_event'], 'event type error'
        if event_type == 'connect':
            page_id = data_dict['page_id']
            await WebPage.init_websocket(page_id, websocket)
            return

        page_event = True if event_type == 'page_event' else False
        WebPage.loop.create_task(
            handle_event(data_dict, com_type=0, page_event=page_event))

    # noinspection PyUnresolvedReferences
    async def on_disconnect(self, websocket, close_code):
        websocket_id = id(websocket)
        page_id = WebPage.websocket_reverse_mapping.get(websocket_id)
        wp = WebPage.instances[page_id]
        await wp.on_disconnect()
        # delete it
        WebPage.websocket_reverse_mapping.pop(websocket_id)


@asynccontextmanager
async def handle_evnet_beofore_and_after(c, event_data):
    # execute on before
    try:
        await c.run_event_function('before', event_data, True)
    except Exception:
        pass
    yield
    # execute on after
    try:
        await c.run_event_function('after', event_data, True)
    except Exception:
        pass


async def handle_event(data_dict, com_type=0, page_event=False):
    # com_type 0: websocket, com_type 1: ajax
    CONNECTION_MAPPING = {0: 'websocket', 1: 'ajax'}
    build_list = None

    logger.info(
        f'In event handler: {CONNECTION_MAPPING[com_type]} {str(data_dict)}')
    event_data = data_dict['event_data']
    if event_data['page_id'] not in WebPage.instances:
        logger.warning('No page to load')
        return
    p = WebPage.instances[event_data['page_id']]

    event_data['page'] = p
    if event_data['event_type'] == 'page_update':
        build_list = p.build_list()
        return {'type': 'page_update', 'data': build_list}

    # get c
    if page_event:
        c = p
    else:
        c = HTMLBaseComponent.instances[event_data['id']]
        event_data['target'] = c

    async with handle_evnet_beofore_and_after(c, event_data):
        # execute on envet
        try:
            if hasattr(c, 'on_' + event_data['event_type']):
                event_result = await c.run_event_function(
                    event_data['event_type'], event_data, True)
            else:
                event_result = None
                logger.debug(
                    f'{c} has no {event_data["event_type"]} event handler')
            logger.debug(f'Event result: {event_result}')
        except Exception:
            # raise Exception(e)
            event_result = None
            logger.error(
                'Event result: \u001b[47;1m\033[93mError in event handler:\033[0m')
            logger.error(traceback.format_exc())

    # If page is not to be updated, the event_function should return anything but None

    if event_result is None:
        if com_type == 0:  # WebSockets communication
            await p.update()
        elif com_type == 1:  # Ajax communication
            build_list = p.build_list()

    if com_type == 1 and event_result is None:
        ajax_response = {'type': 'page_update', 'data': build_list,
                         'page_options': {'display_url': p.display_url,
                                          'title': p.title,
                                          'redirect': p.redirect,
                                          'open': p.open,
                                          }}
        return ajax_response


def justpy(func=None, *, websockets=True, host='127.0.0.1',
           port=5000, startup=None, **kwargs):
    """

    Args:
        func: 要執行的程式
        websockets: 是否使用websocket
        host: uvicorn.run(app, host=host, port=port, debug=True)
        port: uvicorn.run(app, host=host, port=port, debug=True)
        startup: startup function
        **kwargs:

    Returns:

    """
    global func_to_run, startup_func
    if func:
        func_to_run = func
    else:
        func_to_run = initial_func
    if startup:
        startup_func = startup
    if websockets:
        WebPage.use_websockets = True
    else:
        WebPage.use_websockets = False
    # 所有的router 都導入到 func_to_run
    Route("/{path:path}", func_to_run, last=True, name='default')
    for k, v in kwargs.items():
        template_options[k.lower()] = v

    uvicorn.run(app, host=host, port=port, debug=True)

    return func_to_run


def redirect(url):
    wp = WebPage()
    wp.add(Div())
    wp.redirect = url
    return wp


class BasicHTMLParser(HTMLParser):
    def error(self, message):
        pass

    # Void elements do not need closing tag
    void_elements = ['area', 'base', 'br', 'col', 'embed', 'hr', 'img',
                     'input', 'keygen', 'link', 'menuitem', 'meta',
                     'param', 'source', 'track', 'wbr']

    def __init__(self, target=None):
        super().__init__()
        self.target = target
        context = inspect.stack()[2][0]
        self.wp = WebPage()
        self.lasttag = None
        self.context = context
        self.start_tag = True
        self.components = []
        self.name_dict = Dict()  # After parsing holds a dict with named components
        # use name to get
        self.name_dict_attribute = 'name'
        self.root = Div(name='root')
        self.containers = []
        self.containers.append(self.root)

    def feed(self, data):
        if isinstance(data, str):
            data = data.strip()
        return super(BasicHTMLParser, self).feed(data)

    def val_transfer(self, val):
        if val in self.context.f_locals:
            ret = self.context.f_locals[val]
        elif val in self.context.f_globals:
            ret = self.context.f_globals[val]
        else:
            ret = val

        return ret

    def handle_starttag(self, tag, attrs):
        c = component_by_tag(tag, self.context, page=self.wp)
        # set id
        if not c.id:
            cls = HTMLBaseComponent
            c.id = cls.next_id
            cls.next_id += 1

        if c is None:
            logger.warning(f'No such tag({tag}), Div being used instead')
            c = Div()
        for attr in attrs:
            attr = list(attr)
            key, val = attr
            if val is None:
                val = True
            key = key.replace('_', '-')
            # class attr
            if key == 'class':
                key = 'class_'
            # Handle attributes that are also python reserved words
            if key in ['in', 'from']:
                key = '_' + key

            val_transfer = self.val_transfer(val)
            # on eventZ
            if key.startswith('@'):
                if hasattr(self.target, val_transfer):
                    val_transfer = getattr(self.target, val_transfer)
                c.on(key[1:], val_transfer)
                continue
            if key.startswith(':'):
                key = key[1:]
            if key == 'id':
                c.id = val
                continue

            setattr(c, key, val)
            # 如果 有self.name_dict_attribute 則加入到name_dict
            if key == self.name_dict_attribute:
                if val not in self.name_dict:
                    self.name_dict[val] = c
                else:
                    # 多個相同name 改成list
                    if not isinstance(self.name_dict[val], list):
                        self.name_dict[val] = [self.name_dict[val]]
                    self.name_dict[val].append(c)

        self.containers[-1].add_component(c)
        self.containers.append(c)

    def handle_endtag(self, tag):
        # todo containers 作用？
        self.containers.pop()

    def handle_data(self, data):
        pattern = re.compile(r'{{(.+?)}}')
        data = data.strip()
        match = pattern.match(data)
        if match:
            match_text = match.groups()[0]
            match_text = match_text.strip()
            if match_text.startswith('self.'):
                match_text = match_text.lstrip('self.')
                if not hasattr(self.target, match_text):
                    raise ValueError(f'not found {match_text}')
                attr = getattr(self.target, match_text)
                if callable(attr):
                    self.containers[-1].text = attr()
                else:
                    self.containers[-1].text = attr

        elif data:
            self.containers[-1].text = data
        return


def justpy_parser(html_string, **kwargs):
    parser = BasicHTMLParser(**kwargs)
    parser.feed(html_string)
    if len(parser.root.components) == 1:
        parser_result = parser.root.components[0]
    else:
        parser_result = parser.root
    parser_result.name_dict = parser.name_dict
    target = kwargs.get('target')
    if target:
        target.name_dict = parser.name_dict
    for c in parser_result.components:
        c.name_dict = parser.name_dict
    parser_result.initialize(**kwargs)
    return parser_result


def justpy_parser_to_wp(html_string, **kwargs):
    parser = BasicHTMLParser(**kwargs)
    parser.feed(html_string)
    if len(parser.root.components) == 1:
        parser_result = parser.root.components[0]
    else:
        parser_result = parser.root
    parser_result.name_dict = parser.name_dict
    parser_result.initialize(**kwargs)
    wp = parser.wp
    wp.add_component(parser_result)
    wp.name_dict = parser.name_dict
    return wp


def parse_html(html_string, **kwargs):
    return justpy_parser(html_string, **kwargs)
