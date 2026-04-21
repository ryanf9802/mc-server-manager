from mc_server_manager.validation.server_properties import ServerPropertiesValidator
from mc_server_manager.validation.whitelist import WhitelistValidator


def test_server_properties_validator_accepts_expected_lines() -> None:
    validator = ServerPropertiesValidator()

    result = validator.validate("# Comment\nmotd=Weekend\n\nmax-players=8")

    assert result.is_valid


def test_server_properties_validator_rejects_missing_equals() -> None:
    validator = ServerPropertiesValidator()

    result = validator.validate("motd=Weekend\nbroken line")

    assert not result.is_valid
    assert result.issues[0].line_number == 2


def test_whitelist_validator_accepts_expected_shape() -> None:
    validator = WhitelistValidator()

    result = validator.validate('[{"name":"ryanf","uuid":"00000000-0000-0000-0000-000000000000"}]')

    assert result.is_valid


def test_whitelist_validator_rejects_missing_uuid() -> None:
    validator = WhitelistValidator()

    result = validator.validate('[{"name":"ryanf"}]')

    assert not result.is_valid
    assert any(issue.code == "whitelist_uuid_missing" for issue in result.issues)
