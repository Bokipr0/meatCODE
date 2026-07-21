from moldedup.normalize import normalize_name, clean_display_name


def test_case_and_whitespace_folding():
    assert normalize_name("  Vanillin  ") == "vanillin"
    assert normalize_name("VANILLIN") == normalize_name("vanillin")
    assert normalize_name("4-Hydroxy-3-Methoxy   benzaldehyde") == "4-hydroxy-3-methoxy benzaldehyde"


def test_strips_wrapping_quotes():
    assert normalize_name('"vanillin"') == "vanillin"
    assert normalize_name("“Furaneol”") == "furaneol"


def test_unicode_nfkc():
    # full-width chars fold to ascii under NFKC
    assert normalize_name("ｖanillin") == "vanillin"


def test_blank_and_none():
    assert normalize_name("") == ""
    assert normalize_name(None) == ""
    assert normalize_name("   ") == ""


def test_clean_display_preserves_case():
    assert clean_display_name("  Vanillin ") == "Vanillin"
    assert clean_display_name('"2-Acetyl-1-pyrroline"') == "2-Acetyl-1-pyrroline"
