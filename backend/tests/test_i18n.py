from app.core.i18n import normalize_language, translate


def test_all_supported_languages_translate():
    assert [translate("not_found", code) for code in ("ru", "kk", "en", "tr")] == ["Не найдено", "Табылмады", "Not found", "Bulunamadı"]


def test_accept_language_normalization():
    assert normalize_language("kk-KZ,kk;q=0.9") == "kk"
    assert normalize_language("de-DE") == "ru"
