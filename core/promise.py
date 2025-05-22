import sublime
from .object import Object

class Promise:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self):
        if Object.DEBUG:
            Object.add(self)
        self._callbacks_resolved = []
        self._callbacks_rejected = []
        self._resolved = None
        self._rejected = None
        return

    @staticmethod
    def all(promises):
        # Create a new Promise that will be resolved when all input promises are resolved
        result = Promise()

        # Iterate through each promise in the input list
        for p in promises:
            # Attach a 'then' callback to each promise.
            # This lambda will be called when 'p' resolves.
            # The 'promises' and 'result' variables are captured from the outer scope (closure).
            p.then(lambda *args: result.resolve() if all(pr.is_resolved() for pr in promises) else None)

        # The 'all' method itself returns the new 'result' Promise immediately.
        # Its resolution depends on the callbacks attached to individual promises.
        return result

    def then(self, callback):
        if self._rejected is None:
            if self._resolved is not None:
                callback(*self._resolved)
            elif callback not in self._callbacks_resolved:
                self._callbacks_resolved.append(callback)
        return self

    def otherwise(self, callback):
        if self._resolved is None:
            if self._rejected is not None:
                callback(*self._rejected)
            elif callback not in self._callbacks_rejected:
                self._callbacks_rejected.append(callback)
        return

    def is_resolved(self):
        return self._resolved not in (None, False)

    def is_rejected(self):
        return self._rejected not in (None, False)

    def resolve(self, *args):
        if self._resolved is None:
            if self._rejected is None:
                self._resolved = args
                while len(self._callbacks_resolved):
                    self._callbacks_resolved.pop(0)(*self._resolved)

        self._callbacks_rejected = []
        self._callbacks_resolved = []
        return

    def reject(self, *args):
        if self._resolved is None:
            if self._rejected is None:
                self._rejected = args
                while len(self._callbacks_rejected):
                    self._callbacks_rejected.pop(0)(*self._rejected)

        self._callbacks_rejected = []
        self._callbacks_resolved = []
        return
