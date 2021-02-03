import jp


class TodoList(jp.Ol):

    def __init__(self, **kwargs):
        self.todos = []
        super().__init__(**kwargs)

    def react(self):
        self.delete_components()
        for todo in self.todos:
            jp.Li(text=todo, a=self)


def todo_app():
    wp = jp.WebPage(tailwind=False)
    todo_list = TodoList(a=wp, todos=['Buy groceries', 'Learn JustPy', 'Do errands'])
    task = jp.Input(placeholder='Enter task', a=wp)

    def add_task(self, msg):
        todo_list.todos.append(task.value)
        task.value = ''

    jp.Button(text='Add Task', a=wp, click=add_task, style='margin-left: 10px')

    return wp


# jp.justpy(todo_app)
jp.justpy(todo_app, websockets=False)
