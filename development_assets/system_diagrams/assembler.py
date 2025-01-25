import os
import json5

import svg_combiner

DEBUG = False

MARGIN = 20
CONNECTION_MARGIN = 100
INTER_SOCKET_MARGIN = 60
BASE_PATH = "assets"
OUTPUT_PATH = "output"
GAUGE_WIDTHS: dict[int, int] = {
    12: 15,
    22: 2
}


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


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


def debug_print(obj):
    printer = DebugPrinter()
    obj.__debug_print__(printer)
    print(printer.out)


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


CONNECTION_TYPES: dict[str, tuple[Wire, ...]] = {
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


class Assembly:
    def __init__(self, assembly_path: str):
        with open(os.path.join(BASE_PATH, "assemblies", assembly_path)) as f:
            assembly = json5.load(f)

        self.main = Part(assembly["main"])
        self.sockets = [Part(socket) for socket in assembly["sockets"]]
        self.wire_alignments: dict[str, float] = assembly.get("wire_alignments", {})
        self.wire_offsets: dict[str, int] = assembly.get("wire_offsets", {})

        # try to resolve connections from main part to sockets
        for connection in self.main.connections:
            resolved = False
            for socket in self.sockets:
                for socket_connection in socket.connections:
                    if connection.typ == socket_connection.typ and connection.gauge == socket_connection.gauge:
                        connection.targeted_part = socket
                        connection.targeted_connection = socket_connection
                        if connection.wire_gauge_css_class is not None:
                            socket.svg.override_style(f".{connection.wire_gauge_css_class}", "stroke-width", connection.gauge.gauge_width_style)
                        resolved = True
                        break
                if resolved:
                    break
            if not resolved:
                raise ValueError(f"Could not resolve connection {connection} from main part to any socket")

    def write_svg(self, path: str):
        # align main part and sockets
        combined_sockets_height = sum(socket.svg.height for socket in self.sockets) + INTER_SOCKET_MARGIN * (len(self.sockets) - 1)
        overall_height = max(self.main.svg.height, combined_sockets_height)

        self.main.svg.x = MARGIN
        self.main.svg.y = int((overall_height / 2) - (self.main.svg.height / 2)) + MARGIN

        current_y = int((overall_height / 2) - (combined_sockets_height / 2))
        for socket in self.sockets:
            socket.svg.x = self.main.svg.width + CONNECTION_MARGIN + MARGIN
            socket.svg.y = current_y + MARGIN
            current_y += socket.svg.height + INTER_SOCKET_MARGIN

        if DEBUG:
            # print transformed connections
            printer = DebugPrinter()
            printer.add("Transformed connections for main part:")
            printer.as_child()
            self.main.print_connections_transformed(printer, self.main.svg.x, self.main.svg.y)
            printer.as_parent()
            printer.add("Transformed connections for sockets:")
            printer.as_child()
            for socket in self.sockets:
                printer.add(f"Socket {socket.part_path}:")
                printer.as_child()
                socket.print_connections_transformed(printer, socket.svg.x, socket.svg.y)
                printer.as_parent()
            printer.as_parent()
            print(printer.out)

        multi = svg_combiner.MultiSVG(self.main.svg, *map(lambda p: p.svg, self.sockets))

        # connecting wires
        for connection in self.main.connections:
            for point in connection.points.values():
                target_point = connection.targeted_connection.points[point.wire]
                point.draw_path_to(
                    target_point,
                    (self.main.svg.x, self.main.svg.y),
                    (connection.targeted_part.svg.x, connection.targeted_part.svg.y),
                    multi,
                    connection.gauge | connection.targeted_connection.gauge,
                    self.wire_alignments.get(connection.typ, 0.5),
                    self.wire_offsets.get(connection.typ, 0)
                )

        if DEBUG:
            # add debug rectangles
            alpha = "60"
            height_tmp = int(multi.height)
            multi.add_highlight_rect(svg_combiner.Rect(
                x=self.main.svg.x, y=MARGIN,
                width=int(self.main.svg.width), height=height_tmp,
                fill="#00aaff"+alpha, stroke_width=0
            ))
            multi.add_highlight_rect(svg_combiner.Rect(
                x=int(self.main.svg.x + self.main.svg.width), y=MARGIN,
                width=CONNECTION_MARGIN, height=height_tmp,
                fill="#00ff37"+alpha, stroke_width=0
            ))
            multi.add_highlight_rect(svg_combiner.Rect(
                x=int(self.main.svg.x + self.main.svg.width + CONNECTION_MARGIN), y=MARGIN,
                width=int(multi.width - (self.main.svg.x + self.main.svg.width + CONNECTION_MARGIN)), height=height_tmp,
                fill="#ffaa00"+alpha, stroke_width=0
            ))

        with open(path, "w") as f:
            multi.write(f, extra_width=MARGIN, extra_height=MARGIN)

    def __repr__(self):
        return f"Assembly({self.main!r}, {self.sockets!r})"

    def __str__(self):
        mapper = lambda v: f"{{{v}}}"
        return f"Assembly with main part {{{self.main}}} and sockets: {', '.join(map(mapper, self.sockets))}"

    def __debug_print__(self, printer: DebugPrinter):
        printer.add("Assembly with main part:")
        printer.print_child(self.main)
        printer.add("Sockets:")
        for socket in self.sockets:
            printer.print_child(socket)


class ConnectionPoint:
    def __init__(self, wire: Wire, data: dict[str, ...]):
        self.wire = wire
        self.x = float(data["x"])
        self.y = float(data["y"])

    def __repr__(self):
        return f"ConnectionPoint({self.wire!r}, x={self.x}, y={self.y})"

    def __str__(self):
        return f"{self.wire} at ({self.x}, {self.y})"

    def draw_path_to(
            self,
            target_point: "ConnectionPoint",
            my_offset: tuple[float, float],
            other_offset: tuple[float, float],
            multi: svg_combiner.MultiSVG,
            gauge: Gauge,
            alignment: float,
            wire_offset: int
    ):
        path = multi.add_path()
        path.style("stroke-width", gauge.gauge_width_style)
        path.style("stroke", f"#{self.wire.color:06x}")
        path.style("fill", "none")
        path.style("stroke-linejoin", "round")

        x0, y0 = self.x + my_offset[0], self.y + my_offset[1]
        x1, y1 = target_point.x + other_offset[0], target_point.y + other_offset[1]

        offset = -1 if x0 > x1 else 1

        xm = lerp(x0, x1, alignment)
        xm += wire_offset * GAUGE_WIDTHS[gauge.value] * self.wire.idx * 2

        path.move_to(x0-offset, y0)
        path.line_to(xm, y0)
        path.line_to(xm, y1)
        path.line_to(x1+offset, y1)


class Connection:
    def __init__(self, typ: str, data: dict[str, ...]):
        self.typ = typ
        definition = CONNECTION_TYPES[typ]
        self.gauge = Gauge(data.get("gauge", None))
        self.points = {
            wire: ConnectionPoint(wire, data[wire.key])
            for wire in definition
        }
        self.wire_gauge_css_class: str | None = data.get("wire_gauge_css_class", None)
        self.targeted_part: Part | None = None
        self.targeted_connection: Connection | None = None

    def __repr__(self):
        return f"Connection({self.typ!r}, {self.gauge!r}, {self.points!r})"

    def __str__(self):
        return f"{self.typ} connection with {self.gauge} gauge: {', '.join(map(str, self.points))}"


class Part:
    def __init__(self, part_path: str):
        with open(os.path.join(BASE_PATH, "part_descriptions", part_path)) as f:
            part = json5.load(f)

        self.part_path = part_path

        self.connections = [
            Connection(typ, data)
            for typ, data in part["wire_connections"].items()
        ]

        self.svg = svg_combiner.SVG(os.path.join(BASE_PATH, "parts", part["file"]))

    def __repr__(self):
        return f"Part({self.part_path!r}, {self.connections!r})"

    def __str__(self):
        return f"Part {self.part_path} with {len(self.connections)} connections"

    def print_connections_transformed(self, printer: DebugPrinter, x_offs: float, y_offs: float):
        for connection in self.connections:
            printer.add(f"Connection {connection.typ} with {connection.gauge} gauge:")
            printer.as_child()
            for point in connection.points.values():
                printer.add(f"{point.wire} at ({point.x + x_offs}, {point.y + y_offs})")
            printer.as_parent()

    def __debug_print__(self, printer: DebugPrinter):
        printer.add(f"Part {self.part_path} with {len(self.connections)} connections:")
        for connection in self.connections:
            printer.print_child(connection)


def main():
    for assembly_path in os.listdir(os.path.join(BASE_PATH, "assemblies")):
        if assembly_path.endswith(".json5"):
            assembly = Assembly(assembly_path)
            print("\t"+str(assembly))
            out_path = os.path.join(OUTPUT_PATH, assembly_path.replace(".json5", ".svg"))
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            assembly.write_svg(out_path)


if __name__ == "__main__":
    main()