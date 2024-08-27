from __future__ import annotations

import os

from dataloader.indexer.models import Document


class File(Document):
    """A representation of a file."""

    path: str | None = None
    """The path of the file.
    The basename of the path is used as the name of the file and can differ to the name in the metadata.
    """
    mimetype: str | None = None
    """The mimetype of the file."""

    @classmethod
    def from_document(cls, doc: Document, path: str | None = None, mimetype: str | None = None) -> File:
        """Create a file from a document."""
        from dataloader.loaders.models.webloader import WebDocument

        if isinstance(doc, WebDocument):
            return doc.to_file()

        return cls(
            metadata=doc.metadata,
            content=doc.content,
            path=path,
            mimetype=mimetype,
        )

    def to_document(self) -> Document:
        """Convert the file to a document."""
        if dirname := self.get_directory_name():
            self.metadata.category = dirname

        self.metadata.name = self.get_file_name()
        return Document(
            metadata=self.metadata,
            content=self.content,
        )

    def get_file_name(self) -> str:
        """Get the name of the file."""
        return self.build_file_name(self.metadata.name, self.path)

    def get_directory_name(self) -> str | None:
        """Get the name of the directory."""
        return self.build_directory_name(self.path)

    def get_blob_name(self) -> str:
        """Get the name of the blob."""
        return self.build_blob_name(self.metadata.name, self.path)

    @staticmethod
    def build_file_name(filename: str, path: str | None) -> str:
        """Get the name of the file. Returns the filename if no path is provided."""
        if not path or path in (filename, ""):
            return filename
        parts = path.split("/")
        if len(parts) > 2:
            # We can only use one directory depth since we are using the directory name as file category
            # So we need to cut off the first part (directory name) and then flatten the path by replacing slashes with underscores
            return "/".join(parts[1:]).replace("/", "_")
        return os.path.basename(path)

    @staticmethod
    def build_directory_name(path: str | None) -> str | None:
        """Get the name of the directory. Returns None if no directory name can be determined."""
        if not path:
            return None
        parts = path.split("/")
        if len(parts) > 1:
            return parts[0]
        return None

    @classmethod
    def build_blob_name(cls, filename: str, path: str | None) -> str:
        """Get the name of the blob."""
        dirname = cls.build_directory_name(path)
        if dirname:
            return f"{dirname}/{cls.build_file_name(filename, path)}"
        return cls.build_file_name(filename, path)
