import os
import typing

import json5

import svg_combiner
import brute_force_permuter
from assembler_consts import *
from assembler_utils import *


class WirePoint:
    def __init__(self, wire: Wire, data: dict[str, ...]):
        self.wire = wire
        self.x = float(data["x"])
        self.y = float(data["y"])

    def __repr__(self):
        return f"WirePoint({self.wire!r}, x={self.x}, y={self.y})"

    def __str__(self):
        return f"{self.wire} at ({self.x}, {self.y})"


class WireSet:
    def __init__(self, typ: str, data: dict[str, ...]):
        self.type = typ
        definition = WIRE_TYPES[typ]
        self.gauge = Gauge(data.get("gauge", None))
        self.points = {
            wire: WirePoint(wire, data[wire.key])
            for wire in definition
        }
        self.wire_gauge_css_class: str | None = data.get("wire_gauge_css_class", None)

    def __repr__(self):
        return f"WireSet({self.type!r}, {self.gauge!r}, {self.points!r})"

    def __str__(self):
        return f"{self.type} wire set with {self.gauge} gauge: {', '.join(map(str, self.points))}"


class Part:
    def __init__(self, part_path: str):
        with open(os.path.join(BASE_PATH, "part_descriptions", part_path)) as f:
            part = json5.load(f)

        self.part_path = part_path

        self.wire_sets = [
            WireSet(typ, data)
            for typ, data in part["wire_sets"].items()
        ]

        self.svg = svg_combiner.SVG(str(os.path.join(BASE_PATH, "parts", part["file"])), debug_label=part_path.removesuffix(".json5"))

    def __repr__(self):
        return f"Part({self.part_path!r}, {self.wire_sets!r})"

    def __str__(self):
        return f"Part {self.part_path} with {len(self.wire_sets)} wire sets"

    def print_wire_sets_transformed(self, printer: DebugPrinter, x_offs: float, y_offs: float):
        for wire_set in self.wire_sets:
            printer.add(f"WireSet {wire_set.type} with {wire_set.gauge} gauge:")
            printer.as_child()
            for point in wire_set.points.values():
                printer.add(f"{point.wire} at ({point.x + x_offs}, {point.y + y_offs})")
            printer.as_parent()

    def __debug_print__(self, printer: DebugPrinter):
        printer.add(f"Part {self.part_path} with {len(self.wire_sets)} wire sets:")
        for wire_set in self.wire_sets:
            printer.print_child(wire_set)


class BundledConnection:
    def __init__(self, source: WireSet, target: WireSet, source_part: Part, target_part: Part):
        self.source = source
        self.target = target
        self.source_part = source_part
        self.target_part = target_part

        # we hold off on initializing these, because the parts won't be positioned yet at __init__ time
        self._source_offset: tuple[float, float] | None = None
        self._target_offset: tuple[float, float] | None = None

    @property
    def initialized(self) -> bool:
        return self._source_offset is not None and self._target_offset is not None

    def initialize(self):
        self._source_offset = (self.source_part.svg.x, self.source_part.svg.y)
        self._target_offset = (self.target_part.svg.x, self.target_part.svg.y)

    def _ensure_initialized(self):
        if not self.initialized:
            raise ValueError("Offsets not initialized")

    @property
    def source_offset(self) -> tuple[float, float]:
        self._ensure_initialized()
        return self._source_offset

    @property
    def target_offset(self) -> tuple[float, float]:
        self._ensure_initialized()
        return self._target_offset

    @property
    def gauge(self) -> Gauge:
        return self.source.gauge | self.target.gauge

    @property
    def inter_wire_spacing(self) -> float:
        return max(2.0, GAUGE_WIDTHS[self.gauge.value] * 0.5)

    def get_bundle_width(self) -> float:
        wire_count = len(self.source.points)
        return (GAUGE_WIDTHS[self.gauge.value] * wire_count
                + self.inter_wire_spacing * (wire_count - 1))

    def get_wires_to_draw(self) -> typing.Generator[tuple[WirePoint, WirePoint, float], None, None]:
        """Generate pairs of wire points and the track-relative offset to draw the vertical line
        """
        source_points = list(self.source.points.values())
        target_points = [self.target.points[v.wire] for v in source_points]
        connections = zip(source_points, target_points)

        # sort connections by the source point's y coordinate
        connections = sorted(connections, key=lambda c: -c[0].y)

        source_average_y = (sum(point.y for point in source_points) / len(source_points)) + self.source_offset[1]
        target_average_y = (sum(point.y for point in target_points) / len(target_points)) + self.target_offset[1]

        if target_average_y < source_average_y:
            connections = reversed(list(connections))

        for i, (source, target) in enumerate(connections):
            yield source, target, (i * (GAUGE_WIDTHS[self.gauge.value] + self.inter_wire_spacing))

    def _get_vertical_occupancy(self, wire_set: WireSet, offset: tuple[float, float]) -> Range:
        min_y = min(point.y for point in wire_set.points.values()) + offset[1]
        max_y = max(point.y for point in wire_set.points.values()) + offset[1]
        return Range(min_y, max_y).expand(GAUGE_WIDTHS[self.gauge.value] / 2)

    def get_source_vertical_occupancy(self) -> Range:
        self._ensure_initialized()
        return self._get_vertical_occupancy(self.source, self._source_offset)

    def get_target_vertical_occupancy(self) -> Range:
        self._ensure_initialized()
        return self._get_vertical_occupancy(self.target, self._target_offset)

    def get_vertical_occupancy(self) -> Range:
        return self.get_source_vertical_occupancy().expand_with(self.get_target_vertical_occupancy())

    def __str__(self):
        status = "initialized" if self.initialized else "uninitialized"
        return f"BundledConnection {{{self.source_part}}}->{{{self.target_part}}} [{{{self.source}}}->{{{self.target}}}] ({status})"

    def __repr__(self):
        return f"BundledConnection({self.source!r}, {self.target!r}, {self.source_part!r}, {self.target_part!r})"


class DrawingGroup:
    """A group of connections that have to be drawn together because they occupy overlapping 'rows' of the image"""
    def __init__(self):
        self.connections: list[BundledConnection] = []
        self._combined_vertical_occupancy: Range | None = None

    @property
    def combined_vertical_occupancy(self) -> Range:
        if self._combined_vertical_occupancy is None:
            return Range(0, 0, inclusive=False)
        return self._combined_vertical_occupancy

    @property
    def horizontal_width(self) -> float:
        return (sum(connection.get_bundle_width() for connection in self.connections)
                + INTER_TRACK_MARGIN * (len(self.connections) - 1))

    def add(self, connection: BundledConnection):
        self.connections.append(connection)
        if self._combined_vertical_occupancy is None:
            self._combined_vertical_occupancy = connection.get_vertical_occupancy()
        else:
            self._combined_vertical_occupancy.expand_with(connection.get_vertical_occupancy())

    def __str__(self):
        return f"DrawingGroup with {len(self.connections)} connections: {', '.join(map(str, self.connections))}"

    def __repr__(self):
        return f"DrawingGroup({self.connections!r})"

    def draw(self, multi: svg_combiner.MultiSVG, start_x: float):
        # tracks are interpreted as a list of connections from the source to the target
        def evaluator(tracks: list[BundledConnection]) -> float:
            collision_count = 0

            for i_, connection_ in enumerate(tracks):
                # count the number of collisions this connection will experience traveling from the source to the track
                source_occupancy = connection_.get_source_vertical_occupancy()
                for other_connection in tracks[:i_]:
                    if source_occupancy.overlaps(other_connection.get_vertical_occupancy()):
                        collision_count += 1

                # count the number of collisions this connection will experience traveling from the track to the target
                target_occupancy = connection_.get_target_vertical_occupancy()
                for other_connection in tracks[i_+1:]:
                    if target_occupancy.overlaps(other_connection.get_vertical_occupancy()):
                        collision_count += 1

            return -collision_count

        best_tracks = brute_force_permuter.find_best_permutation(set(self.connections), evaluator, good_enough=0)
        track_horizontal_positions = [0]
        for i, connection in enumerate(best_tracks[:-1]):
            track_horizontal_positions.append(track_horizontal_positions[i] + connection.get_bundle_width() + INTER_TRACK_MARGIN)

        # begin drawing connections
        for i in range(len(best_tracks)):
            track = best_tracks[i]
            track_horizontal_position = track_horizontal_positions[i]
            for (source, target, crossover_offset) in track.get_wires_to_draw():
                path = multi.add_path()
                path.style("stroke-width", track.gauge.gauge_width_style)
                path.style("stroke", f"#{source.wire.color:06x}")
                path.style("fill", "none")
                path.style("stroke-linejoin", "round")

                x0 = track.source_offset[0] + source.x
                y0 = track.source_offset[1] + source.y

                xm = start_x + track_horizontal_position + crossover_offset

                x1 = track.target_offset[0] + target.x
                y1 = track.target_offset[1] + target.y

                path.move_to(x0-1, y0)
                path.line_to(xm, y0)
                path.line_to(xm, y1)
                path.line_to(x1+1, y1)


class Assembly:
    def __init__(self, assembly_path: str):
        with open(os.path.join(BASE_PATH, "assemblies", assembly_path)) as f:
            assembly = json5.load(f)

        self.main = Part(assembly["main"])
        self.sockets = [Part(socket) for socket in assembly["sockets"]]
        self.bundled_connections: list[BundledConnection] = []

        # try to form connections to sockets for each wire set in the main part
        for main_wire_set in self.main.wire_sets:
            resolved = False

            for socket in self.sockets:
                for socket_wire_set in socket.wire_sets:
                    # don't link non-matching wire types - that's just silly
                    if main_wire_set.type != socket_wire_set.type:
                        continue

                    # the gauges should be the same (or one of them should be variable). Otherwise, visuals will be off
                    if main_wire_set.gauge != socket_wire_set.gauge:
                        raise ValueError(f"Wire set {main_wire_set} from main part does not match gauge of {socket_wire_set} from socket")

                    # in the case of a variable gauge, we need to provide the correct styling
                    if main_wire_set.wire_gauge_css_class is not None:
                        socket.svg.override_style(f".{main_wire_set.wire_gauge_css_class}", "stroke-width", main_wire_set.gauge.gauge_width_style)

                    self.bundled_connections.append(BundledConnection(main_wire_set, socket_wire_set, self.main, socket))
                    resolved = True
                    break

                # if we found a matching wire set, we don't need to check the other sockets
                if resolved:
                    break

            if not resolved:
                raise ValueError(f"Could not resolve wire set {main_wire_set} from main part to any socket")

    def write_svg(self, path: str):
        # position main part and sockets
        combined_sockets_height = sum(socket.svg.height for socket in self.sockets) + INTER_SOCKET_MARGIN * (len(self.sockets) - 1)
        overall_height = max(self.main.svg.height, combined_sockets_height)

        self.main.svg.x = MARGIN
        self.main.svg.y = int((overall_height / 2) - (self.main.svg.height / 2)) + MARGIN

        current_y = int((overall_height / 2) - (combined_sockets_height / 2))
        for socket in self.sockets:
            socket.svg.x = self.main.svg.width + PRELIMINARY_CONNECTION_TRACKS_WIDTH + MARGIN
            socket.svg.y = current_y + MARGIN
            current_y += socket.svg.height + INTER_SOCKET_MARGIN

        if DEBUG:
            # print transformed connections
            printer = DebugPrinter()
            printer.add("Transformed connections for main part:")
            printer.as_child()
            self.main.print_wire_sets_transformed(printer, self.main.svg.x, self.main.svg.y)
            printer.as_parent()
            printer.add("Transformed connections for sockets:")
            printer.as_child()
            for socket in self.sockets:
                printer.add(f"Socket {socket.part_path}:")
                printer.as_child()
                socket.print_wire_sets_transformed(printer, socket.svg.x, socket.svg.y)
                printer.as_parent()
            printer.as_parent()
            print(printer.out)

        multi = svg_combiner.MultiSVG(self.main.svg, *map(lambda p: p.svg, self.sockets))

        # initialize connection offsets so that we can start grouping connections that need to be de-crossed
        for connection in self.bundled_connections:
            connection.initialize()

        # sort connections by the start of their vertical occupancy
        self.bundled_connections.sort(key=lambda c: c.get_source_vertical_occupancy().min)

        # group connections that need to be drawn together
        drawing_groups: list[DrawingGroup] = []

        if self.bundled_connections:
            current_group = DrawingGroup()
            current_group.add(self.bundled_connections[0])

            # as long as the vertical occupancy of the current group overlaps with the next connection, add it to the group
            for connection in self.bundled_connections[1:]:
                if current_group.combined_vertical_occupancy.overlaps(connection.get_source_vertical_occupancy()):
                    current_group.add(connection)
                else:
                    drawing_groups.append(current_group)
                    current_group = DrawingGroup()
                    current_group.add(connection)

            drawing_groups.append(current_group)

        connection_tracks_width = max(group.horizontal_width for group in drawing_groups)
        for socket in self.sockets:
            socket.svg.x = self.main.svg.width + connection_tracks_width + 2*CONNECTION_TRACKS_MARGIN

        # reinitialize connection offsets so that we can draw them properly
        for connection in self.bundled_connections:
            connection.initialize()

        # now draw each group
        for group in drawing_groups:
            group.draw(multi, self.main.svg.x + self.main.svg.width + CONNECTION_TRACKS_MARGIN)

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
                x=int(self.main.svg.x + self.main.svg.width + CONNECTION_TRACKS_MARGIN), y=MARGIN,
                width=int(connection_tracks_width), height=height_tmp,
                fill="#00ff37"+alpha, stroke_width=0
            ))
            multi.add_highlight_rect(svg_combiner.Rect(
                x=int(self.main.svg.x + self.main.svg.width + connection_tracks_width + 2*CONNECTION_TRACKS_MARGIN), y=MARGIN,
                width=int(multi.width - (self.main.svg.x + self.main.svg.width + connection_tracks_width + 2*CONNECTION_TRACKS_MARGIN)), height=height_tmp,
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