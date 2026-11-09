#!/usr/bin/env python3
"""Generate Markdown API documentation from binding/lvgl.pyi.

This mirrors MaixPy's build-time documentation flow (components/maix/gen_api.py
-> docs/api/maix): ``setup.py`` runs this script after the binding is
generated, and the output under ``docs/api/maix_lvgl/`` is a build artifact
(not tracked in git).
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Method:
    name: str
    signature: str


@dataclass
class Field:
    name: str
    type: str


@dataclass
class Class:
    name: str
    bases: list[str] = field(default_factory=list)
    methods: list[Method] = field(default_factory=list)
    fields: list[Field] = field(default_factory=list)
    nested: list["Class"] = field(default_factory=list)


def _strip_trailer(text: str) -> str:
    text = re.sub(r"\s*:\s*\.\.\.\s*$", "", text.strip())
    return re.sub(r"\s+", " ", text)


def _logical_lines(text: str) -> list[str]:
    """Join def/class continuation lines while parentheses are unbalanced."""
    lines: list[str] = []
    buf = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        buf = line if not buf else buf + " " + line.strip()
        stripped = buf.lstrip()
        if stripped.startswith(("def ", "class ")) and buf.count("(") > buf.count(")"):
            continue
        lines.append(buf)
        buf = ""
    if buf:
        lines.append(buf)
    return lines


def parse_pyi(text: str):
    classes: list[Class] = []
    functions: list[Method] = []
    variables: list[Field] = []
    current: Class | None = None
    nested: Class | None = None

    for line in _logical_lines(text):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "from ", "import ")):
            continue
        indent = len(line) - len(line.lstrip())

        class_match = re.match(r"class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:", stripped)
        def_match = re.match(r"def\s+(\w+)\s*\((.*)\)\s*(?:->\s*(.*?))?\s*:\s*\.\.\.", stripped)
        field_match = re.match(r"(\w+)\s*:\s*(.+)", stripped)

        if indent == 0:
            nested = None
            if class_match:
                bases = [b.strip() for b in (class_match.group(2) or "").split(",") if b.strip()]
                current = Class(class_match.group(1), bases)
                classes.append(current)
                continue
            if def_match:
                functions.append(Method(def_match.group(1), _strip_trailer(stripped)))
                current = None
                continue
            if field_match:
                variables.append(Field(field_match.group(1), _strip_trailer(field_match.group(2))))
            continue

        if current is None:
            continue

        if indent == 4:
            if class_match:
                bases = [b.strip() for b in (class_match.group(2) or "").split(",") if b.strip()]
                nested = Class(class_match.group(1), bases)
                current.nested.append(nested)
                continue
            nested = None
            if def_match:
                current.methods.append(Method(def_match.group(1), _strip_trailer(stripped)))
                continue
            if field_match:
                current.fields.append(Field(field_match.group(1), _strip_trailer(field_match.group(2))))
            continue

        target = nested if nested is not None else current
        if def_match:
            target.methods.append(Method(def_match.group(1), _strip_trailer(stripped)))
        elif field_match:
            target.fields.append(Field(field_match.group(1), _strip_trailer(field_match.group(2))))

    return classes, functions, variables


def classify(cls: Class) -> str:
    name = cls.name
    bases = " ".join(cls.bases)
    if "Exception" in bases or (name.startswith("_") and name not in ("_Struct",)):
        return "skip"
    if name == "_Struct":
        return "skip"
    if cls.methods:
        return "class"
    if (
        cls.fields
        and not cls.nested
        and all(re.fullmatch(r"(ClassVar\[)?int(\])?", f.type.strip()) for f in cls.fields)
    ):
        return "enum"
    if "_Struct" in bases or name.endswith("_t") or cls.fields:
        return "struct"
    return "class"


def _front_matter(title: str) -> str:
    return f"---\ntitle: {title}\n---\n\n"


def _func_markdown(method: Method, level: int = "###") -> str:
    return f"{level} `{method.name}`\n\n```python\n{method.signature}\n```\n\n"


def _class_markdown(cls: Class, kind: str) -> str:
    bases = f"({', '.join(cls.bases)})" if cls.bases else ""
    out = [f"### {kind} {cls.name}{bases}\n"]
    if cls.fields:
        out.append("\n**Fields**\n\n")
        for f in cls.fields:
            out.append(f"- `{f.name}`: `{f.type}`\n")
        out.append("\n")
    if cls.nested:
        for nested in cls.nested:
            out.append(f"\n#### enum {cls.name}.{nested.name}\n\n")
            for f in nested.fields:
                out.append(f"- `{f.name}`: `{f.type}`\n")
            if nested.methods:
                out.append("\n")
                for m in nested.methods:
                    out.append(f"```python\n{m.signature}\n```\n\n")
    if cls.methods:
        out.append("\n**Methods**\n\n")
        for m in cls.methods:
            out.append(f"```python\n{m.signature}\n```\n\n")
    return "".join(out)


def generate(pyi_path: Path, out_dir: Path) -> None:
    classes, functions, variables = parse_pyi(pyi_path.read_text(encoding="utf-8"))

    grouped: dict[str, list[Class]] = {"class": [], "enum": [], "struct": [], "skip": []}
    for cls in classes:
        grouped[classify(cls)].append(cls)

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.md"):
        old.unlink()
    sidebar = out_dir / "sidebar.yaml"
    if sidebar.exists():
        sidebar.unlink()

    # lvgl.md: module-level functions and variables
    lvgl = [_front_matter("maix_lvgl.lvgl")]
    lvgl.append(
        "# lvgl\n\n"
        "Generated CPython bindings for LVGL 9.1.0 (the version pinned by\n"
        "MaixCDK), produced from MaixCDK's LVGL source with the\n"
        "[omnipython-lvgl](https://github.com/PyDevices/omnipython-lvgl) generator.\n\n"
        f"- Functions: {len(functions)}\n"
        f"- Classes: {len(grouped['class'])}\n"
        f"- Enums: {len(grouped['enum'])}\n"
        f"- Structs: {len(grouped['struct'])}\n"
        f"- Module variables: {len(variables)}\n\n"
        "See also: [classes](classes.md), [enums](enums.md), "
        "[structs](structs.md), [maix_lvgl backend](maix_lvgl.md).\n\n"
    )
    lvgl.append("## Functions\n\n")
    for func in sorted(functions, key=lambda m: m.name):
        lvgl.append(_func_markdown(func))
    lvgl.append("## Variables\n\n")
    for var in sorted(variables, key=lambda f: f.name):
        lvgl.append(f"- `{var.name}`: `{var.type}`\n")
    (out_dir / "lvgl.md").write_text("".join(lvgl), encoding="utf-8")

    # classes.md
    classes_md = [_front_matter("maix_lvgl.classes")]
    classes_md.append("# Classes\n\n")
    for cls in sorted(grouped["class"], key=lambda c: c.name):
        classes_md.append(_class_markdown(cls, "class"))
    (out_dir / "classes.md").write_text("".join(classes_md), encoding="utf-8")

    # enums.md
    enums_md = [_front_matter("maix_lvgl.enums")]
    enums_md.append("# Enums and constants\n\n")
    for cls in sorted(grouped["enum"], key=lambda c: c.name):
        enums_md.append(_class_markdown(cls, "enum"))
    (out_dir / "enums.md").write_text("".join(enums_md), encoding="utf-8")

    # structs.md
    structs_md = [_front_matter("maix_lvgl.structs")]
    structs_md.append("# Structs\n\n")
    for cls in sorted(grouped["struct"], key=lambda c: c.name):
        structs_md.append(_class_markdown(cls, "struct"))
    (out_dir / "structs.md").write_text("".join(structs_md), encoding="utf-8")

    # maix_lvgl.md: backend helpers (hand-written, stable API)
    backend = _front_matter("maix_lvgl")
    backend += """# maix_lvgl

`maix_lvgl` re-exports the generated LVGL bindings and adds the MaixCAM2
display/touchscreen backend. Use it as `import maix_lvgl as lv`.

## init

```python
def init(display=None, touchscreen=None, width=None, height=None)
```

Initialize LVGL and bind MaixPy's display/touchscreen. When omitted, a
`maix.display.Display` (BGRA8888) and a `maix.touchscreen.TouchScreen` are
opened. Pass `touchscreen=False` to run without input.

## deinit

```python
def deinit()
```

Stop LVGL and release the display/touchscreen opened by `init()`.

## timer_handler

```python
def timer_handler()
```

Advance the LVGL tick (`lv.tick_inc`) and run one LVGL timer-handler pass.
Use this instead of the raw `lvgl.timer_handler()`.

## process

```python
def process()
```

Alias of `timer_handler()`.

## run

```python
def run(fps=60)
```

Run the LVGL loop until `maix.app.need_exit()` becomes true.

## DisplayDriver

Wraps a `maix.display.Display`: creates the LVGL display, renders into a
BGRA8888 `bytearray` and pushes frames with `display.show()`.

## TouchDriver

Wraps a `maix.touchscreen.TouchScreen`: feeds `read()` into an LVGL pointer
indev.

## Complete example

```python
import time
from maix import app, display, touchscreen
import maix_lvgl as lv

disp = display.Display()
ts = touchscreen.TouchScreen()

try:
    lv.init(disp, ts)
    scr = lv.screen_active()
    btn = lv.button(scr)
    btn.set_size(240, 120)
    btn.center()
    lv.label(btn).set_text("Hello MaixCAM2")

    while not app.need_exit():
        lv.timer_handler()
        time.sleep(0.005)
finally:
    lv.deinit()
    ts.close()
    disp.close()
```
"""
    (out_dir / "maix_lvgl.md").write_text(backend, encoding="utf-8")

    # README index
    readme = _front_matter("maix_lvgl API")
    readme += f"""# maix_lvgl API documentation

Generated from `binding/lvgl.pyi` at build time (MaixPy-style `docs/api`).

| File | Contents |
| --- | --- |
| [lvgl.md](lvgl.md) | module functions ({len(functions)}) and variables ({len(variables)}) |
| [classes.md](classes.md) | widget/object classes ({len(grouped['class'])}) |
| [enums.md](enums.md) | enums and constants ({len(grouped['enum'])}) |
| [structs.md](structs.md) | C struct wrappers ({len(grouped['struct'])}) |
| [maix_lvgl.md](maix_lvgl.md) | MaixCAM2 backend (`init`, `deinit`, `run`, drivers) |

The binding is generated from MaixCDK's pinned LVGL (9.1.0) with
[PyDevices/omnipython-lvgl](https://github.com/PyDevices/omnipython-lvgl).
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    (out_dir / "sidebar.yaml").write_text(
        "- README.md\n- lvgl.md\n- classes.md\n- enums.md\n- structs.md\n- maix_lvgl.md\n",
        encoding="utf-8",
    )

    print(
        f"API docs: {out_dir} "
        f"(functions {len(functions)}, classes {len(grouped['class'])}, "
        f"enums {len(grouped['enum'])}, structs {len(grouped['struct'])})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyi", default=str(ROOT / "binding" / "lvgl.pyi"))
    parser.add_argument("--out", default=str(ROOT / "docs" / "api" / "maix_lvgl"))
    args = parser.parse_args()
    generate(Path(args.pyi), Path(args.out))


if __name__ == "__main__":
    main()
