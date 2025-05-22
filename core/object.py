

class Object:
    things = {}
    DEBUG = True

    @staticmethod
    def add(obj):
        try:
            o = str(obj)
        except:
            o = str(obj.__class__)

        Object.things.update({(id(obj)): o})

    @staticmethod
    def rem(obj):
        try:
            del Object.things[id(obj)]
        except:
            pass

    @staticmethod
    def dump():
        pass

    @staticmethod
    def free(obj):
        primitives = (int, str, bool, float, bytes)
        for key in list(obj.__dict__.keys()):
            if type(getattr(obj, key)) in primitives:
                continue
            delattr(obj, key)
