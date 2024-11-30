from __future__ import annotations

import pathlib
import typing

import gosling.data._tilesets as tilesets
from gosling.utils.core import _compute_data_hash

if typing.TYPE_CHECKING:
    from servir import Provider, Resource, TilesetResource


def _hash_path(path: pathlib.Path):
    """Computes a hash for a path.

    Parameters
    ----------
    path : pathlib.Path
        The path to hash.
    Returns
    -------
    str
        The hash.
    """
    return _compute_data_hash(path.resolve().as_posix())


def _extract_url(resource: Resource | TilesetResource) -> str:
    """Extracts the URL for Gosling from a server resource.

    Parameters
    ----------
    resource : Resource | TilesetResource
        The resource to extract the URL from.
    Returns
    -------
    str
        The URL for Gosling.
    """
    from servir import TilesetResource

    if isinstance(resource, TilesetResource):
        return f"{resource.server.rstrip('/')}/tileset_info/?d={resource.uid}"

    return resource.url


class GoslingDataServer:
    """Backend server for Gosling datasets."""

    def __init__(self) -> None:
        self._provider: None | Provider = None

        # We need to keep references to served resources, because the background
        # server uses weakrefs.
        self._resources: dict[str, Resource | TilesetResource] = {}

    @property
    def port(self):
        if not self._provider:
            raise RuntimeError("Server not started.")
        return self._provider.port

    def reset(self) -> None:
        if self._provider is not None:
            self._provider.stop()
        self._resources = {}

    def __call__(
        self,
        data: str | pathlib.Path | tilesets.Tileset,
        port: int | None = None,
        **kwargs: typing.Any,
    ) -> str:
        if self._provider is None:
            from servir import Provider

            self._provider = Provider()
            self._provider.start(port=port)

        if port is not None and port != self._provider.port:
            self._provider.stop().start(port=port)

        if isinstance(data, tilesets.Tileset):
            resource_id = _hash_path(data.filepath)
        elif isinstance(data, pathlib.Path):
            resource_id = _hash_path(data)
        else:
            resource_id = _compute_data_hash(data)

        if resource_id not in self._resources:
            self._resources[resource_id] = self._provider.create(data, **kwargs)

        return _extract_url(self._resources[resource_id])

    def __rich_repr__(self):
        yield "resources", self._resources
        try:
            port = self.port
        except RuntimeError:
            port = None
        yield "port", port


data_server = GoslingDataServer()


def _create_loader(
    type_: str,
    create_ts: typing.Callable[[pathlib.Path], tilesets.Tileset] | None = None,
):
    def load(url: pathlib.Path | str, port: int | None = None, **kwargs):
        """Adds resource to data_server if local file is detected."""
        fp = pathlib.Path(url)
        if fp.is_file():
            data = create_ts(fp) if create_ts else fp
            url = data_server(data, port=port)

        # bam's index file url
        if "indexUrl" in kwargs:
            fp = pathlib.Path(kwargs["indexUrl"])
            if fp.is_file():
                kwargs["indexUrl"] = data_server(fp, port=port)

        return dict(type=type_, url=str(url), **kwargs)

    return load


# in-memory data
def json(values: list[dict[str, typing.Any]], **kwargs):
    return dict(type="json", values=values, **kwargs)


# file resources
bam = _create_loader("bam")
csv = _create_loader("csv")
bigwig = _create_loader("bigwig")
bed = _create_loader("bed")

# tileset resources
beddb = _create_loader("beddb", tilesets.beddb)
vector = _create_loader("vector", tilesets.bigwig)
matrix = _create_loader("matrix", tilesets.cooler)
multivec = _create_loader("multivec", tilesets.multivec)
