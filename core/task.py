from threading import Thread
from .promise import Promise
from .thread_progress import ThreadProgress

def _process(promise, task, task_args):
    try:
        promise.resolve(task(*task_args))
    except Exception as e:
        promise.reject(e)


class Task:

    @classmethod
    def spawn(self, task, *task_args):
        return Task(task, *task_args)

    def __init__(self, task, *task_args):
        self._promise = Promise()
        self._thread = Thread(target=_process, args=(self._promise, task, task_args))
        self._thread.start()

    def then(self, cb):
        self._promise.then(cb)
        return self

    def otherwise(self, cb):
        self._promise.otherwise(cb)
        return self

    def is_resolved(self):
        return self._promise.is_resolved()

    def is_rejected(self):
        return self._promise.is_rejected()

    def progress(self, text):
        ThreadProgress(self._thread, text)
        return self
