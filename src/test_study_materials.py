"""Guard against extracting exhibits from changed PDFs or HTML download failures."""

import hashlib
import pytest
from build_study_materials import verify_paper


def test_rejects_changed_source_version():
    """A syntactically plausible PDF must still match the reviewed source digest."""
    original = b"%PDF-1.7 original reviewed bytes"
    expected = hashlib.sha256(original).hexdigest()
    verify_paper(original, expected)
    with pytest.raises(ValueError, match="checksum changed"):
        verify_paper(original + b"changed version", expected)


def test_rejects_html_even_if_digest_matches():
    """A server error or sign-in page must not be accepted as the paper."""
    html = b"<html>Sign in</html>"
    with pytest.raises(ValueError, match="did not return a PDF"):
        verify_paper(html, hashlib.sha256(html).hexdigest())
