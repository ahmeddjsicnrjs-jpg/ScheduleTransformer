from NodeGraphQt import BaseNode


class OperationNode(BaseNode):
    """
    Вузол операції у графі процесів.
    Має вхідний порт (залежності) та вихідний порт (наступні операції).
    Властивості: тривалість, кількість працівників.
    """

    __identifier__ = 'schedule.nodes'
    NODE_NAME = 'Операція'

    def __init__(self):
        super().__init__()
        self.add_input('вхід', multi_input=True, color=(180, 80, 80))
        self.add_output('вихід', multi_output=True, color=(80, 180, 80))

        self.add_text_input('op_name', label='Назва', text='Нова операція',
                            tooltip='Назва операції')

        self.create_property('duration', 1, widget_type=7, range=(1, 9999),
                             widget_tooltip='Тривалість (хв)')
        self.create_property('workers_needed', 1, widget_type=7, range=(1, 100),
                             widget_tooltip='Кількість працівників')

        self.set_color(40, 60, 100)
