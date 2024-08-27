from importlib import metadata

try:
    __version__ = metadata.version(__package__)  # type: ignore
except metadata.PackageNotFoundError:
    __version__ = ""

# Avoid polluting the namespace (results of dir(__package__) would include metadata)
del metadata
