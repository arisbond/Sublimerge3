import re, sublime
from difflib import SequenceMatcher
from ..utils import normalize_crlf, prepare_to_compare, splitlines, sort
from ..settings import Settings
from ..object import Object
from ..debug import console
from .matchers import PatienceSequenceMatcher

def get_hunk_type(hunk1, hunk2):
    if hunk1[1] == 0:
        return "+"
    if hunk2[1] == 0:
        return "-"
    return "."


def prepare_text_for_diff(text):
    text = prepare_to_compare(text)
    return text + "\nEOF"


def unified_diff(a, b, matcher=None):
    for group in matcher(None, a, b).get_grouped_opcodes(0):
        i1, i2, j1, j2 = (group[0][1], group[-1][2], group[0][3], group[-1][4])
        yield (i1 + 1, i2 - i1, j1 + 1, j2 - j1)



class Differ2:
    HUNK_RE = re.compile("^@@ \\-(\\d+),?(\\d*) \\+(\\d+),?(\\d*) @@")
    ALGORITHMS = {
        "": SequenceMatcher,
        None: SequenceMatcher,
        "patience": PatienceSequenceMatcher
    }
    ZERO_OFFSET = 0
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self):
        if Object.DEBUG:
            Object.add(self)
        self._seq_number = 0
        self.diff_test()

    def diff_test(self):

        def callback(seq_number, left, right):
            if left[0] != right[0]:
                self.ZERO_OFFSET = 1

        self.difference("a\nb\n\\c\n\\d", "a\n\\c\n\\d", False, callback)

    def difference(self, text1, text2, separate_missing_blocks=False, callback=None, callback_done=None, their_crlf=False, mine_crlf=False):

        def correct(data):
            if data[1] < data[0]:
                data[1] = 0
            if data[1] == 0:
                data[0] += self.ZERO_OFFSET
            return data

        def prepare(start_left, size_left, start_right, size_right):
            end_left = size_left + start_left - 1
            end_right = size_right + start_right - 1
            type_left = type_right = "."
            if end_left < start_left:
                type_left = "-"
                type_right = "+"
            elif end_right < start_right:
                type_right = "-"
                type_left = "+"
            left = correct([start_left, end_left, size_right - size_left, type_left])
            right = correct([start_right, end_right, size_left - size_right, type_right])
            if callback is not None:
                callback(self._seq_number, left, right)
            """decompile difference"""
            self._seq_number += 1

        if not isinstance(text1, list):
            lines1 = splitlines(prepare_text_for_diff(normalize_crlf(text1, their_crlf)))
        else:
            lines1 = text1
        if not isinstance(text2, list):
            lines2 = splitlines(prepare_text_for_diff(normalize_crlf(text2, mine_crlf)))
        else:
            lines2 = text2
        try:
            algorithm = Settings.get("algorithm")
            matcher = self.ALGORITHMS[algorithm]
        except:
            print("Sublimerge: unknown diff algorithm:", algorithm)

        gen = unified_diff(lines1, lines2, matcher=matcher)
        data = {"left": [],  "right": []}
        self._seq_number = 0
        for line in gen:
            if isinstance(line, tuple):
                start_left = line[0]
                start_right = line[2]
                size_left = line[1]
                size_right = line[3]
            # elif not line.startswith("@"):
            #     continue
            # hunk = re.match(self.HUNK_RE, line)
            # if not hunk:
            #     continue
            # start_left = int(hunk.group(1))
            # start_right = int(hunk.group(3))
            # size_left = int(hunk.group(2) or 1)
            # size_right = int(hunk.group(4) or 1)
            # """decompile fix"""
            else:
                if not line.startswith('@'):
                    continue
                hunk = re.match(self.HUNK_RE, line)
                if not hunk:
                    continue
                start_left = int(hunk.group(1))
                start_right = int(hunk.group(3))
                size_left = int(hunk.group(2) or 1)
                size_right = int(hunk.group(4) or 1)
            if size_left > 0 and size_left < size_right and separate_missing_blocks:
                prepare(start_left, size_left, start_right, size_left)
                prepare(start_left + size_left - self.ZERO_OFFSET, 0, start_right + size_left, size_right - size_left)
            elif size_right > 0 and size_right < size_left and separate_missing_blocks:
                prepare(start_left, size_right, start_right, size_right)
                prepare(start_left + size_right, size_left - size_right, start_right + size_right - self.ZERO_OFFSET, 0)
            else:
                prepare(start_left, size_left, start_right, size_right)

        if callback_done is not None:
            callback_done()
        return data


class Change:

    def __init__(self, their=None, their_base=None, mine=None, mine_base=None):
        self.their = their
        self.their_base = their_base
        self.mine = mine
        self.mine_base = mine_base
        self.base = None

    def __repr__(self):
        return " ".join([
            "their", str(self.their),
            "their_base", str(self.their_base),
            "mine_base", str(self.mine_base),
            "mine", str(self.mine),
            "    -->    ",
            "base", str(self.base)])

    def is_conflict(self):
        return self.mine[3] == "!"


class Differ3:

    def difference(self, their, base, mine, callback, callback_merged, callback_done, their_crlf=False, base_crlf=False, mine_crlf=False):
        HUNK_BEGIN = 0
        HUNK_END = 1
        HUNK_MISS = 2
        HUNK_TYPE = 3
        their_original = splitlines(normalize_crlf(their))
        mine_original = splitlines(normalize_crlf(mine))
        their_original.append("\n")
        mine_original.append("\n")
        their_lines = splitlines(prepare_text_for_diff(normalize_crlf(their, their_crlf)))
        base_lines = splitlines(prepare_text_for_diff(normalize_crlf(base, base_crlf)))
        mine_lines = splitlines(prepare_text_for_diff(normalize_crlf(mine, mine_crlf)))
        their_changes = []
        mine_changes = []
        result_changes = []

        def hunk_to_text(text, hunk):
            lines = hunk_to_lines(hunk)
            return text[min(lines) - 1:max(lines) - 1]

        def verify_conflict(change):
            text_their = hunk_to_text(their_lines, change.their)
            text_mine = hunk_to_text(mine_lines, change.mine)
            if text_their or text_mine:
                if prepare_to_compare("".join(text_their)) == prepare_to_compare("".join(text_mine)):
                    change.their[HUNK_TYPE] = change.mine[HUNK_TYPE] = "."

        def hunk_to_line_set(hunk):
            return set(hunk_to_lines(hunk))

        def hunk_to_lines(hunk):
            if hunk[HUNK_END] == 0:
                return range(hunk[HUNK_BEGIN], hunk[HUNK_BEGIN] + 1)
            return range(hunk[HUNK_BEGIN], hunk[HUNK_END] + 1)

        def hunk_size(hunk):
            if hunk[HUNK_END] == 0:
                return 0
            return hunk[HUNK_END] - hunk[HUNK_BEGIN] + 1

        def align_hunks(change):
            hunks = [change.their, change.mine]
            sizes = [hunk_size(hunk) for hunk in hunks]
            highest = max(sizes)
            for i, hunk in enumerate(hunks):
                hunk[HUNK_MISS] = highest - sizes[i]

        def overlaps(hunk1, hunk2):
            if not hunk1 or not hunk2:
                return False
            return hunk_to_line_set(hunk1) & hunk_to_line_set(hunk2)

        def collect_their_to_base(seq_number, their_hunk, base_hunk):
            their_changes.append(Change(their=their_hunk, their_base=base_hunk))

        def collect_mine_to_base(seq_number, mine_hunk, base_hunk):
            mine_changes.append(Change(mine=mine_hunk, mine_base=base_hunk))

        def collect_their_to_mine(seq_number, their_hunk, mine_hunk):
            change = Change(their=their_hunk, mine=mine_hunk)
            for their_change in their_changes[:]:
                if overlaps(their_change.their, their_hunk):
                    change.their_base = their_change.their_base
                    break

            for mine_change in mine_changes[:]:
                if overlaps(mine_change.mine, mine_hunk):
                    change.mine_base = mine_change.mine_base
                    break

            if overlaps(change.their_base, change.mine_base) or change.mine_base and change.their_base and overlaps(change.their, change.mine):
                change.their[HUNK_TYPE] = change.mine[HUNK_TYPE] = "!"
            result_changes.append(change)

        Differ2().difference(their_lines, base_lines, callback=collect_their_to_base)
        Differ2().difference(mine_lines, base_lines, callback=collect_mine_to_base)
        Differ2().difference(their_lines, mine_lines, callback=collect_their_to_mine)
        merged_hunks = []
        merged = []
        last_change = None
        last_text = None
        last_end = None
        whose = "mine"
        text = mine_original
        seq_number = 0
        result_changes = sort(result_changes, (lambda a, b: a.their[HUNK_BEGIN] - b.their[HUNK_BEGIN]))
        for change in result_changes:
            console.log(change)
            verify_conflict(change)
            align_hunks(change)
            if not change.is_conflict():
                if change.mine_base is None:
                    whose = "their"
                    text = their_original
                else:
                    whose = "mine"
                    text = mine_original
            else:
                change.their[HUNK_TYPE] = change.mine[HUNK_TYPE]
            change_line_begin = getattr(change, whose)[HUNK_BEGIN] - 1
            change_line_end = getattr(change, whose)[HUNK_BEGIN] if getattr(change, whose)[HUNK_END] == 0 else getattr(change, whose)[HUNK_END]
            if last_change is not None:
                if getattr(last_change, whose)[HUNK_END] == 0 and getattr(change, whose)[HUNK_END] == 0:
                    begin = getattr(last_change, whose)[HUNK_BEGIN]
                    end = getattr(change, whose)[HUNK_BEGIN] - 1
                elif getattr(last_change, whose)[HUNK_END] == 0:
                    begin = getattr(last_change, whose)[HUNK_BEGIN]
                    end = getattr(change, whose)[HUNK_BEGIN] - 1
                else:
                    begin = getattr(last_change, whose)[HUNK_END] + 1
                    end = getattr(change, whose)[HUNK_BEGIN] - 1
                merged += text[begin - 1:end]
            else:
                merged += text[0:change_line_begin]
            merged_lines = len(merged)
            hunk = getattr(change, whose)[:]
            if hunk[HUNK_END] > 0:
                hunk[HUNK_END] = merged_lines + (hunk[HUNK_END] - hunk[HUNK_BEGIN]) + 1
            hunk[HUNK_BEGIN] = merged_lines + 1
            if not change.is_conflict():
                if getattr(change, whose)[HUNK_END] != 0: # """decompile difference"""
                    merged += text[change_line_begin:change_line_end]
            else:
                hunk[HUNK_MISS] = max(change.their[HUNK_END] - change.their[HUNK_BEGIN], change.mine[HUNK_END] - change.mine[HUNK_BEGIN]) + 1
                hunk[HUNK_END] = 0
            merged_hunks.append(hunk)
            last_change = change
            last_text = text
            last_end = change_line_end
            callback(seq_number, change.their, change.base, change.mine)
            seq_number += 1

        off = 0
        their_original.pop()
        mine_original.pop()
        if last_change is not None:
            off = 1 if getattr(last_change, whose)[HUNK_END] == 0 else 0
            merged += last_text[last_end - off:]
        else:
            merged = mine_original[:]
        if merged and merged[-1]:
            their_nl = their_original[-1] == ""
            mine_nl = mine_original[-1] == ""
            merged_nl = merged[-1][-1] in ("\r", "\n")
            if their_nl != mine_nl and merged_nl:
                merged[-1] = merged[-1][:-1]
        callback_merged("".join(merged), merged_hunks)
        if callback_done is not None:
            callback_done()
