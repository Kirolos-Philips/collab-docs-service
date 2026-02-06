"""CRDT management for real-time document editing using y-py."""

import y_py as Y


class CRDTDocumentManager:
    """Manages a single document's CRDT state using Yjs (y-py)."""

    def __init__(self, initial_state: bytes | None = None):
        self.doc = Y.YDoc()
        self.text = self.doc.get_text("content")

        if initial_state:
            Y.apply_update(self.doc, initial_state)

    def apply_update(self, update: bytes):
        """Merge an incoming binary update into the current document state."""
        Y.apply_update(self.doc, update)

    def get_state(self) -> bytes:
        """Get the full binary state of the document for persistence."""
        return Y.encode_state_as_update(self.doc)

    def get_content(self) -> str:
        """Return the current plain text content of the document."""
        return str(self.text)

    @classmethod
    def from_text(cls, text: str) -> "CRDTDocumentManager":
        """Create a new CRDT document from existing plain text."""
        instance = cls()
        with instance.doc.begin_transaction() as tr:
            instance.text.extend(tr, text)
        return instance
