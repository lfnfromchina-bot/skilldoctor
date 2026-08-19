from skilldoctor.cli import _pick_lang


def test_pick_lang_explicit_flag_wins():
    assert _pick_lang("zh") == "zh"
    assert _pick_lang("zh-CN") == "zh"
    assert _pick_lang("en") == "en"


def test_pick_lang_from_locale(monkeypatch):
    monkeypatch.setattr("locale.getlocale", lambda: ("zh_CN", "UTF-8"))
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)
    assert _pick_lang(None) == "zh"

    monkeypatch.setattr("locale.getlocale", lambda: (None, None))
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert _pick_lang(None) == "en"
