import pytest

from clients.linear.client import LinearClient, LinearClientError


class TestLinearClientInit:
    def test_init_with_api_key(self) -> None:
        """Initialize client with explicit API key."""
        client = LinearClient(api_key="test_api_key")
        assert client._api_key == "test_api_key"

    def test_init_with_api_key_strips_whitespace(self) -> None:
        """Initialize client with API key strips leading/trailing whitespace."""
        client = LinearClient(api_key="  test_api_key  ")
        assert client._api_key == "test_api_key"

    def test_init_raises_for_empty_api_key(self) -> None:
        """Raise error when explicit API key is empty string."""
        with pytest.raises(LinearClientError) as exc_info:
            LinearClient(api_key="")
        assert exc_info.value.code == "EMPTY_API_KEY"
        assert "empty or whitespace-only" in exc_info.value.message

    def test_init_raises_for_whitespace_only_api_key(self) -> None:
        """Raise error when explicit API key is whitespace-only."""
        with pytest.raises(LinearClientError) as exc_info:
            LinearClient(api_key="   ")
        assert exc_info.value.code == "EMPTY_API_KEY"
        assert "empty or whitespace-only" in exc_info.value.message

    def test_init_does_not_validate_scripts_directory(self) -> None:
        """Client initialization does not check scripts directory existence.

        The scripts directory is only validated when a script is actually invoked.
        """
        # Client should initialize even if scripts directory doesn't exist
        # (the check happens in _run_script, not __init__)
        client = LinearClient(api_key="test_key")
        assert client._api_key == "test_key"


class TestValidatePriority:
    @pytest.mark.parametrize("priority", [0, 1, 2, 3, 4])
    def test_valid_priorities_pass(self, priority: int) -> None:
        """Valid priorities (0-4) do not raise errors."""
        client = LinearClient(api_key="test-key")
        # Should not raise
        client._validate_priority(priority)

    def test_none_priority_passes(self) -> None:
        """None priority (no priority set) does not raise."""
        client = LinearClient(api_key="test-key")
        # Should not raise
        client._validate_priority(None)

    @pytest.mark.parametrize("invalid_priority", [-1, 5, 100, -100])
    def test_invalid_priorities_raise(self, invalid_priority: int) -> None:
        """Invalid priorities raise LinearClientError."""
        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client._validate_priority(invalid_priority)
        assert exc_info.value.code == "INVALID_PRIORITY"
        assert "must be between 0 and 4" in exc_info.value.message

    @pytest.mark.parametrize("bool_value", [True, False])
    def test_boolean_raises(self, bool_value: bool) -> None:
        """Boolean values are rejected even though bool is subclass of int."""
        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client._validate_priority(bool_value)
        assert exc_info.value.code == "INVALID_PRIORITY"
