from types import MethodType
from addict import Dict
import asyncio
from .tailwind import Tailwind
import logging
import inspect
import re
from .util import try_save
import typing

# todo
tagfind_tolerant = re.compile(r'([a-zA-Z][^\t\n\r\f />\x00]*)(?:\s|/(?!>))*')
attrfind_tolerant = re.compile(
    r'((?<=[\'"\s/])[^\s/>][^\s/=>]*)(\s*=+\s*'
    r'(\'[^\']*\'|"[^"]*"|(?![\'"])[^>\s]*))?(?:\s|/(?!>))*')

# Dictionary for translating from tag to class
_tag_class_dict = {}


class JustPy:
    loop = None
    LOGGING_LEVEL = logging.DEBUG


class WebPage:
    # TODO: Add page events such as online, beforeunload, resize, visibilitychange
    loop = None
    instances = {}
    use_websockets = True
    delete_flag = True
    tailwind = True
    debug = False
    highcharts_theme = None
    websocket_reverse_mapping = {}  # websocket_id: page_id

    def __init__(self, **kwargs):
        self.run_javascripts = []
        # get websocket
        self.websocket = None
        self.cache = None  # Set this attribute if you want to use the cache.
        self.use_cache = False  # Determines whether the page uses the cache or not
        self.template_file = 'tailwind.html'
        self.title = 'JustPy'
        self.display_url = None
        self.redirect = None
        self.open = None
        self.favicon = None
        self.components = []  # list of direct children components on page
        self.cookies = {}
        self.css = ''
        # todo 什麼時候呢
        self.head_html = ''
        self.body_html = ''
        # If html attribute is not empty, sets html of page directly
        # todo 什麼時候有? raw html tag?
        self.html = ''
        # todo 什麼時候呢
        self.body_style = ''
        # todo 什麼時候呢
        self.body_classes = ''
        self.reload_interval = None
        self.events = []
        self.data = {}
        WebPage.instances[self.page_id] = self
        for k, v in kwargs.items():
            self.__setattr__(k, v)

    @property
    def page_id(self):
        return id(self)

    def __repr__(self):
        return f'{self.__class__.__name__}(page_id: {self.page_id}, number of components: {len(self.components)}, reload interval: {self.reload_interval})'

    @staticmethod
    async def init_websocket(page_id, websocket):
        websocket_id = id(websocket)
        wp = WebPage.instances.get(page_id)
        wp.websocket = websocket
        WebPage.websocket_reverse_mapping[websocket_id] = page_id

        if wp and wp.run_javascripts:
            while len(wp.run_javascripts):
                (javascript_string, request_id, send) = wp.run_javascripts.pop(0)
                await wp.run_javascript(javascript_string=javascript_string, request_id=request_id, send=send)

    def __len__(self):
        return len(self.components)

    def add_component(self, child, position=None):
        if position is None:
            self.components.append(child)
        else:
            self.components.insert(position, child)
        child.add_page(self)
        return self

    def add_components(self, children: list):
        for child in children:
            self.add_component(child)

    async def on_disconnect(self):
        if self.delete_flag:
            self.delete_components()
            self.remove_page()

    def remove_page(self):
        WebPage.instances.pop(self.page_id)

    def delete_components(self):
        for c in self.components:
            c.delete()
        self.components = []

    def add(self, *args):
        for component in args:
            self.add_component(component)
        return self

    def __add__(self, other):
        self.add_component(other)
        return self

    def __iadd__(self, other):
        self.add_component(other)
        return self

    def remove_component(self, component):
        try:
            self.components.remove(component)
        except Exception:
            raise Exception('Component cannot be removed because it was not in Webpage')
        return self

    def remove(self, component):
        self.remove_component(component)

    def get_components(self):
        return self.components

    def last(self):
        return self.components[-1]

    def set_cookie(self, k, v):
        self.cookies[str(k)] = str(v)

    def delete_cookie(self, k):
        if k in self.cookies:
            del (self.cookies[str(k)])

    async def run_javascript(self, javascript_string, *, request_id=None, send=True):
        websocket = self.websocket
        if not websocket:
            self.run_javascripts.append(
                (javascript_string, request_id, send)
            )

        dict_to_send = {'event_type': 'run_javascript', 'data': javascript_string, 'request_id': request_id,
                        'send': send}
        WebPage.loop.create_task(websocket.send_json(dict_to_send))
        return self

    async def reload(self):
        return await self.run_javascript('location.reload()')

    async def update_old(self, *, built_list=None):
        websocket = self.websocket
        if not built_list:
            component_build = self.build_list()
        else:
            component_build = built_list
        WebPage.loop.create_task(websocket.send_json({'event_type': 'page_update', 'data': component_build,
                                                      'page_options': {'display_url': self.display_url,
                                                                       'title': self.title,
                                                                       'redirect': self.redirect,
                                                                       'open': self.open,
                                                                       'favicon': self.favicon}}))
        return self

    async def update(self, websocket=None):
        websocket = websocket or self.websocket
        page_build = self.build_list()
        dict_to_send = {'event_type': 'page_update', 'data': page_build,
                        'page_options': {'display_url': self.display_url,
                                         'title': self.title,
                                         'redirect': self.redirect, 'open': self.open,
                                         'favicon': self.favicon}}

        WebPage.loop.create_task(websocket.send_json(dict_to_send))
        return self

    async def delayed_update(self, delay):
        await asyncio.sleep(delay)
        return await self.update()

    def to_html(self, indent=0, indent_step=0, format_=True):
        block_indent = ' ' * indent
        if format_:
            ws = '\n'
        else:
            ws = ''
        s = f'{block_indent}<div>{ws}'
        for c in self.components:
            s = f'{s}{c.to_html(indent + indent_step, indent_step, format_)}'
        s = f'{s}{block_indent}</div>{ws}'
        return s

    def react(self):
        pass

    def build_list(self):
        object_list = []
        self.react()
        for i, obj in enumerate(self.components):
            obj.react()
            d = obj.convert_object_to_dict()
            object_list.append(d)
        return object_list

    async def run_event_function(self, event_type, event_data, create_namespace_flag=True):
        event_function = getattr(self, 'on_' + event_type)
        if create_namespace_flag:
            function_data = Dict(event_data)
        else:
            function_data = event_data
        if inspect.iscoroutinefunction(event_function):
            event_result = await event_function(function_data)
        else:
            event_result = event_function(function_data)
        return event_result


# todo
class TailwindUIPage(WebPage):
    # https://tailwindui.com/components

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.template_file = 'tailwindui.html'


class HTMLBaseComponent(Tailwind):
    """
    Base Component for all HTML components
    """
    next_id = 1
    html_render = ''
    # for singletone id: instance
    instances = {}
    temp_flag = True
    delete_flag = True
    needs_deletion = False

    attributes = []
    html_tag = 'div'
    vue_type = 'html_component'  # Vue.js component name

    html_global_attributes = ['accesskey', 'class', 'contenteditable', 'dir', 'draggable', 'dropzone', 'hidden', 'id',
                              'lang', 'spellcheck', 'style', 'tabindex', 'title']

    # 客製化的 attr，給js & python ex: vue_type, html_tag
    attribute_list = ['id', 'vue_type', 'show', 'events', 'event_modifiers', 'class_', 'style', 'set_focus',
                      'html_tag', 'class_name', 'event_propagation', 'inner_html', 'animation', 'debug', 'transition']

    # not_used_global_attributes = ['dropzone', 'translate', 'autocapitalize',
    #                               'itemid', 'itemprop', 'itemref', 'itemscope', 'itemtype']

    # Additions to global attributes to add to attrs dict apart from id and style.
    used_global_attributes = ['contenteditable', 'dir', 'tabindex', 'title', 'accesskey', 'draggable', 'lang',
                              'spellcheck']

    def __init__(self, **kwargs):
        super().__init__()
        self.name_dict = Dict()
        self.components = []
        # 每new 一個 self.id 就會增加一個 用在on evnet 等等功能上
        cls = HTMLBaseComponent
        temp = kwargs.get('temp', cls.temp_flag)
        delete_flag = kwargs.get('delete_flag', cls.delete_flag)
        if temp and delete_flag:
            self.id = None
        else:
            self.id = cls.next_id
            cls.next_id += 1

        self.events = []
        self.event_modifiers = Dict()
        self.transition = None
        self.page = None
        self.pages = {}  # Dictionary of pages the component is on. Not managed by framework.
        # self.model = []

        self.class_name = type(self).__name__
        self.debug = False
        self.inner_html = ''
        self.animation = False
        self.show = True
        self.set_focus = False
        self.class_ = ''
        self.slot = None
        # todo
        self.scoped_slots = {}  # For Quasar and other Vue.js based components
        self.style = ''
        self.directives = []
        self.data = {}
        self.drag_options = None
        self.allowed_events = ['click', 'mouseover', 'mouseout', 'mouseenter', 'mouseleave', 'input', 'change',
                               'after', 'before', 'keydown', 'keyup', 'keypress', 'focus', 'blur', 'submit',
                               'dragstart', 'dragover', 'drop', 'click__out']
        self.events = []
        self.event_modifiers = Dict()
        self.additional_properties = []  # Additional fields to get from the JavasScript event object
        self.event_propagation = True  # If True events are propagated
        # todo
        self.prop_list = []  # For components from libraries like quasar

        self.initialize(**kwargs)

    def __new__(cls, *args, **kwargs):
        from .justpy import justpy_parser
        if cls.html_render:
            return justpy_parser(cls.html_render, target=cls)
        return super(HTMLBaseComponent, cls).__new__(cls)

    def __len__(self):
        if hasattr(self, 'components'):
            return len(self.components)
        else:
            return 0

    def __repr__(self):
        name = self.name if hasattr(self, 'name') else 'No name'
        return f'{self.__class__.__name__}(id: {self.id}, html_tag: {self.html_tag}, vue_type: {self.vue_type}, name: {name}, number of components: {len(self)})'

    @staticmethod
    def convert_dict_to_object(d):
        obj = globals()[d['class_name']]()
        for obj_prop in d['object_props']:
            obj.add(HTMLBaseComponent.convert_dict_to_object(obj_prop))
        for k, v in d.items():
            obj.__dict__[k] = v
        for k, v in d['attrs'].items():
            obj.__dict__[k] = v
        return obj

    def add_to_page(self, wp: WebPage):
        wp.add_component(self)

    def add_to(self, *args):
        for c in args:
            c.add_component(self)

    def add_attribute(self, attr, value):
        self.attrs[attr] = value

    def add_event(self, event_type):
        if event_type not in self.allowed_events:
            self.allowed_events.append(event_type)

    def add_allowed_event(self, event_type):
        self.add_event(event_type)

    def add_scoped_slot(self, slot, c):
        self.scoped_slots[slot] = c

    def to_html(self, indent=0, indent_step=0, format_=True):
        block_indent = ' ' * indent
        if format_:
            ws = '\n'
        else:
            ws = ''
        s = f'{block_indent}<{self.html_tag} '
        d = self.convert_object_to_dict()
        for attr, value in d['attrs'].items():
            if value:
                s = f'{s}{attr}="{value}" '
        if self.class_:
            s = f'{s}class="{self.class_}"/>{ws}'
        else:
            s = f'{s}/>{ws}'
        return s

    def react(self):
        return

    def convert_object_to_dict(self) -> dict:
        # todo
        d = {
            'attrs': {},
            'scoped_slots': {},
            'directives': {},
            'additional_properties': self.additional_properties,
            'drag_options': self.drag_options

        }
        # Name is a special case. Allow it to be defined for all
        with try_save():
            d['attrs']['name'] = self.name
        # Add id if CSS transition is defined
        if self.transition:
            self.check_transition()
        if self.id:
            d['attrs'] = {'id': str(self.id)}

        for attr in HTMLBaseComponent.attribute_list:
            d[attr] = getattr(self, attr)

        # set directives
        for i in self.directives:
            if i[0:2] == 'v-':  # It is a directive
                with try_save():
                    d['directives'][i[2:]] = getattr(self, i.replace('-', '_'))
        # attrs
        for i in self.prop_list + self.attributes + HTMLBaseComponent.used_global_attributes:
            with try_save():
                d['attrs'][i] = getattr(self, i)
                if i in ['in', 'from']:  # Attributes that are also python reserved words
                    d['attrs'][i] = getattr(self, '_' + i)
                if '-' in i:
                    s = i.replace('-', '_')  # kebab case to snake case
                    d['attrs'][i] = getattr(self, s)

        # scoped_slots
        for s in self.scoped_slots:
            d['scoped_slots'][s] = self.scoped_slots[s].convert_object_to_dict()
        return d

    def initialize(self, **kwargs):
        # for subclass __init__
        self.init_id_and_instance()

        # setattr
        for k, v in kwargs.items():
            self.__setattr__(k, v)
        # add to component
        keys = kwargs.keys()
        for com in ['a', 'add_to']:
            if com in keys:
                kwargs[com].add_component(self)

        self.set_keyword_events(**kwargs)

    def init_id_and_instance(self):
        cls = HTMLBaseComponent
        if not self.id:
            self.id = cls.next_id
            cls.next_id += 1
        cls.instances[self.id] = self

    def set_keyword_events(self, **kwargs):
        # for subclass __init__
        keys = kwargs.keys()
        for e in self.allowed_events:
            for prefix in ['', 'on', 'on_']:
                if prefix + e in keys:
                    fn = kwargs[prefix + e]
                    if isinstance(fn, str):
                        fn_string = f'def oneliner{self.id}(self, msg):\n {fn}'
                        exec(fn_string)
                        self.on(e, locals()[f'oneliner{self.id}'])
                    else:
                        self.on(e, fn)
                    break

    def delete(self):
        if self.needs_deletion:
            if self.delete_flag:
                HTMLBaseComponent.instances.pop(self.id)
                self.needs_deletion = False

    def on(self, event_type, func, debounce=None, throttle=None, immediate=False):
        if event_type not in self.allowed_events:
            raise Exception(f'No event of type {event_type} supported')

        # todo
        self.needs_deletion = True
        if inspect.ismethod(func):
            setattr(self, 'on_' + event_type, func)
        else:
            setattr(self, 'on_' + event_type, MethodType(func, self))
        if event_type not in self.events:
            self.events.append(event_type)
        if debounce:
            self.event_modifiers[event_type].debounce = {'value': debounce, 'timeout': None, 'immediate': immediate}
        elif throttle:
            self.event_modifiers[event_type].throttle = {'value': throttle, 'timeout': None}

    def remove_event(self, event_type):
        if event_type in self.events:
            self.events.remove(event_type)

    def has_event_function(self, event_type):
        if getattr(self, 'on_' + event_type, None):
            return True
        else:
            return False

    def has_class(self, class_name):
        return class_name in self.class_.split()

    def remove_class(self, tw_class):
        class_list = self.class_.split()
        try:
            class_list.remove(tw_class)
        except Exception:
            pass
        self.class_ = ' '.join(class_list)

    def hidden(self, flag=True):
        if flag:
            self.set_class('hidden')
        else:
            self.remove_class('hidden')

    def hidden_toggle(self):
        if self.has_class('hidden'):
            self.remove_class('hidden')
        else:
            self.set_class('hidden')

    def check_transition(self):
        if self.transition and (not self.id):
            cls = HTMLBaseComponent
            self.id = cls.next_id
            cls.next_id += 1

    def remove_page_from_pages(self, wp: WebPage):
        self.pages.pop(wp.page_id)

    def add_page(self, wp: WebPage):
        self.page = wp
        self.pages[wp.page_id] = wp
        for child in self.components:
            child.add_page(wp)

    def add_page_to_pages(self, wp: WebPage):
        self.pages[wp.page_id] = wp

    def set_model(self, value):
        if hasattr(self, 'model') and len(self.model):
            if len(self.model) == 2:
                self.model[0].data[self.model[1]] = value
            else:
                self.model[0][self.model[1]] = value

    def get_model(self):
        if len(self.model) == 2:
            model_value = self.model[0].data[self.model[1]]
        else:
            model_value = self.model[0][self.model[1]]
        return model_value

    async def run_event_function(self, event_type, event_data, create_namespace_flag=True):
        event_function = getattr(self, 'on_' + event_type)
        if create_namespace_flag:
            function_data = Dict(event_data)
        else:
            function_data = event_data
        if inspect.iscoroutinefunction(event_function):
            event_result = await event_function(function_data)
        else:
            event_result = event_function(function_data)
        return event_result


class Div(HTMLBaseComponent):
    # A general purpose container
    # This is a component that other components can be added to

    html_tag = 'div'

    def __init__(self, **kwargs):
        self.html_entity = False
        self.children = []
        super().__init__(**kwargs)
        self.components = self.children.copy()

    def delete(self):
        if self.delete_flag:
            for c in self.components:
                c.delete()
            if self.needs_deletion:
                HTMLBaseComponent.instances.pop(self.id)
            self.components = []

    def __getitem__(self, index):
        return self.components[index]

    def add_component(self, child: typing.Any, position=None, slot=None):
        if slot:
            child.slot = slot
        child.page = self.page
        child.pages = self.pages
        if position is None:
            self.components.append(child)
        else:
            self.components.insert(position, child)
        return self

    def add_components(self, children: list):
        for child in children:
            self.add_component(child)

    def delete_components(self):
        for c in self.components:
            c.delete()
        self.components = []

    def add(self, *args):
        for component in args:
            self.add_component(component)
        return self

    def __add__(self, child):
        self.add_component(child)
        return self

    def __iadd__(self, child):
        self.add_component(child)
        return self

    def add_first(self, child):
        self.add_component(child, 0)

    def remove_component(self, component):
        try:
            self.components.remove(component)
        except Exception:
            raise Exception('Component cannot be removed because it is not contained in element')
        return self

    def remove(self, component):
        self.remove_component(component)

    def get_components(self):
        return self.components

    def first(self):
        return self.components[0]

    def last(self):
        return self.components[-1]

    def to_html(self, indent=0, indent_step=0, format_=True):
        block_indent = ' ' * indent
        if format_:
            ws = '\n'
        else:
            ws = ''
        s = f'{block_indent}<{self.html_tag} '
        d = self.convert_object_to_dict()
        for attr, value in d['attrs'].items():
            if value:
                s = f'{s}{attr}="{value}" '
        if self.style:
            s = f'{s}style="{self.style}"'
        if self.class_:
            s = f'{s}class="{self.class_}">{ws}'
        else:
            s = f'{s}>{ws}'
        if self.inner_html:
            s = f'{s}{self.inner_html}</{self.html_tag}>{ws}'
            return s
        try:
            s = f'{s}{self.text}{ws}'
        except Exception:
            pass
        for c in self.components:
            s = f'{s}{c.to_html(indent + indent_step, indent_step, format_)}'
        s = f'{s}{block_indent}</{self.html_tag}>{ws}'
        return s

    def model_update(self):
        # [wp, 'text'] for example
        # self.text = str(self.model[0].data[self.model[1]])
        self.text = self.get_model()

    def build_list(self):
        object_list = []
        for i, obj in enumerate(self.components):
            obj.react()
            d = obj.convert_object_to_dict()
            object_list.append(d)
        return object_list

    def convert_object_to_dict(self) -> dict:
        d = super().convert_object_to_dict()
        if hasattr(self, 'model'):
            self.model_update()
        d['object_props'] = self.build_list()
        if hasattr(self, 'text'):
            self.text = str(self.text)
            d['text'] = self.text
            # Handle HTML entities. Warning: They should be in their own span or div. Setting inner_html overrides all else in container
            if self.html_entity:
                d['inner_html'] = self.text
        return d


class Input(Div):
    # Edge and Internet explorer do not support the input event for checkboxes and radio buttons. Use change instead
    # IMPORTANT: Scope of name of radio buttons is the whole page and not the form unless form is specified

    html_tag = 'input'
    attributes = ['accept', 'alt', 'autocomplete', 'autofocus', 'checked', 'dirname', 'disabled', 'form',
                  'formaction', 'formenctype', 'formmethod', 'formnovalidate', 'formtarget', 'height', 'list',
                  'max', 'maxlength', 'min', 'minlength', 'multiple', 'name', 'pattern', 'placeholder', 'readonly',
                  'required', 'size', 'src', 'step', 'type', 'value', 'width']

    def __init__(self, **kwargs):

        self.value = ''
        self.checked = False
        self.debounce = 200  # 200 millisecond default debounce for events
        self.no_events = False
        # Types for input element:
        # ['button', 'checkbox', 'color', 'date', 'datetime-local', 'email', 'file', 'hidden', 'image',
        # 'month', 'number', 'password', 'radio', 'range', 'reset', 'search', 'submit', 'tel', 'text', 'time', 'url', 'week']
        self.type = 'text'
        self.form = None
        super().__init__(**kwargs)

        def default_input(self, msg):
            return self.before_event_handler(msg)

        if not self.no_events:
            self.on('before', default_input)

    def __repr__(self):
        num_components = len(self.components)
        return f'{self.__class__.__name__}(id: {self.id}, html_tag: {self.html_tag}, input_type: {self.type}, vue_type: {self.vue_type}, value: {self.value}, checked: {self.checked}, number of components: {num_components})'

    def before_event_handler(self, msg):
        logging.debug('%s %s %s %s %s', 'before ', self.type, msg.event_type, msg.input_type, msg)
        if msg.event_type not in ['input', 'change', 'select']:
            return
        if msg.input_type == 'checkbox':
            # The checked field is boolean
            self.checked = msg.checked
            if hasattr(self, 'model'):
                self.model[0].data[self.model[1]] = msg.checked
        elif msg.input_type == 'radio':
            # If a radio field, all other radio buttons with same name need to have value changed
            # If form is specified, the scope is that form. If not, it is the whole page
            self.checked = True
            if self.form:
                Input.radio_button_set(self, self.form)
            else:
                Input.radio_button_set(self, msg.page)
            if hasattr(self, 'model'):
                self.model[0].data[self.model[1]] = msg.value
            self.value = msg.value
        else:
            if msg.input_type == 'number':
                try:
                    msg.value = int(msg.value)
                except Exception:
                    msg.value = float(msg.value)
            if hasattr(self, 'model'):
                # self.model[0].data[self.model[1]] = msg.value
                self.set_model(msg.value)
            self.value = msg.value

    @staticmethod
    def radio_button_set(radio_button, container):
        # Set all radio buttons in container with same name as radio_button to unchecked
        if hasattr(container, 'components'):
            for c in container.components:
                if hasattr(c, 'name'):
                    if c.name == radio_button.name and not radio_button.id == c.id:
                        c.checked = False
                Input.radio_button_set(radio_button, c)

    @staticmethod
    def radio_button_set_model_update(radio_button, container, model_value):
        for c in container.components:
            if hasattr(c, 'name'):
                if c.name == radio_button.name:
                    if c.value == model_value:
                        c.checked = True
                    else:
                        c.checked = False
            Input.radio_button_set_model_update(radio_button, c, model_value)

    def model_update(self):
        # update_value = self.model[0].data[self.model[1]]
        update_value = self.get_model()
        if self.type == 'checkbox':
            self.checked = update_value
        elif self.type == 'radio':
            model_value = update_value
            if self.form:
                Input.radio_button_set_model_update(self, self.form, model_value)
            else:
                Input.radio_button_set_model_update(self, self.model[0], model_value)
        else:
            self.value = update_value

    def convert_object_to_dict(self) -> dict:
        d = super().convert_object_to_dict()
        d['debounce'] = self.debounce
        d['input_type'] = self.type  # Needed for vue component updated life hook and event handler
        if self.type in ['text', 'textarea']:
            d['value'] = str(self.value)
        else:
            d['value'] = self.value
        d['attrs']['value'] = self.value
        d['checked'] = self.checked
        if not self.no_events:
            if self.type in ['radio', 'checkbox', 'select'] or self.type == 'file':
                # Not all browsers create input event
                if 'change' not in self.events:
                    self.events.append('change')
            else:
                if 'input' not in self.events:
                    self.events.append('input')
        if self.checked:
            d['attrs']['checked'] = True
        else:
            d['attrs']['checked'] = False
        try:
            d['attrs']['form'] = self.form.id
        except Exception:
            pass

        return d


class InputChangeOnly(Input):
    """
    Does not generate the 'input' event. Generates the 'change' event. Leaves other events unchanged.
    Use if you don't need to look at each character typed. Saves interaction with the server
    The 'change' event docs:
    https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/change_event
    Salient: When the element loses focus after its value was changed, but not committed (e.g., after editing the value
    of <textarea> or <input type="text">) or when Enter is pressed.
    """

    def convert_object_to_dict(self) -> dict:
        d = super().convert_object_to_dict()
        d['events'].remove('input')
        if 'change' not in d['events']:
            d['events'].append('change')
        return d


class Form(Div):
    html_tag = 'form'
    attributes = ['accept-charset', 'action', 'autocomplete', 'enctype', 'method', 'name', 'novalidate', 'target']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        def default_submit(self, msg):
            print('Default form submit', msg.form_data)
            return True

        if not self.has_event_function('submit'):
            # If an event handler is not  assigned, the front end cannot stop the default page request that happens when a form is submitted
            self.on('submit', default_submit)


class Label(Div):
    html_tag = 'label'
    attributes = ['for', 'form']  # In JustPy these are components, not ids of component like in HTML

    def __init__(self, **kwargs):
        self.for_component = None
        super().__init__(**kwargs)

    def convert_object_to_dict(self) -> dict:
        d = super().convert_object_to_dict()
        try:
            d['attrs']['for'] = self.for_component.id
        except Exception:
            pass
        try:
            d['attrs']['form'] = self.form.id
        except Exception:
            pass
        return d


class Textarea(Input):
    html_tag = 'textarea'
    attributes = ['autofocus', 'cols', 'dirname', 'disabled', 'form', 'maxlength', 'name',
                  'placeholder', 'readonly', 'required', 'rows', 'wrap', 'value']

    def __init__(self, **kwargs):
        self.rows = '4'
        self.cols = '50'
        super().__init__(**kwargs)
        self.type = 'textarea'
        self.input_type = 'text'


class Select(Input):
    # Need to set value of select on creation, otherwise blank line will show on page update
    html_tag = 'select'
    attributes = ['autofocus', 'disabled', 'form', 'multiple', 'name', 'required', 'size']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.type = 'select'


class A(Div):
    html_tag = 'a'
    attributes = ['download', 'href', 'hreflang', 'media', 'ping', 'rel', 'target', 'type']

    def __init__(self, **kwargs):

        self.href = None
        self.bookmark = None  # The component on page to jump to or scroll to
        self.scroll_to = None
        self.title = ''
        self.rel = "noopener noreferrer"
        self.download = None  # If attribute is set, file is downloaded, only works html 5  https://www.w3schools.com/tags/att_a_download.asp
        self.target = '_self'  # _blank, _self, _parent, _top, framename
        # https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollIntoView
        self.scroll = False  # If True, scrolling is enabled
        self.scroll_option = 'smooth'  # One of "auto" or "smooth".
        self.block_option = 'start'  # One of "start", "center", "end", or "nearest". Defaults to "start".
        self.inline_option = 'nearest'  # One of "start", "center", "end", or "nearest". Defaults to "nearest".
        super().__init__(**kwargs)

        if not kwargs.get('click'):
            def default_click(self, msg):
                return True

            self.on('click', default_click)

    def convert_object_to_dict(self) -> dict:
        d = super().convert_object_to_dict()
        d['scroll'] = self.scroll
        d['scroll_option'] = self.scroll_option
        d['block_option'] = self.block_option
        d['inline_option'] = self.inline_option
        if self.bookmark is not None:
            self.href = '#' + str(self.bookmark.id)
            self.scroll_to = str(self.bookmark.id)
        if d['scroll']:
            d['scroll_to'] = self.scroll_to
        d['attrs']['href'] = self.href
        d['attrs']['target'] = self.target
        if self.download is not None:
            d['attrs']['download'] = self.download
        return d


Link = A  # The 'Link' name is more descriptive and can be used instead


class Icon(Div):

    def __init__(self, **kwargs):
        self.icon = 'dog'  # Default icon
        super().__init__(**kwargs)

    def convert_object_to_dict(self) -> dict:
        d = super().convert_object_to_dict()
        d['class_'] = self.class_ + ' fa fa-' + self.icon
        return d


class EditorMD(Textarea):
    # https://www.cssportal.com/style-input-range/   style an input range
    # Set the page's tailwind attribute to False for preview to work
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.debounce = 0
        self.input_type = 'textarea'
        self.vue_type = 'editorjp'
        self.html_tag = 'textarea'


class Space(Div):

    # Creates a span with hard spaces.

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.num = kwargs.get('num', 1)
        self.html_tag = 'span'
        self.inner_html = '&nbsp;' * self.num


# Non html components

class TabGroup(Div):
    """
    Displays a tab based on its value. Has a dict of tabs whose keys is the value. A tab is any JustPy component.

    format of dict: {'value1': {'tab': comp1, 'order': number}, 'value2': {'tab': comp2, 'order': number} ...}
    self.tabs - tab dict
    self.animation_next = 'slideInRight'    set animation for tab coming in
    self.animation_prev = 'slideOutLeft'    set animation for tab going out
    self.animation_speed = 'faster'  can be on of  '' | 'slow' | 'slower' | 'fast'  | 'faster'
    self.value  value of group and tab to display
    self.previous - previous tab, no need to change except to set to '' in order to display tab without animation which is default at first

    """

    wrapper_classes = ' '
    wrapper_style = 'display: flex; position: absolute; width: 100%; height: 100%;  align-items: center; justify-content: center; background-color: #fff;'

    def __init__(self, **kwargs):

        self.tabs = {}  # Dict with format 'value': {'tab': Div component, 'order': number} for each entry
        self.value = ''
        self.previous_value = ''
        # https://github.com/daneden/animate.css
        self.animation_next = 'slideInRight'
        self.animation_prev = 'slideOutLeft'
        self.animation_speed = 'faster'  # '' | 'slow' | 'slower' | 'fast'  | 'faster'

        self.wrapper_div_classes = None
        self.wrapper_div = None

        super().__init__(**kwargs)

    def __setattr__(self, key, value):
        if key == 'value':
            try:
                self.previous_value = self.value
            except Exception:
                pass
        self.__dict__[key] = value

    def model_update(self):
        self.value = self.model[0].data[self.model[1]]

    def convert_object_to_dict(self) -> dict:
        self.components = []
        self.wrapper_div_classes = self.animation_speed  # Component in this will be centered

        if self.previous_value:
            self.wrapper_div = Div(class_=self.wrapper_div_classes, animation=self.animation_next, temp=True,
                                   style=f'{self.__class__.wrapper_style} z-index: 50;', a=self)
            self.wrapper_div.add(self.tabs[self.value]['tab'])
            self.wrapper_div = Div(class_=self.wrapper_div_classes, animation=self.animation_prev, temp=True,
                                   style=f'{self.__class__.wrapper_style} z-index: 0;', a=self)
            self.wrapper_div.add(self.tabs[self.previous_value]['tab'])
        else:
            self.wrapper_div = Div(class_=self.wrapper_div_classes, temp=True, a=self,
                                   style=self.__class__.wrapper_style)
            self.wrapper_div.add(self.tabs[self.value]['tab'])

        self.style = ' position: relative; overflow: hidden; ' + self.style  # overflow: hidden;
        d = super().convert_object_to_dict()
        return d


# HTML tags for which corresponding classes will be created
_tag_create_list = ['address', 'article', 'aside', 'footer', 'header', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'main',
                    'nav', 'section',
                    'blockquote', 'dd', 'dl', 'dt', 'figcaption', 'figure', 'hr', 'li', 'ol', 'p', 'pre', 'ul',
                    'abbr', 'b', 'bdi', 'bdo', 'br', 'cite', 'code', 'data', 'dfn', 'em', 'i', 'kbd', 'mark', 'q', 'rb',
                    'rp', 'rt', 'rtc', 'ruby', 's', 'samp', 'small', 'span', 'strong', 'sub', 'sup', 'time', 'tt', 'u',
                    'var', 'wbr',
                    'area', 'audio', 'img', 'map', 'track', 'video',
                    'embed', 'iframe', 'object', 'param', 'picture', 'source',
                    'del', 'ins', 'title',
                    'caption', 'col', 'colgroup', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr',
                    'button', 'fieldset', 'legend', 'meter', 'optgroup', 'option', 'progress',  # datalist not supported
                    'details', 'summary', 'style'  # dialog not supported
                    ]

# Only tags that have non-gloabal  attributes that are supported by HTML 5 are in this dict
_attr_dict = {'a': ['download', 'href', 'hreflang', 'media', 'ping', 'rel', 'target', 'type'],
              'area': ['alt', 'coords', 'download', 'href', 'hreflang', 'media', 'rel', 'shape', 'target', 'type'],
              'audio': ['autoplay', 'controls', 'loop', 'muted', 'preload', 'src'], 'base': ['href', 'target'],
              'bdo': ['dir'], 'blockquote': ['cite'],
              'button': ['autofocus', 'disabled', 'form', 'formaction', 'formenctype', 'formmethod',
                         'formnovalidate', 'formtarget', 'name', 'type', 'value'], 'canvas': ['height', 'width'],
              'col': ['span'], 'colgroup': ['span'], 'data': ['value'], 'del': ['cite', 'datetime'],
              'details': ['open'], 'dialog': ['open'], 'embed': ['height', 'src', 'type', 'width'],
              'fieldset': ['disabled', 'form', 'name'],
              'form': ['accept-charset', 'action', 'autocomplete', 'enctype', 'method', 'name', 'novalidate',
                       'target'], 'html': ['xmlns'],
              'iframe': ['height', 'name', 'sandbox', 'src', 'srcdoc', 'width'],
              'img': ['alt', 'crossorigin', 'height', 'ismap', 'longdesc', 'sizes', 'src', 'srcset', 'usemap',
                      'width'],
              'input': ['accept', 'alt', 'autocomplete', 'autofocus', 'checked', 'dirname', 'disabled', 'form',
                        'formaction', 'formenctype', 'formmethod', 'formnovalidate', 'formtarget', 'height', 'list',
                        'max', 'maxlength', 'min', 'minlength', 'multiple', 'name', 'pattern', 'placeholder',
                        'readonly',
                        'required', 'size', 'src', 'step', 'type', 'value', 'width'], 'ins': ['cite', 'datetime'],
              'label': ['for', 'form'], 'li': ['value'],
              'link': ['crossorigin', 'href', 'hreflang', 'media', 'rel', 'sizes', 'type'], 'map': ['name'],
              'meta': ['charset', 'content', 'http-equiv', 'name'],
              'meter': ['form', 'high', 'low', 'max', 'min', 'optimum', 'value'],
              'object': ['data', 'form', 'height', 'name', 'type', 'usemap', 'width'],
              'ol': ['reversed', 'start', 'type'], 'optgroup': ['disabled', 'label'],
              'option': ['disabled', 'label', 'selected', 'value'], 'output': ['for', 'form', 'name'],
              'param': ['name', 'value'], 'progress': ['max', 'value'], 'q': ['cite'],
              'script': ['async', 'charset', 'defer', 'src', 'type'],
              'select': ['autofocus', 'disabled', 'form', 'multiple', 'name', 'required', 'size'],
              'source': ['src', 'srcset', 'media', 'sizes', 'type'], 'style': ['media', 'type'],
              'td': ['colspan', 'headers', 'rowspan'],
              'textarea': ['autofocus', 'cols', 'dirname', 'disabled', 'form', 'maxlength', 'name', 'placeholder',
                           'readonly', 'required', 'rows', 'wrap'],
              'th': ['abbr', 'colspan', 'headers', 'rowspan', 'scope', 'sorted'], 'time': ['datetime'],
              'track': ['default', 'kind', 'label', 'src', 'srclang'],
              'video': ['autoplay', 'controls', 'height', 'loop', 'muted', 'poster', 'preload', 'src', 'width']}


# Name definition for static syntax analysers
# Classes are defined dynamically right after, this is just to assist code editors


def creaet_html_class_factory(tag_captitalize_name):
    return type(tag_captitalize_name.capitalize(), (Div,),
                {'html_tag': tag_captitalize_name.lower(),
                 'attributes': _attr_dict.get(tag_captitalize_name.lower(), [])})


Address = creaet_html_class_factory('Address')
Article = creaet_html_class_factory('Article')
Aside = creaet_html_class_factory('Aside')
Footer = creaet_html_class_factory('Footer')
Header = creaet_html_class_factory('Header')
H1 = creaet_html_class_factory('H1')
H2 = creaet_html_class_factory('H2')
H3 = creaet_html_class_factory('H3')
H4 = creaet_html_class_factory('H4')
H5 = creaet_html_class_factory('H5')
H6 = creaet_html_class_factory('H6')
Main = creaet_html_class_factory('Main')
Nav = creaet_html_class_factory('Nav')
Section = creaet_html_class_factory('Section')
Blockquote = creaet_html_class_factory('Blockquote')
Dd = creaet_html_class_factory('Dd')
Dl = creaet_html_class_factory('Dl')
Dt = creaet_html_class_factory('Dt')
Figcaption = creaet_html_class_factory('Figcaption')
Figure = creaet_html_class_factory('Figure')
Hr = creaet_html_class_factory('Hr')
Li = creaet_html_class_factory('Li')
Ol = creaet_html_class_factory('Ol')
P = creaet_html_class_factory('P')
Pre = creaet_html_class_factory('Pre')
Ul = creaet_html_class_factory('Ul')
Abbr = creaet_html_class_factory('Abbr')
B = creaet_html_class_factory('B')
Bdi = creaet_html_class_factory('Bdi')
Bdo = creaet_html_class_factory('Bdo')
Br = creaet_html_class_factory('Br')
Cite = creaet_html_class_factory('Cite')
Code = creaet_html_class_factory('Code')
Data = creaet_html_class_factory('Data')
Dfn = creaet_html_class_factory('Dfn')
Em = creaet_html_class_factory('Em')
I = creaet_html_class_factory('I')
Kbd = creaet_html_class_factory('Kbd')
Mark = creaet_html_class_factory('Mark')
Q = creaet_html_class_factory('Q')
Rb = creaet_html_class_factory('Rb')
Rp = creaet_html_class_factory('Rp')
Rt = creaet_html_class_factory('Rt')
Rtc = creaet_html_class_factory('Rtc')
Ruby = creaet_html_class_factory('Ruby')
S = creaet_html_class_factory('S')
Samp = creaet_html_class_factory('Samp')
Small = creaet_html_class_factory('Small')
Span = creaet_html_class_factory('Span')
Strong = creaet_html_class_factory('Strong')
Sub = creaet_html_class_factory('Sub')
Sup = creaet_html_class_factory('Sup')
Time = creaet_html_class_factory('Time')
Tt = creaet_html_class_factory('Tt')
U = creaet_html_class_factory('U')
Var = creaet_html_class_factory('Var')
Wbr = creaet_html_class_factory('Wbr')
Area = creaet_html_class_factory('Area')
Audio = creaet_html_class_factory('Audio')
Img = creaet_html_class_factory('Img')
Map = creaet_html_class_factory('Map')
Track = creaet_html_class_factory('Track')
Video = creaet_html_class_factory('Video')
Embed = creaet_html_class_factory('Embed')
Iframe = creaet_html_class_factory('Iframe')
Object = creaet_html_class_factory('Object')
Param = creaet_html_class_factory('Param')
Picture = creaet_html_class_factory('Picture')
Source = creaet_html_class_factory('Source')
Del = creaet_html_class_factory('Del')
Ins = creaet_html_class_factory('Ins')
Caption = creaet_html_class_factory('Caption')
Col = creaet_html_class_factory('Col')
Colgroup = creaet_html_class_factory('Colgroup')
Table = creaet_html_class_factory('Table')
Tbody = creaet_html_class_factory('Tbody')
Td = creaet_html_class_factory('Td')
Tfoot = creaet_html_class_factory('Tfoot')
Th = creaet_html_class_factory('Th')
Thead = creaet_html_class_factory('Thead')
Tr = creaet_html_class_factory('Tr')
Button = creaet_html_class_factory('Button')
Fieldset = creaet_html_class_factory('Fieldset')
Legend = creaet_html_class_factory('Legend')
Meter = creaet_html_class_factory('Meter')
Optgroup = creaet_html_class_factory('Optgroup')
Option = creaet_html_class_factory('Option')
Progress = creaet_html_class_factory('Progress')
Details = creaet_html_class_factory('Details')
Summary = creaet_html_class_factory('Summary')

Animate = AnimateMotion = AnimateTransform = Circle = ClipPath = Defs = Desc = Discard = Ellipse = FeBlend = FeColorMatrix = FeComponentTransfer = FeComposite = FeConvolveMatrix = FeDiffuseLighting = FeDisplacementMap = FeDistantLight = FeDropShadow = FeFlood = FeFuncA = FeFuncB = FeFuncG = FeFuncR = FeGaussianBlur = FeImage = FeMerge = FeMergeNode = FeMorphology = FeOffset = FePointLight = FeSpecularLighting = FeSpotLight = FeTile = FeTurbulence = Filter = ForeignObject = G = Image = Line = LinearGradient = Marker = Mask = Metadata = Mpath = Path = Pattern = Polygon = Polyline = RadialGradient = Rect = Set = Stop = Svg = Switch = Symbol = Text = TextPath = Tspan = Use = View = None
# **********************************
# SVG components
# https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute

# in, in2, mode
svg_tags = ['a', 'animate', 'animateMotion', 'animateTransform', 'audio', 'canvas', 'circle', 'clipPath', 'defs',
            'desc', 'discard', 'ellipse', 'feBlend', 'feColorMatrix', 'feComponentTransfer', 'feComposite',
            'feConvolveMatrix', 'feDiffuseLighting', 'feDisplacementMap', 'feDistantLight', 'feDropShadow', 'feFlood',
            'feFuncA', 'feFuncB', 'feFuncG', 'feFuncR', 'feGaussianBlur', 'feImage', 'feMerge', 'feMergeNode',
            'feMorphology', 'feOffset', 'fePointLight', 'feSpecularLighting', 'feSpotLight', 'feTile', 'feTurbulence',
            'filter', 'foreignObject', 'g', 'iframe', 'image', 'line', 'linearGradient', 'marker', 'mask', 'metadata',
            'mpath', 'path', 'pattern', 'polygon', 'polyline', 'radialGradient', 'rect', 'script', 'set', 'stop',
            'style', 'svg', 'switch', 'symbol', 'text', 'textPath', 'title', 'tspan', 'unknown', 'use', 'video', 'view']

svg_tags_use = ['animate', 'animateMotion', 'animateTransform', 'circle', 'clipPath', 'defs',
                'desc', 'discard', 'ellipse', 'feBlend', 'feColorMatrix', 'feComponentTransfer', 'feComposite',
                'feConvolveMatrix', 'feDiffuseLighting', 'feDisplacementMap', 'feDistantLight', 'feDropShadow',
                'feFlood',
                'feFuncA', 'feFuncB', 'feFuncG', 'feFuncR', 'feGaussianBlur', 'feImage', 'feMerge', 'feMergeNode',
                'feMorphology', 'feOffset', 'fePointLight', 'feSpecularLighting', 'feSpotLight', 'feTile',
                'feTurbulence',
                'filter', 'foreignObject', 'g', 'image', 'line', 'linearGradient', 'marker', 'mask', 'metadata',
                'mpath', 'path', 'pattern', 'polygon', 'polyline', 'radialGradient', 'rect', 'set', 'stop',
                'svg', 'switch', 'symbol', 'text', 'textPath', 'tspan', 'use', 'view']

svg_presentation_attributes = ['alignment-baseline', 'baseline-shift', 'clip', 'clip-path', 'clip-rule', 'color',
                               'color-interpolation', 'color-interpolation-filters', 'color-profile', 'color-rendering',
                               'cursor', 'direction', 'display', 'dominant-baseline', 'enable-background', 'fill',
                               'fill-opacity', 'fill-rule', 'filter', 'flood-color', 'flood-opacity', 'font-family',
                               'font-size', 'font-size-adjust', 'font-stretch', 'font-style', 'font-variant',
                               'font-weight', 'glyph-orientation-horizontal', 'glyph-orientation-vertical',
                               'image-rendering', 'kerning', 'letter-spacing', 'lighting-color', 'marker-end',
                               'marker-mid', 'marker-start', 'mask', 'opacity', 'overflow', 'pointer-events',
                               'shape-rendering', 'stop-color', 'stop-opacity', 'stroke', 'stroke-dasharray',
                               'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit',
                               'stroke-opacity', 'stroke-width', 'text-anchor', 'transform', 'text-decoration',
                               'text-rendering', 'unicode-bidi', 'vector-effect', 'visibility', 'word-spacing',
                               'writing-mode',
                               'cx', 'cy', 'r', 'rx', 'ry', 'd', 'fill', 'transform']

svg_filter_attributes = ['height', 'result', 'width', 'x', 'y', 'type', 'tableValues', 'slope', 'intercept',
                         'amplitude', 'exponent', 'offset', 'xlink:href']

svg_animation_attributes = ['attributeType', 'attributeName', 'begin', 'dur', 'end', 'min', 'max', 'restart',
                            'repeatCount', 'repeatDur', 'fill', 'calcMode', 'values', 'keyTimes', 'keySplines', 'from',
                            'to', 'by', 'additive', 'accumulate']

svg_attr_dict = {'a': ['download', 'requiredExtensions', 'role', 'systemLanguage'],
                 'animate': ['accumulate', 'additive', 'attributeName', 'begin', 'by', 'calcMode', 'dur', 'end', 'fill',
                             'from', 'href', 'keySplines', 'keyTimes', 'max', 'min', 'repeatCount', 'repeatDur',
                             'requiredExtensions', 'restart', 'systemLanguage', 'to', 'values'],
                 'animateMotion': ['accumulate', 'additive', 'begin', 'by', 'calcMode', 'dur', 'end', 'fill', 'from',
                                   'href', 'keyPoints', 'keySplines', 'keyTimes', 'max', 'min', 'origin', 'path',
                                   'repeatCount', 'repeatDur', 'requiredExtensions', 'restart', 'rotate',
                                   'systemLanguage', 'to', 'values'],
                 'animateTransform': ['accumulate', 'additive', 'attributeName', 'begin', 'by', 'calcMode', 'dur',
                                      'end', 'fill', 'from', 'href', 'keySplines', 'keyTimes', 'max', 'min',
                                      'repeatCount', 'repeatDur', 'requiredExtensions', 'restart', 'systemLanguage',
                                      'to', 'type', 'values'],
                 'audio': ['requiredExtensions', 'role', 'systemLanguage'],
                 'canvas': ['preserveAspectRatio', 'requiredExtensions', 'role', 'systemLanguage'],
                 'circle': ['pathLength', 'requiredExtensions', 'role', 'systemLanguage'],
                 'clipPath': ['clipPathUnits', 'requiredExtensions', 'systemLanguage'],
                 'discard': ['begin', 'href', 'requiredExtensions', 'role', 'systemLanguage'],
                 'ellipse': ['pathLength', 'requiredExtensions', 'role', 'systemLanguage'],
                 'feBlend': ['height', 'in', 'in2', 'mode', 'result', 'width', 'x', 'y'],
                 'feColorMatrix': ['height', 'in', 'result', 'type', 'values', 'width', 'x', 'y'],
                 'feComponentTransfer': ['height', 'in', 'result', 'width', 'x', 'y'],
                 'feComposite': ['height', 'in', 'in2', 'k1', 'k2', 'k3', 'k4', 'operator', 'result', 'width', 'x',
                                 'y'],
                 'feConvolveMatrix': ['bias', 'divisor', 'edgeMode', 'height', 'in', 'kernelMatrix', 'kernelUnitLength',
                                      'order', 'preserveAlpha', 'result', 'targetX', 'targetY', 'width', 'x', 'y'],
                 'feDiffuseLighting': ['diffuseConstant', 'height', 'in', 'kernelUnitLength', 'result', 'surfaceScale',
                                       'width', 'x', 'y'],
                 'feDisplacementMap': ['height', 'in', 'in2', 'result', 'scale', 'width', 'x', 'xChannelSelector', 'y',
                                       'yChannelSelector'], 'feDistantLight': ['azimuth', 'elevation'],
                 'feDropShadow': ['dx', 'dy', 'height', 'in', 'result', 'stdDeviation', 'width', 'x', 'y'],
                 'feFlood': ['height', 'result', 'width', 'x', 'y'],
                 'feFuncA': ['amplitude', 'exponent', 'intercept', 'offset', 'slope', 'tableValues', 'type'],
                 'feFuncB': ['amplitude', 'exponent', 'intercept', 'offset', 'slope', 'tableValues', 'type'],
                 'feFuncG': ['amplitude', 'exponent', 'intercept', 'offset', 'slope', 'tableValues', 'type'],
                 'feFuncR': ['amplitude', 'exponent', 'intercept', 'offset', 'slope', 'tableValues', 'type'],
                 'feGaussianBlur': ['edgeMode', 'height', 'in', 'result', 'stdDeviation', 'width', 'x', 'y'],
                 'feImage': ['crossorigin', 'height', 'href', 'preserveAspectRatio', 'result', 'width', 'x', 'y'],
                 'feMerge': ['height', 'result', 'width', 'x', 'y'], 'feMergeNode': ['in'],
                 'feMorphology': ['height', 'in', 'operator', 'radius', 'result', 'width', 'x', 'y'],
                 'feOffset': ['dx', 'dy', 'height', 'in', 'result', 'width', 'x', 'y'], 'fePointLight': ['x', 'y', 'z'],
                 'feSpecularLighting': ['height', 'in', 'kernelUnitLength', 'result', 'specularConstant',
                                        'specularExponent', 'surfaceScale', 'width', 'x', 'y'],
                 'feSpotLight': ['limitingConeAngle', 'pointsAtX', 'pointsAtY', 'pointsAtZ', 'specularExponent', 'x',
                                 'y', 'z'], 'feTile': ['height', 'in', 'result', 'width', 'x', 'y'],
                 'feTurbulence': ['baseFrequency', 'height', 'numOctaves', 'result', 'seed', 'stitchTiles', 'type',
                                  'width', 'x', 'y'],
                 'filter': ['filterUnits', 'height', 'primitiveUnits', 'width', 'x', 'y'],
                 'foreignObject': ['requiredExtensions', 'role', 'systemLanguage'],
                 'g': ['requiredExtensions', 'role', 'systemLanguage'],
                 'iframe': ['requiredExtensions', 'role', 'systemLanguage'],
                 'image': ['crossorigin', 'href', 'preserveAspectRatio', 'requiredExtensions', 'role',
                           'systemLanguage'],
                 'line': ['pathLength', 'requiredExtensions', 'role', 'systemLanguage', 'x1', 'x2', 'y1', 'y2'],
                 'linearGradient': ['gradientTransform', 'gradientUnits', 'href', 'spreadMethod', 'x1', 'x2', 'y1',
                                    'y2'],
                 'marker': ['markerHeight', 'markerUnits', 'markerWidth', 'orient', 'preserveAspectRatio', 'refX',
                            'refY', 'viewBox'],
                 'mask': ['height', 'maskContentUnits', 'maskUnits', 'requiredExtensions', 'systemLanguage', 'width',
                          'x', 'y'], 'mpath': ['href'],
                 'path': ['pathLength', 'requiredExtensions', 'role', 'systemLanguage'],
                 'pattern': ['height', 'href', 'patternContentUnits', 'patternTransform', 'patternUnits',
                             'preserveAspectRatio', 'viewBox', 'width', 'x', 'y'],
                 'polygon': ['pathLength', 'points', 'requiredExtensions', 'role', 'systemLanguage'],
                 'polyline': ['pathLength', 'points', 'requiredExtensions', 'role', 'systemLanguage'],
                 'radialGradient': ['cx', 'cy', 'fr', 'fx', 'fy', 'gradientTransform', 'gradientUnits', 'href', 'r',
                                    'spreadMethod'],
                 'rect': ['pathLength', 'requiredExtensions', 'role', 'systemLanguage'], 'script': ['href'],
                 'set': ['attributeName', 'begin', 'dur', 'end', 'fill', 'href', 'max', 'min', 'repeatCount',
                         'repeatDur', 'requiredExtensions', 'restart', 'systemLanguage', 'to'], 'stop': ['offset'],
                 'style': ['media'],
                 'svg': ['playbackorder', 'preserveAspectRatio', 'requiredExtensions', 'role', 'systemLanguage',
                         'timelinebegin', 'transform', 'viewBox', 'zoomAndPan', 'xmlns', 'version'],
                 'switch': ['requiredExtensions', 'role', 'systemLanguage'],
                 'symbol': ['preserveAspectRatio', 'refX', 'refY', 'role', 'viewBox'],
                 'text': ['dx', 'dy', 'lengthAdjust', 'requiredExtensions', 'role', 'rotate', 'systemLanguage',
                          'textLength', 'x', 'y'],
                 'textPath': ['href', 'lengthAdjust', 'method', 'path', 'requiredExtensions', 'role', 'side', 'spacing',
                              'startOffset', 'systemLanguage', 'textLength'],
                 'tspan': ['dx', 'dy', 'lengthAdjust', 'requiredExtensions', 'role', 'rotate', 'systemLanguage',
                           'textLength', 'x', 'y'], 'unknown': ['requiredExtensions', 'role', 'systemLanguage'],
                 'use': ['href', 'requiredExtensions', 'role', 'systemLanguage'],
                 'video': ['requiredExtensions', 'role', 'systemLanguage'],
                 'view': ['preserveAspectRatio', 'role', 'viewBox', 'zoomAndPan']}

for tag in svg_tags_use:
    c_tag = tag[0].capitalize() + tag[1:]
    globals()[c_tag] = type(c_tag, (Div,),
                            {'html_tag': tag,
                             'attributes': svg_attr_dict.get(tag,
                                                             []) + svg_presentation_attributes + svg_filter_attributes})


# *************************** end SVG components

class HTMLEntity(Span):
    # Render HTML Entities

    def __init__(self, **kwargs):
        self.entity = ''
        super().__init__(**kwargs)

    def convert_object_to_dict(self) -> dict:
        d = super().convert_object_to_dict()
        d['inner_html'] = self.entity
        return d


class Hello(Div):

    def __init__(self, **kwargs):
        self.counter = 1
        super().__init__(**kwargs)
        self.class_ = 'm-1 p-1 text-2xl text-center text-white bg-blue-500 hover:bg-blue-800 cursor-pointer'
        self.text = 'Hello! (click me)'

        async def click(self, msg):
            self.text = f'Hello! I was clicked {self.counter} times'
            self.counter += 1

        self.on('click', click)


class QHello(Hello):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.class_ = 'text-h3 text-primary q-ma-md'


def component_by_tag(tag, context=None, **kwargs):
    tag_class_name = tag.capitalize()
    global_dict = globals()
    for dct in [global_dict, context.f_locals, context.f_globals]:
        if tag_class_name in dct:
            return dct[tag_class_name](**kwargs)
    else:
        raise ValueError(f'Tag not defined: {tag}')


class AutoTable(Table):
    """
    Creates an HTML table from a list of lists
    First list is used as headers
    """
    td_classes = 'border px-4 py-2 text-center'
    tr_even_classes = 'bg-gray-100 '
    tr_odd_classes = ''
    th_classes = 'px-4 py-2'

    def __init__(self, **kwargs):
        self.values = []
        super().__init__(**kwargs)

    def react(self, data):
        self.set_class('table-auto')
        # First row of values is header
        if self.values:
            headers = self.values[0]
            thead = Thead(a=self)
            tr = Tr(a=thead)
            for item in headers:
                Th(text=item, class_=self.th_classes, a=tr)
            tbody = Tbody(a=self)
            for i, row in enumerate(self.values[1:]):
                if i % 2 == 1:
                    tr = Tr(class_=self.tr_even_classes, a=tbody)
                else:
                    tr = Tr(class_=self.tr_odd_classes, a=tbody)
                for item in row:
                    Td(text=item, class_=self.td_classes, a=tr)


def get_websocket(event_data):
    return WebPage.instances[event_data['page_id']].websocket


def create_transition():
    return Dict({'enter': '', 'enter_start': '', 'enter_end': '',
                 'leave': '', 'leave_start': '', 'leave_end': '',
                 'load': '', 'load_start': '', 'load_end': ''
                 })


class Styles:
    button_simple = 'bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded'
    button_pill = 'bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full'
    button_outline = 'bg-transparent hover:bg-blue-500 text-blue-700 font-semibold hover:text-white py-2 px-4 border border-blue-500 hover:border-transparent rounded'
    button_bordered = 'bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 border border-blue-700 rounded'
    button_disabled = 'bg-blue-500 text-white font-bold py-2 px-4 rounded opacity-50 cursor-not-allowed'
    button_3d = 'bg-blue-500 hover:bg-blue-400 text-white font-bold py-2 px-4 border-b-4 border-blue-700 hover:border-blue-500 rounded'
    button_elevated = 'bg-white hover:bg-gray-100 text-gray-800 font-semibold py-2 px-4 border border-gray-400 rounded shadow'

    input_classes = "m-2 bg-gray-200 border-2 border-gray-200 rounded w-64 py-2 px-4 text-gray-700 focus:outline-none focus:bg-white focus:border-purple-500"

    # https://www.lipsum.com /
    lorem_ipsum = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
    """
