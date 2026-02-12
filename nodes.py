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
        self.add_text_input('duration_hours', label='Тривалість (год)', text='',
                            tooltip='Тривалість операції у годинах')
        self.add_text_input('duration_days', label='Тривалість (дн)', text='',
                            tooltip='Тривалість операції у днях (1 день = 8 робочих годин)')
        self.add_text_input('workers_needed', label='Працівників', text='1',
                            tooltip='Кількість працівників для операції')

        self.set_color(40, 60, 100)
