import sublime, re

class XML_Path:

    def __init__(self, root):
        self._root = root

    def query(self, query):
        root = self._root
        paths = query.split("/")
        len_paths = len(paths)
        for i, path in enumerate(paths):
            if path:
                result = []
                LIST_ALL = i < len_paths - 1 and paths[i + 1] == "*"
                for child in root.childnodes():
                    if isinstance(child, XML_Element):
                        if LIST_ALL:
                            if child.tag_name() == path:
                                result.append(child)
                        else:
                            if path == child.tag_name():
                                root = child
                                break
                            continue

                if LIST_ALL:
                    return result
                continue

        return root


class XML_Node:

    def __init__(self):
        self._parent_node = None
        return

    def set_parent_node(self, parent):
        self._parent_node = parent

    def remove(self):
        if self._parent_node:
            self._parent_node.remove_child(self)


class XML_TextNode(XML_Node):

    def __init__(self, text):
        XML_Node.__init__(self)
        self._text = text

    def __repr__(self):
        return self._text


class XML_Element(XML_Node):
    RE_ATTRIBUTES = re.compile('([a-zA-Z][a-zA-Z0-9_-]*)\\s*=\\s*("|\')(.*)(\\2)')

    def __init__(self, tag, attributes, self_closing):
        XML_Node.__init__(self)
        attrs = {}
        for item in re.finditer(self.RE_ATTRIBUTES, attributes):
            attrs.update({(item.group(1)): (item.group(3))})

        self._tag = tag
        self._attributes = attrs
        self._childnodes = []
        self._self_closing = self_closing

    def __repr__(self):
        ret = "<%s%s" % (self._tag, self._attributes)
        if self._self_closing:
            return ret + "/>"
        ret += ">"
        for child in self._childnodes:
            ret += str(child)

        return ret + "</" + self._tag + ">"

    def get_attribute(self, attr):
        if attr in self._attributes:
            return self._attributes[attr]
        else:
            return

    def query(self, query):
        return XML_Path(self).query(query)

    def append_child(self, child):
        self._childnodes.append(child)
        child.set_parent_node(self)

    def tag_name(self):
        return self._tag

    def childnodes(self):
        return self._childnodes[:]

    def remove_child(self, child):
        return self._childnodes.remove(child)

    def text(self, to_set=None):
        if to_set:
            self._childnodes = [
             XML_TextNode(text)]
        else:
            text = ""
            for child in self._childnodes:
                if isinstance(child, XML_TextNode):
                    text += str(child)
                else:
                    text += child.get_text()

            return text

    def traverse(self):
        for child in self._childnodes:
            if isinstance(child, XML_TextNode):
                yield child
            else:
                yield child
                for c in child.traverse():
                    yield c


class XML:
    XML_META_RE = re.compile("(<[!?][^>]+>)")
    XML_SPLIT_RE = re.compile("(<[^>]+>)")
    XML_TAG_BEGIN_RE = re.compile("<([^\\s/]+)([^>]*)>")
    XML_TAG_END_RE = re.compile("</([^>]+)>")

    def __init__(self):
        self._data = []
        self._dom = None
        return

    def __repr__(self):
        return "".join([str(v) for v in self._data])

    def load_string(self, text):
        self._data = []
        for item in re.split(XML.XML_META_RE, text):
            if item.strip() == "" or re.match(XML.XML_META_RE, item):
                self._data.append(XML_TextNode(item))
            else:
                self._data.append(self._parse(item))
                self._dom = self._data[-1]

    def _parse(self, text):
        current = None
        stack = []
        for item in re.split(XML.XML_SPLIT_RE, text):
            tag_begin = re.match(XML.XML_TAG_BEGIN_RE, item)
            if tag_begin:
                self_closing = item.endswith("/>")
                node = XML_Element(tag_begin.group(1), tag_begin.group(2), self_closing)
                if not current:
                    current = node
                else:
                    current.append_child(node)
                    if not self_closing:
                        current = node
                if not self_closing:
                    stack.append(node)
            else:
                tag_end = re.match(XML.XML_TAG_END_RE, item)
                if tag_end:
                    closed = stack.pop()
                    if tag_end.group(1) != closed.tag_name():
                        raise Exception("Expected `</%s>`, but `</%s>` found" % (closed.tag_name(), tag_end.group(1)))
                    if len(stack) > 0:
                        current = stack[-1]
                    else:
                        return current
                elif current:
                    current.append_child(XML_TextNode(item))
                    continue

        return

    def root(self):
        return self._dom

    def traverse(self):
        return self._dom.traverse()

    def query(self, query):
        return XML_Path(self._dom).query(query)
