import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from telediff.__main__ import main as telediff_main


def make_config(tmp_path, content):
    config_dir = tmp_path / "config"
    os.makedirs(config_dir, exist_ok=True)
    config_file = config_dir / "config.toml"
    config_file.write_text(content)
    return config_dir


def run_cli(args, monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["telediff"] + args)
    monkeypatch.setattr(
        "telediff.util.user_config_dir", lambda app: str(tmp_path / "config")
    )
    with pytest.raises(SystemExit) as excinfo:
        telediff_main()
    return excinfo.value.code


def test_test_command_valid_channel(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(["test", "--channel", "foo"], monkeypatch, tmp_path)
        out = capsys.readouterr()
        assert code == 0
        apprise_obj.add.assert_called_once_with("apprise://devnull/")
        apprise_obj.notify.assert_called_once_with(
            title="telediff test", body="This is a test notification from telediff."
        )
        assert "Test notification sent to channel 'foo'" in out.out


def test_test_command_invalid_channel(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    with patch("apprise.Apprise") as mock_apprise:
        code = run_cli(["test", "--channel", "bar"], monkeypatch, tmp_path)
        out = capsys.readouterr()
        assert code == 1
        mock_apprise.return_value.add.assert_not_called()
        assert "Error:" in out.out or "Error:" in out.err


def test_test_command_custom_title(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["test", "--channel", "foo", "--title", "MyTitle"], monkeypatch, tmp_path
        )
        out = capsys.readouterr()
        assert code == 0
        apprise_obj.notify.assert_called_once_with(
            title="MyTitle", body="This is a test notification from telediff."
        )
        assert "Test notification sent to channel 'foo'" in out.out
