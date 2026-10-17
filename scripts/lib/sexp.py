"""Minimal S-expression reader for KiCad files.

Stdlib only and Python 3.9 compatible, so it runs under KiCad's bundled
Python as well as a normal python3. Atoms are returned as `Atom` (bare) or
`str` (quoted) so callers can tell `(layer F.Cu)` from `(layer "F.Cu")` if
they need to; most callers just compare with ==.
"""

from typing import List, Union


class Atom(str):
    """A bare (unquoted) token."""


Node = Union[str, List["Node"]]


def parse(text: str) -> List[Node]:
    """Parse all top-level expressions in `text`."""
    stack: List[List[Node]] = [[]]
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "(":
            stack.append([])
            i += 1
        elif c == ")":
            if len(stack) == 1:
                raise ValueError(f"unbalanced ')' at offset {i}")
            done = stack.pop()
            stack[-1].append(done)
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    nxt = text[j + 1]
                    buf.append({"n": "\n", "t": "\t", "r": "\r"}.get(nxt, nxt))
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            if j >= n:
                raise ValueError(f"unterminated string at offset {i}")
            stack[-1].append("".join(buf))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()"':
                j += 1
            stack[-1].append(Atom(text[i:j]))
            i = j
    if len(stack) != 1:
        raise ValueError("unbalanced '(' at end of input")
    return stack[0]


def load(path) -> Node:
    """Parse a file that contains exactly one top-level expression."""
    with open(path, encoding="utf-8") as f:
        exprs = parse(f.read())
    if len(exprs) != 1:
        raise ValueError(f"{path}: expected one top-level expression, got {len(exprs)}")
    return exprs[0]


def head(node: Node) -> str:
    return node[0] if isinstance(node, list) and node else ""


def children(node: Node, name: str) -> List[List[Node]]:
    """Direct children of `node` whose head is `name`."""
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def child(node: Node, name: str):
    """First direct child with head `name`, or None."""
    for c in node:
        if isinstance(c, list) and c and c[0] == name:
            return c
    return None


def walk(node: Node, path=()):
    """Yield (path, list_node) for every list in the tree, depth first.

    `path` is the tuple of heads from the root down to (excluding) the node.
    """
    if isinstance(node, list):
        yield path, node
        sub = path + (head(node),)
        for c in node[1:]:
            yield from walk(c, sub)


def _atom(a):
    if isinstance(a, Atom):
        return str(a)
    return '"%s"' % a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def dump_lines(node, indent=0):
    """Serialize `node` as lines: one line per list whose children are all atoms."""
    pad = "  " * indent
    if not isinstance(node, list):
        return [pad + _atom(node)]
    atoms = [c for c in node if not isinstance(c, list)]
    lists = [c for c in node if isinstance(c, list)]
    head = "(" + " ".join(_atom(a) for a in atoms)
    if not lists:
        return [pad + head + ")"]
    out = [pad + head]
    for c in lists:
        out += dump_lines(c, indent + 1)
    return out + [pad + ")"]
