def csv(url: str, **kwargs):
    return dict(type="csv", url=url, **kwargs)


def bigwig(url: str, **kwargs):
    return dict(type="bigwig", url=url, **kwargs)


def json(url: str, **kwargs):
    return dict(type="json", url=url, **kwargs)


def beddb(url: str, **kwargs):
    return dict(type="beddb", url=url, **kwargs)


def vector(url: str, **kwargs):
    return dict(type="vector", url=url, **kwargs)


def multivec(url: str, **kwargs):
    return dict(type="multivec", url=url, **kwargs)


def bam(url: str, **kwargs):
    return dict(type="bam", url=url, **kwargs)


def matrix(url: str, **kwargs):
    return dict(type="matrix", url=url, **kwargs)