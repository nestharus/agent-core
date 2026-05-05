import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from clients.linear.cli import (
    get_issue_description,
    main,
    split_plans,
    update_issue,
)


class TestMain:
    def test_no_command_shows_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should show error when no command is provided."""
        with patch.object(sys, "argv", ["linear"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 2
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is False
            assert result["error"]["code"] == "INVALID_INPUT"
