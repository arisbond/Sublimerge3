from bisect import bisect
import difflib
from ..object import Object

class PatienceSequenceMatcher(difflib.SequenceMatcher):
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, isjunk=None, a="", b=""):
        if Object.DEBUG:
            Object.add(self)
        difflib.SequenceMatcher.__init__(self, isjunk, a, b)

    def _unique_lcs(self, a, b):
        index1 = {}
        index2 = {}
        btoa = [None]*len(b)
        backs = [None] * len(b)
        stacks = []
        lasts = []
        n = 0
        for i in range(len(a)):
            line = a[i]
            index1[line] = None if line in index1 else i

        for pos, line in enumerate(b):
            _next = index1.get(line)
            if _next is not None:
                if line in index2:
                    btoa[index2[line]] = None
                    del index1[line]
                else:
                    index2[line] = pos
                    btoa[pos] = _next

        for b_pos, a_pos in enumerate(btoa):
            if a_pos is None:
                continue
            if stacks and stacks[-1] < a_pos:
                n = len(stacks)
            elif stacks and stacks[n] < a_pos and (n == len(stacks) - 1 or stacks[n + 1] > a_pos):
                n += 1
            else:
                n = bisect(stacks, a_pos)
            if n > 0:
                backs[b_pos] = lasts[n - 1]
            if n < len(stacks):
                stacks[n] = a_pos
                lasts[n] = b_pos
            else:
                stacks.append(a_pos)
                lasts.append(b_pos)

        if len(lasts) == 0:
            return []
        result = []
        n = lasts[-1]
        while n is not None:
            result.append((btoa[n], n))
            n = backs[n]

        result.reverse()
        return result

    def _recurse_matches(self, a, b, a_lo, b_lo, a_hi, b_hi, matches, max_recursion):
        if max_recursion < 0 or a_lo == a_hi or b_lo == b_hi:
            return
        last_length = len(matches)
        last_a_pos = a_lo - 1
        last_b_pos = b_lo - 1
        for a_pos, b_pos in self._unique_lcs(a[a_lo:a_hi], b[b_lo:b_hi]):
            a_pos += a_lo
            b_pos += b_lo
            if last_a_pos + 1 != a_pos or last_b_pos + 1 != b_pos:
                self._recurse_matches(a, b, last_a_pos + 1, last_b_pos + 1, a_pos, b_pos, matches, max_recursion - 1)
            last_a_pos = a_pos
            last_b_pos = b_pos
            matches.append((a_pos, b_pos))

        if len(matches) > last_length:
            self._recurse_matches(a, b, last_a_pos + 1, last_b_pos + 1, a_hi, b_hi, matches, max_recursion - 1)
        elif a[a_lo] == b[b_lo]:
            while a_lo < a_hi and b_lo < b_hi and a[a_lo] == b[b_lo]:
                matches.append((a_lo, b_lo))
                a_lo += 1
                b_lo += 1

            self._recurse_matches(a, b, a_lo, b_lo, a_hi, b_hi, matches, max_recursion - 1)
        elif a[a_hi - 1] == b[b_hi - 1]:
            na_hi = a_hi - 1
            nb_hi = b_hi - 1
            while na_hi > a_lo and nb_hi > b_lo and a[na_hi - 1] == b[nb_hi - 1]:
                na_hi -= 1
                nb_hi -= 1

            self._recurse_matches(a, b, last_a_pos + 1, last_b_pos + 1, na_hi, nb_hi, matches, max_recursion - 1)
            for i in range(a_hi - na_hi):
                matches.append((na_hi + i, nb_hi + i))

    def _collapse_matches(self, matches):
        collapsed = []
        start_a = start_b = None
        length = 0
        for i_a, i_b in matches:
            if start_a is not None and i_b == start_b + length and i_a == start_a + length:
                length += 1
            # elif start_a is not None:
            #     collapsed.append((start_a, start_b, length))
            # start_a = i_a
            # start_b = i_b
            # length = 1
            # """decompile fix"""
            else:
                if start_a is not None:
                    collapsed.append((start_a, start_b, length))
                start_a = i_a
                start_b = i_b
                length = 1

        if length != 0:
            collapsed.append((start_a, start_b, length))
        return collapsed

    def get_matching_blocks(self):
        if self.matching_blocks is not None:
            return self.matching_blocks

        matches = []
        self._recurse_matches(self.a, self.b, 0, 0, len(self.a), len(self.b), matches, 10)
        self.matching_blocks = self._collapse_matches(matches)
        self.matching_blocks.append((len(self.a), len(self.b), 0))
        return self.matching_blocks
