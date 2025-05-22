import sublime

class NavigationBehavior:

    def __init__(self):
        self._selected_index = 0

    def is_2way(self):
        return True

    def is_3way(self):
        return False

    def get_previous_change(self, change_only=False):
        return self._listing.get_previous_node(change_only)

    def get_next_change(self, change_only=False):
        return self._listing.get_next_node(change_only)

    def get_selected_change(self):
        return self._listing.get_selected_node()

    def select_current_change(self):
        return self._listing.select_current_node()

    def select_next_change(self, change_only=False):
        return self._listing.select_next_node(change_only)

    def select_previous_change(self, change_only=False):
        return self._listing.select_previous_node(change_only)

    def go_into_selected_change(self):
        node = self._listing.get_selected_node()
        if node:
            if node.is_dir():
                if not node.has_missing():
                    self._listing = self._listing.enter_selected_node()
            else:
                self._compare_node(node)

    def go_back(self):
        listing = self._listing.enter_parent_node()
        if listing:
            self._listing = listing
