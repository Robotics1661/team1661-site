import typing
from xml.dom import minidom
import random


#EXCEPTIONAL_CLASSES: set[str] = {
#    "cls-output-wire"
#}


def uniq() -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    numeric = "0123456789"
    if not hasattr(uniq, "past"):
        uniq.past = set()

    generated = None
    while generated is None or generated in uniq.past:
        generated = random.choice(alphabet) + "".join(random.choices(alphabet + numeric, k=7))
    return generated


class SVG:
    def __init__(self, path: str):
        with open(path) as f:
            raw = f.read()

        self._path = path
        self._doc = minidom.parseString(raw)
        svg_element = self._doc.getElementsByTagName("svg")[0]
        self._width = float(svg_element.getAttribute("width"))
        self._height = float(svg_element.getAttribute("height"))

        self.x = 0
        self.y = 0

        self._remapped_ids: dict[str, str] = {}
        self._remapped_classes: dict[str, str] = {}

        self._rewrite_ids()

        self._style_overrides: dict[str, dict[str, str]] = {}

    def override_style(self, selector: str, key: str, value: str):
        if selector.startswith("."):
            selector = "." + self._remapped_classes.get(selector[1:], selector[1:])
        elif selector.startswith("#"):
            selector = "#" + self._remapped_ids.get(selector[1:], selector[1:])
        if selector not in self._style_overrides:
            self._style_overrides[selector] = {}
        self._style_overrides[selector][key] = value

    def _rewrite_ids(self):
        # rewrite `id` and `class` attributes
        for element in self._doc.getElementsByTagName("*"):
            if element.hasAttribute("id"):
                old_id = element.getAttribute("id")
                if old_id in self._remapped_ids:
                    new_id = self._remapped_ids[old_id]
                else:
                    new_id = f"{uniq()}_{old_id}"
                    self._remapped_ids[old_id] = new_id
                element.setAttribute("id", new_id)
            if element.hasAttribute("class"):
                old_class = element.getAttribute("class")
#                if old_class in EXCEPTIONAL_CLASSES:
#                    continue
                if old_class in self._remapped_classes:
                    new_class = self._remapped_classes[old_class]
                else:
                    new_class = f"{uniq()}_{old_class}"
                    self._remapped_classes[old_class] = new_class
                element.setAttribute("class", new_class)

        # rewrite style elements
        for element in self._doc.getElementsByTagName("style"):
            self._rewrite_style(element)

    def _rewrite_style(self, element: minidom.Element):
        style = element.firstChild.nodeValue
        old_classes = sorted(self._remapped_classes.keys(), key=len, reverse=True)
        for old_class in old_classes:
            new_class = self._remapped_classes[old_class]
            style = style.replace(f".{old_class}", f".{new_class}")
        element.firstChild.nodeValue = style

    @property
    def doc(self) -> minidom.Document:
        doc = minidom.Document()
        # clone all elements from self._doc
        for element in self._doc.childNodes:
            doc.appendChild(element.cloneNode(deep=True))

        if self._style_overrides:
            svg = doc.getElementsByTagName("svg")[0]
            overridden_styles = doc.createElement("style")
            overridden_styles.setAttribute("id", "overridden_styles")
            style_text = "\n"
            for selector, properties in self._style_overrides.items():
                style_text += f"{selector} {{\n"
                for key, value in properties.items():
                    style_text += f"    {key}: {value} !important;\n"
                style_text += "}\n"
            overridden_styles.appendChild(doc.createTextNode(style_text))
            svg.appendChild(overridden_styles)

        return doc

    @property
    def width(self) -> float:
        return self._width

    @property
    def height(self) -> float:
        return self._height

    def write(self, file: typing.IO):
        file.write(self.doc.toprettyxml())

    def __repr__(self) -> str:
        return f"SVG(\"{self._path}\" {self.width}x{self.height})"


class Rect:
    def __init__(self, x: int, y: int, width: int, height: int, stroke: str = "black", stroke_width: int = 1, fill: str = "none"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.stroke = stroke
        self.stroke_width = stroke_width
        self.fill = fill

    def create_element(self, doc: minidom.Document) -> minidom.Element:
        rect = doc.createElement("rect")
        rect.setAttribute("x", str(self.x))
        rect.setAttribute("y", str(self.y))
        rect.setAttribute("width", str(self.width))
        rect.setAttribute("height", str(self.height))
        rect.setAttribute("stroke", self.stroke)
        rect.setAttribute("stroke-width", str(self.stroke_width))
        rect.setAttribute("fill", self.fill)
        return rect


class Path:
    def __init__(self):
        self._style = {}
        self._path = ""

    def style(self, key: str, value: str) -> "Path":
        self._style[key] = value
        return self

    def move_to(self, x: float, y: float) -> "Path":
        self._path += f"M{x},{y} "
        return self

    def move_to_rel(self, dx: float, dy: float) -> "Path":
        self._path += f"m{dx},{dy}"
        return self

    def line_to(self, x: float, y: float) -> "Path":
        self._path += f"L{x},{y}"
        return self

    def line_to_rel(self, dx: float, dy: float) -> "Path":
        self._path += f"l{dx},{dy}"
        return self

    def line_to_horiz(self, x: float) -> "Path":
        self._path += f"H{x}"
        return self

    def line_to_horiz_rel(self, dx: float) -> "Path":
        self._path += f"h{dx}"
        return self

    def line_to_vert(self, y: float) -> "Path":
        self._path += f"V{y}"
        return self

    def line_to_vert_rel(self, dy: float) -> "Path":
        self._path += f"v{dy}"
        return self

    def create_element(self, doc: minidom.Document) -> minidom.Element:
        el = doc.createElement("path")
        el.setAttribute("d", self._path)
        el.setAttribute("style", "; ".join(f"{k}:{v}" for k, v in self._style.items()))
        return el


class MultiSVG:
    def __init__(self, *svgs: SVG):
        self._svgs: list[SVG] = list(svgs)

        self._doc = minidom.Document()
        self._svg_element = self._doc.createElement("svg")
        # set up xmlns attributes
        self._svg_element.setAttribute("xmlns", "http://www.w3.org/2000/svg")
        self._svg_element.setAttribute("xmlns:svg", "http://www.w3.org/2000/svg")

        self._doc.appendChild(self._svg_element)

        self._highlight_rects: set[Rect] = set()
        self._paths: list[Path] = []

    def add_highlight_rect(self, rect: Rect):
        self._highlight_rects.add(rect)

    def remove_highlight_rect(self, rect: Rect):
        self._highlight_rects.remove(rect)

    def add_path(self) -> Path:
        p = Path()
        self._paths.append(p)
        return p

    @property
    def width(self) -> float:
        return max(
            0, *(svg.x + svg.width for svg in self._svgs),
            *(rect.x + rect.width for rect in self._highlight_rects)
        )

    @property
    def height(self) -> float:
        return max(
            0, *(svg.y + svg.height for svg in self._svgs),
            *(rect.y + rect.height for rect in self._highlight_rects)
        )

    @staticmethod
    def _clean(element: minidom.Element):
        # remove all sodipodi:* and inkscape:* elements and attributes
        for child in list(element.childNodes):
            if child.nodeType == minidom.Node.ELEMENT_NODE:
                child: minidom.Element
                if child.nodeName.startswith("sodipodi:") or child.nodeName.startswith("inkscape:"):
                    element.removeChild(child)
                else:
                    MultiSVG._clean(child)
        for attr in list(element.attributes.keys()):
            if attr.startswith("sodipodi:") or attr.startswith("inkscape:") or attr in {"xmlns:inkscape", "xmlns:sodipodi"}:
                element.removeAttribute(attr)

    def write(self, file: typing.IO, extra_width: float = 0, extra_height: float = 0):
        doc = minidom.Document()
        # clone all elements from self._doc
        for element in self._doc.childNodes:
            doc.appendChild(element.cloneNode(deep=True))

        svg_element = doc.getElementsByTagName("svg")[0]

        style_element = doc.createElement("style")
        svg_element.appendChild(style_element)
        style_element.appendChild(doc.createTextNode("svg{overflow:visible;}"))

        width = 0.0
        height = 0.0

        for rect in self._highlight_rects:
            svg_element.appendChild(rect.create_element(doc))
            width = max(width, rect.x + rect.width)
            height = max(height, rect.y + rect.height)

        width += extra_width
        height += extra_height

        for path in self._paths:
            svg_element.appendChild(path.create_element(doc))

        for svg in self._svgs:
            # create wrapper group
            group = doc.createElement("g")
            group.setAttribute("transform", f"translate({svg.x}, {svg.y})")
            # clone all elements from svg.doc
            for element in svg.doc.childNodes:
                group.appendChild(element.cloneNode(deep=True))
            svg_element.appendChild(group)

            width = max(width, svg.x + svg.width)
            height = max(height, svg.y + svg.height)

        svg_element.setAttribute("width", str(width))
        svg_element.setAttribute("height", str(height))

        for element in doc.childNodes:
            MultiSVG._clean(element)

        doc.normalize()

        file.write(doc.toprettyxml())


"""
def combine(path_a: str, path_b: str, out_path: str):
    with open(path_a) as a_file:
        a_raw = a_file.read()
    with open(path_b) as b_file:
        b_raw = b_file.read()

    a = minidom.parseString(a_raw)
    b = minidom.parseString(b_raw)

    return a
"""
