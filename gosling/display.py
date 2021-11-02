from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Set, Union
from gosling.schema import SCHEMA_VERSION, THEMES
import json
import uuid

import jinja2

HTML_TEMPLATE = jinja2.Template(
    """
<!DOCTYPE html>
<html>
<head>
  <style>.error { color: red; }</style>
  <link rel="stylesheet" href="{{ base_url }}/higlass@{{ higlass_version }}/dist/hglib.css">
</head>
<body>
  <div id="{{ output_div }}"></div>
  <script type="module">

    async function loadScript(src) {
        return new Promise(resolve => {
            const script = document.createElement('script');
            script.onload = resolve;
            script.src = src;
            script.async = false;
            document.head.appendChild(script);
        });
    }

    async function loadGosling() {
        // Manually load scripts from window namespace since requirejs might not be
        // available in all browser environments.
        // https://github.com/DanielHreben/requirejs-toggle
        if (!window.gosling) {
            window.__requirejsToggleBackup = {
                define: window.define,
                require: window.require,
                requirejs: window.requirejs,
            };
            for (const field of Object.keys(window.__requirejsToggleBackup)) {
                window[field] = undefined;
            }

            // load dependencies sequentially
            const sources = [
                "{{ base_url }}/react@{{ react_version }}/umd/react.production.min.js",
                "{{ base_url }}/react-dom@{{ react_version }}/umd/react-dom.production.min.js",
                "{{ base_url }}/pixi.js@{{ pixijs_version }}/dist/browser/pixi.min.js",
                "{{ base_url }}/gosling.js@{{ gosling_version }}/dist/gosling.js",
            ];

            for (const src of sources) await loadScript(src);

            // restore requirejs after scripts have loaded
            Object.assign(window, window.__requirejsToggleBackup);
            delete window.__requirejsToggleBackup;
        }
        return window.gosling;
    };

    var el = document.getElementById('{{ output_div }}');
    var spec = {{ spec }};
    var opt = {{ embed_options }};

    loadGosling()
        .then(gosling => gosling.embed(el, spec, opt))
        .catch(err => {
            el.innerHTML = `\
<div class="error">
    <p>JavaScript Error: ${error.message}</p>
    <p>This usually means there's a typo in your Gosling specification. See the javascript console for the full traceback.</p>
</div>`;
            throw error;
        });
  </script>
</body>
</html>
"""
)

GoslingSpec = Dict[str, Any]


def spec_to_html(
    spec: GoslingSpec,
    gosling_version: str = SCHEMA_VERSION.lstrip("v"),
    higlass_version: str = "1.11",
    react_version: str = "17",
    pixijs_version: str = "6",
    base_url: str = "https://unpkg.com",
    output_div: str = "vis",
    embed_options: Dict[str, Any] = None,
):
    embed_options = embed_options or dict(padding=0, theme=themes.get())

    return HTML_TEMPLATE.render(
        spec=json.dumps(spec),
        embed_options=json.dumps(embed_options),
        gosling_version=gosling_version,
        higlass_version=higlass_version,
        react_version=react_version,
        pixijs_version=pixijs_version,
        base_url=base_url,
        output_div=output_div,
    )


class Renderer:
    def __init__(self, output_div: str = "jupyter-gosling-{}", **kwargs: Any):
        self._output_div = output_div
        self.kwargs = kwargs

    @property
    def output_div(self) -> str:
        return self._output_div.format(uuid.uuid4().hex)

    def __call__(self, spec: GoslingSpec, **meta: Any) -> Dict[str, Any]:
        raise NotImplementedError()


class HTMLRenderer(Renderer):
    def __call__(self, spec: GoslingSpec, **meta: Any):
        kwargs = self.kwargs.copy()
        kwargs.update(meta)
        html = spec_to_html(spec=spec, output_div=self.output_div, **kwargs)
        return {"text/html": html}


@dataclass
class RendererRegistry:
    renderers: Dict[str, Renderer] = field(default_factory=dict)
    active: Optional[str] = None

    def register(self, name: str, renderer: Renderer) -> None:
        self.renderers[name] = renderer

    def enable(self, name: str) -> None:
        assert name in self.renderers
        self.active = name

    def get(self) -> Renderer:
        assert isinstance(self.active, str) and self.active in self.renderers
        return self.renderers[self.active]


html_renderer = HTMLRenderer()
renderers = RendererRegistry()
renderers.register("default", html_renderer)
renderers.register("html", html_renderer)
renderers.register("colab", html_renderer)
renderers.register("kaggle", html_renderer)
renderers.register("zeppelin", html_renderer)
renderers.enable("default")

CustomTheme = Dict[str, Any]


@dataclass
class ThemesRegistry:
    themes: Set[str]
    custom_themes: Dict[str, CustomTheme] = field(default_factory=dict)
    active: Optional[str] = None

    def register(self, name: str, theme: CustomTheme) -> None:
        assert (
            name not in self.themes
        ), f"cannot override built-in themes, {self.themes}"
        self.custom_themes[name] = theme

    def enable(self, name: str) -> None:
        assert (
            name in self.custom_themes or name in self.themes
        ), f"theme must be one of {self.themes} or {set(self.custom_themes.keys())}."
        self.active = name

    def get(self) -> Union[None, str, CustomTheme]:
        if self.active is None:
            return None
        if self.active in self.themes: 
            return self.active
        return self.custom_themes[self.active]


themes = ThemesRegistry(THEMES)
