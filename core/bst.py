

class TreeNode:

    def __init__(self, key, val, left=None, right=None, parent=None):
        self.key = key
        self.payload = val
        self.left = left
        self.right = right
        self.parent = parent

    def has_left_child(self):
        return self.left

    def has_right_child(self):
        return self.right

    def is_left_child(self):
        return self.parent and self.parent.left == self

    def is_right_child(self):
        return self.parent and self.parent.right == self

    def is_root(self):
        return not self.parent

    def is_leaf(self):
        return not (self.right or self.left)

    def has_any_children(self):
        return self.right or self.left

    def has_both_children(self):
        return self.right and self.left

    def replace_node_data(self, key, value, lc, rc):
        self.key = key
        self.payload = value
        self.left = lc
        self.right = rc
        if self.has_left_child():
            self.left.parent = self
        if self.has_right_child():
            self.right.parent = self


class BinarySearchTree:

    def __init__(self):
        self.root = None
        self.size = 0
        return

    def length(self):
        return self.size

    def __len__(self):
        return self.size

    def put(self, key, val):
        if self.root:
            self._put(key, val, self.root)
        else:
            self.root = TreeNode(key, val)
        self.size = self.size + 1

    def _put(self, key, val, current_node):
        if key < current_node.key:
            if current_node.has_left_child():
                self._put(key, val, current_node.left)
            else:
                current_node.left = TreeNode(key, val, parent=current_node)
        elif current_node.has_right_child():
            self._put(key, val, current_node.right)
        else:
            current_node.right = TreeNode(key, val, parent=current_node)

    def __setitem__(self, k, v):
        self.put(k, v)

    def get(self, key):
        if self.root:
            res = self._get(key, self.root)
            if res:
                return res.payload
            else:
                return
        else:
            return
        return

    def _get(self, key, current_node):
        if not current_node:
            return
        else:
            if current_node.key == key:
                return current_node
            else:
                if key < current_node.key:
                    return self._get(key, current_node.left)
                return self._get(key, current_node.right)
            return

    def __getitem__(self, key):
        return self.get(key)

    def __contains__(self, key):
        if self._get(key, self.root):
            return True
        else:
            return False

    def delete(self, key):
        if self.size > 1:
            nodeToRemove = self._get(key, self.root)
            if nodeToRemove:
                self.remove(nodeToRemove)
                self.size = self.size - 1
            else:
                raise KeyError("Error, key not in tree")
        elif self.size == 1 and self.root.key == key:
            self.root = None
            self.size = self.size - 1
        else:
            raise KeyError("Error, key not in tree")
        return

    def __delitem__(self, key):
        self.delete(key)

    def splice_out(self):
        if self.is_leaf():
            if self.is_left_child():
                self.parent.left = None
            else:
                self.parent.right = None
        elif self.has_any_children():
            if self.has_left_child():
                if self.is_left_child():
                    self.parent.left = self.left
                else:
                    self.parent.right = self.left
                self.left.parent = self.parent
            elif self.is_left_child():
                self.parent.left = self.right
            else:
                self.parent.right = self.right
            self.right.parent = self.parent
        return

    def find_successor(self):
        succ = None
        if self.has_right_child():
            succ = self.right.find_min()
        elif self.parent:
            if self.is_left_child():
                succ = self.parent
            else:
                self.parent.right = None
                succ = self.parent.find_successor()
                self.parent.right = self
        return succ

    def find_min(self):
        current = self
        while current.has_left_child():
            current = current.left

        return current

    def remove(self, current_node):
        if current_node.is_leaf():
            if current_node == current_node.parent.left:
                current_node.parent.left = None
            else:
                current_node.parent.right = None
        elif current_node.has_both_children():
            succ = current_node.find_successor()
            succ.splice_out()
            current_node.key = succ.key
            current_node.payload = succ.payload
        elif current_node.has_left_child():
            if current_node.is_left_child():
                current_node.left.parent = current_node.parent
                current_node.parent.left = current_node.left
            elif current_node.is_right_child():
                current_node.left.parent = current_node.parent
                current_node.parent.right = current_node.left
            else:
                current_node.replace_node_data(current_node.left.key, current_node.left.payload, current_node.left.left, current_node.left.right)
        elif current_node.is_left_child():
            current_node.right.parent = current_node.parent
            current_node.parent.left = current_node.right
        elif current_node.is_right_child():
            current_node.right.parent = current_node.parent
            current_node.parent.right = current_node.right
        else:
            current_node.replace_node_data(current_node.right.key, current_node.right.payload, current_node.right.left, current_node.right.right)
        return
