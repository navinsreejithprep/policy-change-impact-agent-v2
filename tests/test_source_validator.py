from app.tools.source_validator import (
    classify_source,
    detect_amendment_note,
    detect_version_status,
    is_likely_official,
    is_official,
)


def test_official_domain_recognised():
    assert is_official("https://www.meity.gov.in/a")
    assert classify_source("https://www.meity.gov.in/a") == "official"


def test_secondary_domain_rejected():
    assert not is_official("https://example.com/a")
    assert classify_source("https://example.com/a") == "secondary"


def test_subdomain_of_allowlisted_domain_is_official():
    assert is_official("https://press.cert-in.org.in/notice")


def test_non_allowlisted_government_domain_is_likely_official_not_secondary():
    assert not is_official("https://www.cisa.gov/topics/some-advisory")
    assert is_likely_official("https://www.cisa.gov/topics/some-advisory")
    assert classify_source("https://www.cisa.gov/topics/some-advisory") == "likely_official"


def test_generic_gov_uk_domain_is_likely_official():
    assert classify_source("https://www.gov.uk/some-guidance") == "likely_official"


def test_blog_is_secondary_not_likely_official():
    assert classify_source("https://lawfirm-blog.example.com/commentary") == "secondary"


def test_version_status_detects_draft():
    assert detect_version_status("This is a draft consultation paper.") == "draft"


def test_version_status_detects_final():
    assert detect_version_status("This notification is gazetted and comes into force immediately.") == "final"


def test_version_status_unknown_when_no_markers():
    assert detect_version_status("Generic content with no version markers.") == "unknown"


def test_amendment_note_flags_supersession_language():
    note = detect_amendment_note("This circular supersedes the 2019 circular on the same subject.")
    assert note is not None
    assert "supersede" in note.lower()


def test_amendment_note_none_when_no_markers():
    assert detect_amendment_note("Plain regulatory text with no amendment language.") is None
