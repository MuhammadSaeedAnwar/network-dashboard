import pytest

from app.services.validation import ValidationError, validate_single_target


@pytest.mark.parametrize("address", ["192.168.1.1", "10.0.0.5", "example.com", "my-router.local", "::1"])
def test_valid_targets_pass(address):
    assert validate_single_target(address) == address


@pytest.mark.parametrize(
    "address",
    [
        "192.168.1.0/24",
        "10.0.0.0/8",
        "",
        "   ",
        "host; rm -rf /",
        "host | cat /etc/passwd",
        "host $(whoami)",
        "host `whoami`",
        "192.168.*.1",
        "two words",
    ],
)
def test_invalid_targets_rejected(address):
    with pytest.raises(ValidationError):
        validate_single_target(address)


def test_cidr_rejected_with_clear_message():
    with pytest.raises(ValidationError, match="CIDR"):
        validate_single_target("10.0.0.0/24")
