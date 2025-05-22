import sublime, os
from ...diff.directories import DiffDirectories
from ...task import Task
from ...promise_progress import PromiseProgress
from ...object import Object
from .item import Item, TYPE_REMOVED, TYPE_CHANGE, TYPE_INSERTED, SIDE_LEFT, SIDE_RIGHT
from .node import Node

class Listing:

    def __init__(self, left_path, right_path, left_panel, right_panel, parent_listing=None, parent_node=None):
        self._left_path = left_path
        self._right_path = right_path
        self._left_panel = left_panel
        self._right_panel = right_panel
        self._diff = DiffDirectories(left_path, right_path)
        self._nodes = []
        self._nodes_by_name = {}
        self._parent_listing = parent_listing
        self._parent_node = parent_node
        self._data = self._diff.listing()
        self._create_nodes()
        self._is_displayed = False
        self._selected_index = 0

    def destroy(self):
        Object.free(self)

    def create(self):
        self.display()
        return Task.spawn(self._deep).progress("Computing differences...")

    def refresh(self, node=None):
        if node:
            self._modify_parent_node_diffs_count(node, -node.diffs if node.is_equal() else node.diffs)
        self._data = self._diff.listing()
        self._create_nodes(node)

    def remove(self, node):
        if node:
            self._modify_parent_node_diffs_count(node, -node.diffs)
        del self._nodes_by_name[node.get_name()]
        pos = self._nodes.index(node)
        self._nodes.remove(node)
        for data in self._data["items"][:]:
            if data.get_name() == node.get_name():
                self._data["items"].remove(data)
                continue

        node.destroy()
        for i in range(pos, len(self._nodes)):
            self._nodes[i].set_row(self._nodes[i].get_row() - 1)
            self._nodes[i].render()

        self.select_current_node()

    def _deep(self):
        for node in self._nodes:
            self._deep_node(node)

    def _deep_node(self, node):
        if node.diffs:
            self._modify_parent_node_diffs_count(node, node.diffs)
        if not node.is_dir() or node.has_missing():
            return
        node.listing = Listing(left_path=node.left.path, right_path=node.right.path, left_panel=self._left_panel, right_panel=self._right_panel, parent_listing=self, parent_node=node)
        node.listing._deep()

    def _create_nodes(self, updated_node=None):
        row = 2
        if not updated_node:
            for node in self._nodes:
                node.clear()

            self._nodes = []
            self._nodes_by_name = {}
        else:
            for data in self._data["items"]:
                if data.get_name() == updated_node.get_name():
                    updated_node.left = Item(data.get_name(), data.left, self._left_panel, SIDE_LEFT, False)
                    updated_node.right = Item(data.get_name(), data.right, self._right_panel, SIDE_RIGHT, False)
                    updated_node.left_path = self._left_path
                    updated_node.right_path = self._right_path
                    count_diffs = updated_node.diffs
                    updated_node.diffs = data.diffs
                    updated_node.render()
                    updated_node.render()
                    self._deep_node(updated_node)
                    return

            return
        for i, data in enumerate(self._data["items"]):
            left_item = Item(data.get_name(), data.left, self._left_panel, SIDE_LEFT, False)
            right_item = Item(data.get_name(), data.right, self._right_panel, SIDE_RIGHT, False)
            node = Node(left_item, right_item, self._left_path, self._right_path, data.diffs, row, self._data["max_len"])
            self._nodes_by_name.update({(node.get_name()): node})
            self._nodes.append(node)
            row += 1

    def _modify_parent_node_diffs_count(self, node, value):
        if self._parent_listing:
            self._parent_node.diffs += value
            self._parent_listing._modify_parent_node_diffs_count(self._parent_node, value)
        if self._is_displayed:
            if node.is_dir():
                self._nodes_by_name[node.get_name()].mark()

    def _clear_parent_node_diffs_count(self, value):
        if self._parent_listing:
            self._parent_node.diffs = sum([v.diffs for v in self._nodes]) + value
            self._parent_listing._clear_parent_node_diffs_count(value)

    def _create_header(self):
        header = {"name": "Name", 
         "size": "Size", 
         "modified": "Last Modified"}
        for name in header:
            self._data["max_len"][name] = max(self._data["max_len"][name], len(header[name]))

        self._header = Node(Item("/header", header, self._left_panel, SIDE_LEFT, True), Item("/header", header, self._right_panel, SIDE_RIGHT, True), None, None, 0, 0, self._data["max_len"])
        return self._header.render()

    def display(self):
        self._is_displayed = True
        self._left_panel.get_view().set_name(self._data["left"])
        self._right_panel.get_view().set_name(self._data["right"])
        left_content, right_content = self._create_header()
        left_content += "\n"
        right_content += "\n"
        for node in self._nodes:
            l, r = node.render()
            left_content += l
            right_content += r

        self._left_panel.get_view().run_command("sublimerge_view_replace", {"begin": 0, 
         "end": (self._left_panel.get_view().size()), 
         "text": left_content})
        self._right_panel.get_view().run_command("sublimerge_view_replace", {"begin": 0, 
         "end": (self._right_panel.get_view().size()), 
         "text": right_content})
        for node in self._nodes:
            node.render()
            node.mark()

        self.select_current_node()

    def enter_selected_node(self):
        node = self.get_selected_node()
        if node:
            if node.is_dir():
                for v in self._nodes:
                    v.clear()

                self._is_displayed = False
                node.listing.display()
        return node.listing

    def enter_parent_node(self):
        if self._parent_listing:
            for node in self._nodes:
                node.clear()

            self._is_displayed = False
            self._parent_listing.display()
            return self._parent_listing

    def get_previous_node(self, change_only=False):
        offset = self._selected_index
        while len(self._nodes) > 0 and offset > 0:
            offset -= 1
            if not change_only or self._nodes[offset].diffs > 0:
                return (self._nodes[offset], offset)

    def get_next_node(self, change_only=False):
        size = len(self._nodes)
        offset = self._selected_index
        while size > 0 and offset < size - 1:
            offset += 1
            if not change_only or self._nodes[offset].diffs > 0:
                return (self._nodes[offset], offset)

    def get_selected_node(self):
        if self._selected_index >= 0:
            self._selected_index = min(self._selected_index, len(self._nodes))
            return self._nodes[self._selected_index]

    def select_current_node(self):
        node = self.get_selected_node()
        if node:
            node.select()

    def select_next_node(self, change_only=False):
        node, index = self.get_next_node(change_only)
        if node:
            current = self.get_selected_node()
            if current:
                current.unselect()
            self._selected_index = index
            node.select()
            self._ensure_in_viewport(node)

    def select_previous_node(self, change_only=False):
        node, index = self.get_previous_node(change_only)
        if node:
            current = self.get_selected_node()
            if current:
                current.unselect()
            self._selected_index = index
            node.select()
            self._ensure_in_viewport(node)

    def _ensure_in_viewport(self, node):
        self._left_panel.scroll_to(node.left.get_region())
        self._right_panel.scroll_to(node.right.get_region())
