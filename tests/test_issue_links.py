from img2dwg.utils.issue_links import extract_issue_links


def test_extract_issue_links_parses_closes_and_refs() -> None:
    text = """
    ## Summary
    Closes #23
    Refs #24
    """

    links = extract_issue_links(text)

    assert links.closing_ids == {23}
    assert links.reference_ids == {24}


def test_extract_issue_links_supports_full_issue_url() -> None:
    text = "Fixes https://github.com/J511Y/img2dwg/issues/18"

    links = extract_issue_links(text)

    assert links.closing_ids == {18}
    assert links.reference_ids == set()


def test_extract_issue_links_supports_multiple_targets_per_line() -> None:
    text = "Resolved: #10, #11 and J511Y/img2dwg#12"

    links = extract_issue_links(text)

    assert links.closing_ids == {10, 11, 12}
    assert links.reference_ids == set()


def test_extract_issue_links_deduplicates_between_close_and_ref() -> None:
    text = """
    Refs #23
    Closes #23
    Refs #30
    """

    links = extract_issue_links(text)

    assert links.closing_ids == {23}
    assert links.reference_ids == {30}


def test_extract_issue_links_handles_empty_text() -> None:
    links = extract_issue_links(None)

    assert links.closing_ids == set()
    assert links.reference_ids == set()
