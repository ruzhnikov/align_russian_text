"""выровнять русский текст по обоим краям для текстового терминала,
с переносами, без словаря (правилам русского языка следовать насколько возможно, без фанатизма)

в общем когда-то использовал такую эмирику (всех деталей уже не помню):
- перенос ставим между двумя гласными
- одну букву не оставляем и не перенсим
- ь, ъ, ы, й за буквы не считаем и клеим к предыдущей
- ст, ск считаем за одну букву (согласную) (кажется я больше сочетаний находил, но для алгоритмики и двух хватит, без фанатизма)
- согласные разрываем или на двойной или посередине.
- для нечетного числа согласных лишня согласная остается идет на следующую строку.
"""


import sys
import argparse
from typing import Deque, List
from collections import deque
from dataclasses import dataclass
from functools import reduce
from enum import Enum


VOWELS = "аиеёоуыэюяАИЕЁОУЫЭЮЯ"
CONSONANTS = "бвгджзклмнпрстфхцчшщБВГДЖЗКЛМНПРСТФХЦЧШЩ"
SPEC_LETTERS = "ьъйЬЪЙ"
ALPHABET = "".join(x for x in (x for x in (VOWELS, CONSONANTS, SPEC_LETTERS)))
SET_VOWELS = set(VOWELS)
SET_CONSONANT = set(CONSONANTS)

MIN_TERM_SIZE = 20
MIN_WORD_LEN = 4
DEFAULT_PIVOT = -1
DEFAULT_TERM_SIZE = 80


class WorkMode(Enum):
    TEXT = 0
    WORD = 1


# all gramatic rules taken from https://rosuchebnik.ru/material/pravila-perenosa-slov-v-russkom-yazyke-nachalka/


def vowels_and_consonats(left: List[str], right: List[str]) -> bool:
    for part in (left, right):
        set_part = set(part)
        check_res = SET_VOWELS.intersection(set_part) and SET_CONSONANT.intersection(set_part)
        if not check_res:
            return False

    return True


def special_symbols(left: List[str], right: List[str]) -> bool:
    if right[0].lower() == "ы":
        return False

    if right[0].lower() in SPEC_LETTERS:
        return False

    return True


def common_symbols(left: List[str], right: List[str]) -> bool:
    # двойная согласная. Разрешено. Например, пропел-лер
    if left[-1] in CONSONANTS and left[-1] == right[0]:
        return True

    # две согласных подряд. Разрешено. Например, прос-мотр
    if left[-1] in CONSONANTS and right[0] in CONSONANTS:
        return True

    # двойная согласная в одной из частей. Запрещено. Например, су-ббота
    if left[-1] in CONSONANTS and left[-2] == left[-1]:
        return False

    if right[0] in CONSONANTS and right[1] == right[0]:
        return False

    # нельзя отрывать гласную от согласной. Например, пол-ено
    if left[-1] in CONSONANTS and right[0] in VOWELS:
        return False

    return True


GRAMMATICAL_RULES = {
    f"длина слова >= {MIN_WORD_LEN}": (lambda left, right: len(left + right) >= MIN_WORD_LEN),
    "гласные и согласные в обеих частях слова": vowels_and_consonats,
    "мягкий, твёрдый и 'й краткая'": special_symbols,
    "общие правила": common_symbols
}


def _can_be_hyphenated(left: List[str], right: List[str]) -> bool:
    return reduce(
        (lambda res, rule: res and rule(left, right)),
        GRAMMATICAL_RULES.values(), True)


class WordHandler:
    def __init__(self) -> None:
        self.buffer = []

    def _clean_up(self):
        self.buffer[:] = []

    def _write(self):
        print("".join(self.buffer))

    def _hyphenation(self, pivot: int) -> List[int]:
        result = []

        while pivot >= 2:
            left = self.buffer[0:pivot]
            right = self.buffer[pivot:]

            if _can_be_hyphenated(left, right):
                result.append(pivot)

            pivot -= 1

        return result

    def _handle(self):
        if len(self.buffer) == 0:
            return

        pivot = len(self.buffer) - 2
        hyphens = self._hyphenation(pivot)

        for hyphen in hyphens:
            self.buffer = self.buffer[0:hyphen] + ['-'] + self.buffer[hyphen:]

        self._write()
        self._clean_up()

    def work(self, ch: str):
        if ch in ALPHABET:
            self.buffer.append(ch)
            return

        self._handle()

    def eof(self):
        self._handle()


@dataclass
class TextHyphenator:
    buffer: List[str]
    tmp_buf: Deque
    pivot: int
    word_begin: int = -1

    def work(self):
        self._calc_word_begin()

        can_be_hyphenated = False
        while (self.pivot - self.word_begin) > 1:
            left = self.buffer[self.word_begin:self.pivot]
            right = self.buffer[self.pivot:]

            can_be_hyphenated = _can_be_hyphenated(left, right)
            if can_be_hyphenated:
                break

            self.pivot -= 1

        if can_be_hyphenated:
            self._hyphenate()
        else:
            self._move_whole_word()

    def _calc_word_begin(self):
        word_begin = -1

        for i in range(self.pivot, -1, -1):
            if self.buffer[i] not in ALPHABET:
                word_begin = i + 1
                break

        assert word_begin != -1
        self.word_begin = word_begin

    def _append_tmp_buffer(self, data: List[str]):
        data.reverse()
        self.tmp_buf.extendleft(data)

    def _move_whole_word(self):
        self._append_tmp_buffer(self.buffer[self.word_begin:])
        self.buffer[self.word_begin:] = []

    def _hyphenate(self):
        self._append_tmp_buffer(self.buffer[self.pivot:])
        self.buffer[self.pivot:] = []
        self.buffer.append("-")


class TextHandler:
    def __init__(self, term_size: int):
        self.term_size = term_size
        self.buffer = []
        self.tmp_buf = deque()
        self.pivot = DEFAULT_PIVOT
        self.need_to_write = False

    @property
    def enough_space(self) -> bool:
        return len(self.buffer) < self.term_size

    def _write(self):
        print("".join(self.buffer))

    def _clean_up(self):
        self.buffer[:] = []
        self.buffer.extend(self.tmp_buf)
        self.tmp_buf.clear()
        self.need_to_write = False
        self.pivot = DEFAULT_PIVOT

    def _decide_what_to_do(self, ch: str):
        if ch in ALPHABET:
            if self.pivot == DEFAULT_PIVOT:
                self.pivot = len(self.buffer) - 1
            self.buffer.append(ch)
            return

        if self.pivot == DEFAULT_PIVOT:
            if not ch.isspace():
                self.buffer.append(ch)
            self.need_to_write = True
            return

        self.tmp_buf.append(ch)

        TextHyphenator(self.buffer, self.tmp_buf, self.pivot).work()
        self.need_to_write = True

    def _handle_char(self, ch):
        if self.enough_space:
            self.buffer.append(ch)
            return

        self._decide_what_to_do(ch)

        if self.need_to_write:
            self._write()
            self._clean_up()

    def work(self, ch: str):
        self._handle_char(ch)

    def eof(self):
        if not self.buffer:
            return

        if self.enough_space:
            self._write()
            return

        self._handle_char('')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--term_size', type=int, help="Terminal size")
    parser.add_argument('-m', '--work_mode', type=int, default=0, help="Work mode. 0 - text mode, 1 - word mode")
    args = parser.parse_args()

    term_size = args.term_size if args.term_size else DEFAULT_TERM_SIZE
    if term_size < MIN_TERM_SIZE:
        raise Exception(f"The term size has to be at least {MIN_TERM_SIZE}")

    work_mode = WorkMode.WORD if args.work_mode == 1 else WorkMode.TEXT

    if work_mode == WorkMode.TEXT:
        h = TextHandler(term_size)
    else:
        h = WordHandler()

    for line in sys.stdin:
        for ch in line:
            if ch == "\n":
                ch = " "
            h.work(ch)

    h.eof()
