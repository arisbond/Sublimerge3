

class Observable:
    EVENTS = []

    def __init__(self):
        self._Observable__handlers = {}
        self._Observable__silent = []

    def set_silent(self, event, silent):
        if event not in self.EVENTS:
            raise Exception("unsupported event: " + event)
        if silent and event not in self._Observable__silent:
            self._Observable__silent.append(event)
        elif not silent:
            if event in self._Observable__silent:
                self._Observable__silent.remove(event)

    def on(self, event, callback, prepend=False):
        try:
            if event not in self.EVENTS:
                raise Exception("unsupported event: " + event)
            if event not in self._Observable__handlers:
                self._Observable__handlers.update({event: [callback]})
            elif not prepend:
                self._Observable__handlers[event].append(callback)
            else:
                self._Observable__handlers[event].insert(0, callback)
        except:
            pass

    def un(self, event=None, callback=None):
        try:
            if event is None:
                self._Observable__handlers = {}
                return
            if event not in self.EVENTS:
                raise Exception("unsupported event: " + event)
            if event not in self._Observable__handlers:
                return
            if callback is None:
                del self._Observable__handlers[event]
            elif callback in self._Observable__handlers[event]:
                self._Observable__handlers[event].remove(callback)
        except:
            pass

        return

    def fire(self, event, *args):
        try:
            if event in self._Observable__silent:
                return
        except:
            return

        if event not in self.EVENTS:
            raise Exception("unsupported event: " + event)
        if event in self._Observable__handlers:
            handlers = self._Observable__handlers[event][:]
            for callback in handlers:
                if event == "destroy":
                    self._Observable__handlers[event].remove(callback)
                if event not in self._Observable__silent:
                    if callback(self, *args) is False:
                        break
                    continue
