from mc_server_manager.services.world_name import create_slug, ensure_unique_slug


def test_create_slug_normalizes_input() -> None:
    assert create_slug(" Weekend Vanilla++ 2026 ") == "weekend-vanilla-2026"


def test_create_slug_falls_back_to_world() -> None:
    assert create_slug("!!!") == "world"


def test_ensure_unique_slug_appends_suffix() -> None:
    assert ensure_unique_slug("weekend", {"weekend", "weekend-2"}) == "weekend-3"
