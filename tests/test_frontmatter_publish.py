import pytest
from scripts.frontmatter import add_frontmatter, is_ready_for_sync, promote_status, get_document_status


def test_ai_processed_sets_in_progress_and_not_ready_for_sync():
    content = "# Test Report\n\nSome content"
    updated = add_frontmatter(content, "test_report.md", status=None, ai_processed=True)

    # Status should be in_progress when AI processed
    assert get_document_status(updated) == "in_progress"

    # Not ready for sync until explicitly promoted
    assert not is_ready_for_sync(updated)

    # Promote to published
    promoted = promote_status(updated, "test_report.md")
    assert get_document_status(promoted) == "review" or get_document_status(promoted) == "published"

    # Promote until published
    while get_document_status(promoted) != "published":
        promoted = promote_status(promoted, "test_report.md")

    assert is_ready_for_sync(promoted)
