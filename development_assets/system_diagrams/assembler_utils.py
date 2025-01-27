__all__ = ["DebugPrinter", "Range", "RangeSet", "Gauge", "Wire", "debug_print", "lerp", "WIRE_TYPES"]

from assembler_consts import *


class DebugPrinter:
    def __init__(self):
        self._indent = 0
        self._out = ""

    @property
    def out(self) -> str:
        return self._out

    def add(self, text: str):
        self._out += "  " * self._indent + text + "\n"

    def as_child(self):
        self._indent += 1

    def as_parent(self):
        self._indent -= 1

    def print_child(self, child):
        self.as_child()
        if hasattr(child, "__debug_print__"):
            child.__debug_print__(self)
        else:
            self.add(str(child))
        self.as_parent()


class Range:
    def __init__(self, min_: float, max_: float, inclusive: bool = True):
        self._min = min_
        self._max = max_
        self._inclusive = inclusive

    @property
    def min(self) -> float: return self._min

    @property
    def max(self) -> float: return self._max

    @property
    def inclusive(self) -> bool: return self._inclusive

    def __contains__(self, item: float) -> bool:
        if self.inclusive:
            return self.min <= item <= self.max
        else:
            return self.min < item < self.max

    def __repr__(self) -> str:
        return f"Range({self.min}, {self.max}, inclusive={self.inclusive})"

    def __str__(self):
        open_bracket = "[" if self.inclusive else "("
        close_bracket = "]" if self.inclusive else ")"
        return f"Range{open_bracket}{self.min}, {self.max}{close_bracket}"

    def __add__(self, other: 'Range|RangeSet') -> 'RangeSet':
        if isinstance(other, Range):
            return RangeSet(self, other)
        elif isinstance(other, RangeSet):
            return RangeSet(self, *other.ranges)
        else:
            raise ValueError(f"Unsupported type: {type(other)}")

    def __radd__(self, other: 'Range|RangeSet') -> 'RangeSet':
        return self + other

    def overlaps(self, other: 'Range') -> bool:
        if self.min == self.max and not self.inclusive:
            return False
        return self.min < other.max and self.max > other.min

    def offset(self, offset: float) -> 'Range':
        return Range(self.min + offset, self.max + offset, self.inclusive)

    def expand(self, amount: float) -> 'Range':
        return Range(self.min - amount, self.max + amount, self.inclusive)

    def expand_with(self, other: 'Range') -> 'Range':
        return Range(min(self.min, other.min), max(self.max, other.max), self.inclusive or other.inclusive)


class RangeSet:
    def __init__(self, *ranges: Range):
        self.ranges: list[Range] = list(ranges)
        self.condense()

    def __iadd__(self, other: 'Range|RangeSet') -> 'RangeSet':
        if isinstance(other, Range):
            self.ranges.append(other)
        elif isinstance(other, RangeSet):
            self.ranges.extend(other.ranges)
        else:
            raise ValueError(f"Unsupported type: {type(other)}")
        self.condense()
        return self

    def condense(self):
        self.ranges.sort(key=lambda r: r.min)
        i = 0
        while i < len(self.ranges) - 1:
            if self.ranges[i].overlaps(self.ranges[i+1]):
                self.ranges[i] = Range(self.ranges[i].min, self.ranges[i+1].max)
                del self.ranges[i+1]
            else:
                i += 1

    def __contains__(self, item: float) -> bool:
        return any(item in r for r in self.ranges)

    def offset(self, offset: float) -> 'RangeSet':
        return RangeSet(*(r.offset(offset) for r in self.ranges))

    def __repr__(self) -> str:
        return f"RangeSet({', '.join(repr(r) for r in self.ranges)})"

    def __str__(self) -> str:
        return f"RangeSet( {' U '.join(str(r) for r in self.ranges)} )"


class Gauge:
    def __init__(self, value: int | str | None):
        if type(value) == str:
            if value == "*":
                self.value = None
            else:
                self.value = int(value)
        else:
            self.value = value

    @property
    def gauge_width_style(self) -> str:
        return f"{GAUGE_WIDTHS[self.value]}px !important"

    def __repr__(self):
        return f"Gauge({self.value})"

    def __str__(self):
        if self.value is None:
            return "*"
        else:
            return str(self.value)

    def __eq__(self, other):
        if self.value is other:
            return True
        elif isinstance(other, Gauge):
            return self.value is None or other.value is None or self.value == other.value
        else:
            return False

    def __ne__(self, other):
        return not self == other

    def __or__(self, other):
        if self.value is None:
            return other
        else:
            return self


class Wire:
    def __init__(self, typ: str, key: str, color: int, idx: int):
        self.type = typ
        self.key = key
        self.color = color
        self.idx = idx

    def __repr__(self):
        return f"Wire(\"{self.type}\", \"{self.key}\", 0x{self.color:06x})"

    def __str__(self):
        return f"{self.key} {self.type} wire ({self.color:06x})"

    def __hash__(self):
        return hash(self.key) ^ hash(self.type)

    def __eq__(self, other):
        return self is other or isinstance(other, Wire) and self.type == other.type and self.key == other.key


def debug_print(obj):
    printer = DebugPrinter()
    obj.__debug_print__(printer)
    print(printer.out)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


WIRE_TYPES: dict[str, tuple[Wire, ...]] = {
    v[0].type: v
    for v in [
        (
            Wire("power", "red", 0xe6282b, 0),
            Wire("power", "black", 0x231f20, 1)),
        (
            Wire("can_a", "yellow", 0xd5dc28, 0),
            Wire("can_a", "green", 0x37b04a, 1)),
        (
            Wire("can_b", "yellow", 0xd5dc28, 0),
            Wire("can_b", "green", 0x37b04a, 1)), ]
}