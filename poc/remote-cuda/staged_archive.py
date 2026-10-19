"""Bound gzip expansion before tarfile can consume hidden PAX/GNU metadata."""
from contextlib import contextmanager
import gzip
import io
import tarfile


def read_compressed(path, limit):
    # Bound the read itself, rather than allocating an arbitrarily large file.
    with path.open('rb') as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise ValueError('compressed archive limit exceeded')
    return data


@contextmanager
def open_archive(data, compressed_limit, expanded_limit, member_limit):
    if not 0 < len(data) <= compressed_limit:
        raise ValueError('compressed archive limit exceeded')
    # This includes every header, extension payload and padding byte, even gzip
    # members/trailing tar data that tarfile would otherwise skip. Do not hand
    # compressed bytes to tarfile: it parses extension metadata before yielding.
    with gzip.GzipFile(fileobj=io.BytesIO(data), mode='rb') as source:
        expanded = source.read(expanded_limit + 1)
    if len(expanded) > expanded_limit:
        raise ValueError('expanded archive limit exceeded before tar parsing')
    with tarfile.open(fileobj=io.BytesIO(expanded), mode='r:') as archive:
        def members():
            for count, member in enumerate(archive, 1):
                if count > member_limit:
                    raise ValueError('archive member limit exceeded')
                yield member
        yield archive, members()
