import ast
import dataclasses
import itertools
import pathlib
import re
from typing import Iterable, Optional, TypeVar, Tuple
import jinja2
import tokenize
import io

from gosling.examples import iter_examples


GALLERY_TEMPLATE = jinja2.Template(
    """
.. This document is auto-generated by the gosling-gallery extension. Do not modify directly.

.. _{{ gallery_ref }}:

This gallery contains a selection of examples of the visualizations **gos** can create.

{% for category, examples in example_groups %}

{{ category | capitalize }}
{% for char in category %}-{% endfor %}

.. toctree::

{% for example in examples %}
    {{ example.name }}
{%- endfor %}

{%- endfor %}
"""
)

EXAMPLE_TEMPLATE = jinja2.Template(
    """
.. This document is auto-generated by the gosling-gallery extension. Do not modify directly.

.. _gallery_{{ name }}:

{{ docstring }}

.. gosling-plot::
    {% if code_below %}:code-below:{% endif %}

    {{ code | indent(4) }}
"""
)

@dataclasses.dataclass
class Example:
    name: str
    docstring: str
    code: str
    lineno: int
    category: str

    @classmethod
    def from_file(cls, file: pathlib.Path):
        content = file.read_text()
        # change from Windows format to UNIX for uniformity
        content = content.replace("\r\n", "\n")
        docstring = ast.get_docstring(ast.parse(content)) or ""

        # Find the category comment
        find_category = re.compile(r"^#\s*category:\s*(.*)$", re.MULTILINE)
        match = find_category.search(content)
        if match is not None:
            category = match.groups()[0]
            # remove this comment from the content
            content = find_category.sub("", content)
        else:
            category = "other"

        ts = tokenize.tokenize(io.BytesIO(content.encode("utf-8")).readline)
        ds_lines = 0
        # find the first string according to the tokenizer and get
        # it's end row
        for tk in ts:
            if tk.exact_type == 3:
                ds_lines, _ = tk.end
                break
        # grab the rest of the file
        rest = "\n".join(content.split("\n")[ds_lines:])
        lineno = ds_lines + 1

        return cls(
            name=file.stem,
            docstring=docstring,
            code=rest,
            lineno=lineno,
            category=category,
        )

T = TypeVar("T")
def prev_this_next(it: Iterable[T], sentinel=None) -> Iterable[Tuple[Optional[T], T, Optional[T]]]:
    """Utility to return (prev, this, next) tuples from an iterator"""
    i1, i2, i3 = itertools.tee(it, 3)
    next(i3, None)
    return zip(itertools.chain([sentinel], i1), i2, itertools.chain(i3, [sentinel]))

def populate_examples():
    return sorted(map(Example.from_file, iter_examples()), key=lambda e: e.category)

def main(app):
    srcdir = pathlib.Path(app.builder.srcdir)
    title = "Example Gallery"
    gallery_dir = "gallery"
    gallery_ref = "example-gallery"
    target_dir = srcdir / gallery_dir

    if not target_dir.is_dir():
        target_dir.mkdir(parents=True)

    examples = populate_examples()
    example_groups = itertools.groupby(examples, key=lambda e: e.category)

    # Write the gallery index file
    with open(target_dir / "index.rst", "w") as f:
        f.write(
            GALLERY_TEMPLATE.render(
                title=title,
                example_groups=example_groups,
                gallery_ref=gallery_ref,
            )
        )

    for prev_ex, example, next_ex in prev_this_next(examples):
        ex = dataclasses.asdict(example)
        ex["code_below"] = True
        if prev_ex:
            ex["prev_ref"]= f"gallery_{prev_ex.name}"
        if next_ex:
            ex["next_ref"] = f"gallery_{next_ex.name}"
        with open(target_dir / (example.name + ".rst"), "w") as f:
            f.write(EXAMPLE_TEMPLATE.render(ex))


def setup(app):
    app.connect("builder-inited", main)
