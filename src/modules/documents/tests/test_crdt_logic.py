"""Unit tests for CRDTDocumentManager."""

import y_py as Y

from src.modules.documents.crdt import CRDTDocumentManager


def test_crdt_initial_state():
    """Test initializing CRDT with text and state."""
    manager = CRDTDocumentManager.from_text("Hello World")
    assert manager.get_content() == "Hello World"

    state = manager.get_state()
    assert isinstance(state, bytes)

    new_manager = CRDTDocumentManager(state)
    assert new_manager.get_content() == "Hello World"


def test_crdt_merging():
    """Test that two independent updates converge."""
    base = CRDTDocumentManager.from_text("Hello")
    base_state = base.get_state()

    # Client A adds " Alice"
    client_a = CRDTDocumentManager(base_state)
    with client_a.doc.begin_transaction() as tr:
        client_a.text.insert(tr, 5, " Alice")
    update_a = Y.encode_state_as_update(client_a.doc, base_state)

    # Client B adds " Bob"
    client_b = CRDTDocumentManager(base_state)
    with client_b.doc.begin_transaction() as tr:
        client_b.text.insert(tr, 5, " Bob")
    update_b = Y.encode_state_as_update(client_b.doc, base_state)

    # Apply both to base
    base.apply_update(update_a)
    base.apply_update(update_b)

    # Result should contain both (order depends on Yjs internal logic, but should be stable)
    content = base.get_content()
    assert "Alice" in content
    assert "Bob" in content
    assert content.startswith("Hello")


def test_crdt_to_from_text():
    """Test utility methods."""
    manager = CRDTDocumentManager.from_text("Initial")
    assert manager.get_content() == "Initial"

    manager.apply_update(CRDTDocumentManager.from_text(" Overwritten?").get_state())
    # Note: apply_update merges, it doesn't replace unless the Yjs operations say so.
    # In this case, it might just append or create a messy merge.
    # But for text, it's about operations.
