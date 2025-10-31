"""
Test suite for LockResult nested failure support.

Tests the enhanced LockResult class with nested_failures, context, and passing_path fields
for hierarchical error reporting in composite locks.
"""

from stageflow.lock import LockResult, LockType


class TestLockResultNestedFailures:
    """Test suite for LockResult nested failure functionality."""

    def test_lock_result_with_nested_failures(self):
        """Verify LockResult supports nested failures."""
        nested1 = LockResult(
            success=False,
            property_path="field1",
            lock_type=LockType.EXISTS,
            error_message="Field1 is missing",
        )

        nested2 = LockResult(
            success=False,
            property_path="field2",
            lock_type=LockType.EXISTS,
            error_message="Field2 is missing",
        )

        parent = LockResult(
            success=False,
            property_path="<conditional>",
            lock_type=LockType.EXISTS,  # Using existing type for test
            error_message="THEN branch failed",
            nested_failures=[nested1, nested2],
            context="then branch",
        )

        assert len(parent.nested_failures) == 2
        assert parent.context == "then branch"

    def test_lock_result_format_error_tree(self):
        """Verify error tree formatting."""
        nested = LockResult(
            success=False,
            property_path="testing",
            lock_type=LockType.EXISTS,
            error_message="Testing section is required",
        )

        parent = LockResult(
            success=False,
            property_path="<conditional>",
            lock_type=LockType.EXISTS,  # Using existing type for test
            error_message="Conditional validation failed",
            nested_failures=[nested],
            context="then branch",
        )

        tree = parent.format_error_tree()
        assert "[then branch]" in tree
        assert "→ Conditional validation failed" in tree
        assert "Testing section is required" in tree

    def test_lock_result_passing_path(self):
        """Verify passing_path field for OR logic."""
        result = LockResult(
            success=True,
            property_path="<or_logic>",
            lock_type=LockType.EXISTS,  # Using existing type for test
            passing_path=2,
            context="Path 2 passed",
        )

        assert result.passing_path == 2
        assert result.context == "Path 2 passed"

    def test_lock_result_backward_compatibility(self):
        """Verify existing code still works without new fields."""
        # Old-style LockResult creation (no new fields)
        result = LockResult(
            success=False,
            property_path="field",
            lock_type=LockType.EXISTS,
            error_message="Field is missing",
        )

        # New fields have default values
        assert result.nested_failures == []
        assert result.context == ""
        assert result.passing_path is None

    def test_lock_result_format_error_tree_empty(self):
        """Verify format_error_tree works with no nested failures."""
        result = LockResult(
            success=False,
            property_path="field",
            lock_type=LockType.EXISTS,
            error_message="Field is missing",
        )

        tree = result.format_error_tree()
        assert "Field is missing" in tree
        assert "[" not in tree  # No context

    def test_lock_result_format_error_tree_with_context_only(self):
        """Verify format_error_tree works with context but no error message."""
        result = LockResult(
            success=True,
            property_path="<or_logic>",
            lock_type=LockType.EXISTS,  # Using existing type for test
            context="Path 1 passed",
            passing_path=1,
        )

        tree = result.format_error_tree()
        assert "[Path 1 passed]" in tree
        assert "→" not in tree  # No error message

    def test_lock_result_format_error_tree_nested_hierarchy(self):
        """Verify format_error_tree works with multiple levels of nesting."""
        # Deepest level
        leaf = LockResult(
            success=False,
            property_path="deep.field",
            lock_type=LockType.EXISTS,
            error_message="Deep field missing",
        )

        # Middle level
        middle = LockResult(
            success=False,
            property_path="<nested>",
            lock_type=LockType.EXISTS,  # Using existing type for test
            error_message="Nested condition failed",
            nested_failures=[leaf],
            context="nested condition",
        )

        # Top level
        root = LockResult(
            success=False,
            property_path="<root>",
            lock_type=LockType.EXISTS,  # Using existing type for test
            error_message="Root condition failed",
            nested_failures=[middle],
            context="root condition",
        )

        tree = root.format_error_tree()

        # Check structure
        lines = tree.split("\n")
        assert len(lines) >= 3

        # Root level
        assert "[root condition]" in lines[0]
        assert "→ Root condition failed" in lines[1]

        # Nested level (indented)
        assert "  [nested condition]" in tree
        assert "  → Nested condition failed" in tree
        assert "    → Deep field missing" in tree

    def test_lock_result_format_error_tree_indent_levels(self):
        """Verify format_error_tree handles indentation correctly."""
        result = LockResult(
            success=False,
            property_path="test",
            lock_type=LockType.EXISTS,
            error_message="Test error",
        )

        # Test different indent levels
        tree0 = result.format_error_tree(0)
        tree1 = result.format_error_tree(1)
        tree2 = result.format_error_tree(2)

        assert "→ Test error" in tree0
        assert "  → Test error" in tree1
        assert "    → Test error" in tree2
