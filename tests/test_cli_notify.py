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
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with pytest.raises(SystemExit) as excinfo:
        telediff_main()
    return excinfo.value.code


def test_notify_new_text_file(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello world\n")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        apprise_obj.notify.assert_called()
        # Should send a diff from empty
        args, kwargs = apprise_obj.notify.call_args
        assert "hello world" in kwargs["body"]
        assert "Notification sent" in out.out


def test_notify_unchanged_text_file(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello world\n")
    # First run to create cache
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
        assert code == 0
    # Second run, should detect no change and not notify
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        apprise_obj.notify.assert_not_called()
        assert "No change detected" in out.out


def test_notify_new_text_file_from_stdin(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file2.txt"
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdin, "read", lambda: "from stdin\n")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("from stdin\n")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        apprise_obj.notify.assert_called()
        args, kwargs = apprise_obj.notify.call_args
        assert "from stdin" in kwargs["body"]
        assert "@@ -0,0 +1 @@" in kwargs["body"]
        assert "Notification sent" in out.out


def test_notify_changed_text_file(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file3.txt"
    file_path.write_text("first\n")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
    # Change file
    file_path.write_text("second\n")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        apprise_obj.notify.assert_called()
        args, kwargs = apprise_obj.notify.call_args
        assert "second" in kwargs["body"]
        assert "diff" in kwargs["body"] or "---" in kwargs["body"]
        assert "Notification sent" in out.out


def test_notify_custom_body_includes_path(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file4.txt"
    file_path.write_text("irrelevant\n")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            [
                "notify",
                "--channel",
                "foo",
                "--file",
                str(file_path),
                "--body",
                "custom body",
            ],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        args, kwargs = apprise_obj.notify.call_args
        assert "custom body" in kwargs["body"]
        assert str(file_path) in kwargs["body"]
        assert "Notification sent" in out.out


def test_notify_custom_body_no_path(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file5.txt"
    file_path.write_text("irrelevant\n")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            [
                "notify",
                "--channel",
                "foo",
                "--file",
                str(file_path),
                "--body",
                "custom body",
                "--no-path-in-body",
            ],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        args, kwargs = apprise_obj.notify.call_args
        assert "custom body" in kwargs["body"]
        assert str(file_path) not in kwargs["body"]
        assert "Notification sent" in out.out


def test_notify_body_prepend_append(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file6.txt"
    file_path.write_text("irrelevant\n")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            [
                "notify",
                "--channel",
                "foo",
                "--file",
                str(file_path),
                "--body-prepend",
                "PRE-",
                "--body-append=-POST",
            ],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        args, kwargs = apprise_obj.notify.call_args
        assert kwargs["body"].startswith("PRE-")
        assert kwargs["body"].endswith("-POST")
        assert "Notification sent" in out.out


def test_notify_title_prepend_append(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file7.txt"
    file_path.write_text("irrelevant\n")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            [
                "notify",
                "--channel",
                "foo",
                "--file",
                str(file_path),
                "--title-prepend",
                "PRE-",
                "--title-append=-POST",
            ],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        args, kwargs = apprise_obj.notify.call_args
        assert kwargs["title"].startswith("PRE-")
        assert kwargs["title"].endswith("-POST")
        assert "Notification sent" in out.out


def test_notify_max_length(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file8.txt"
    file_path.write_text("A" * 1000)
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        apprise_obj.servers = [MagicMock()]
        apprise_obj.servers[0].body_maxlen = 1000
        apprise_obj.servers[0].title_maxlen = 1000
        code = run_cli(
            [
                "notify",
                "--channel",
                "foo",
                "--file",
                str(file_path),
                "--max-length",
                "10",
            ],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        args, kwargs = apprise_obj.notify.call_args
        assert len(kwargs["body"]) == 10
        assert "Notification sent" in out.out


def test_notify_new_binary_file(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file9.bin"
    file_path.write_bytes(b"\x00\x01\x02")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        args, kwargs = apprise_obj.notify.call_args
        assert "binary" in kwargs["body"] or "unknown type" in kwargs["body"]
        assert "Notification sent" in out.out


def test_notify_changed_binary_file(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file10.bin"
    file_path.write_bytes(b"\x00\x01\x02")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
    # Change file
    file_path.write_bytes(b"\x00\x01\x03")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        args, kwargs = apprise_obj.notify.call_args
        assert "binary" in kwargs["body"] or "unknown type" in kwargs["body"]
        assert "Notification sent" in out.out


def test_notify_unchanged_binary_file(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file11.bin"
    file_path.write_bytes(b"\x00\x01\x02")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
    # Second run, no change
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        apprise_obj.notify.assert_not_called()
        assert "No change detected" in out.out


def test_notify_custom_body_binary_file(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file12.bin"
    file_path.write_bytes(b"\x00\x01\x02")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            [
                "notify",
                "--channel",
                "foo",
                "--file",
                str(file_path),
                "--body",
                "binbody",
            ],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        args, kwargs = apprise_obj.notify.call_args
        assert "binbody" in kwargs["body"]
        assert "Notification sent" in out.out


def test_notify_stdin_overwrites_file(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file13.txt"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("new from stdin\n")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdin, "read", lambda: "new from stdin\n")
    if file_path.exists():
        file_path.unlink()
    file_path.write_text("new from stdin\n")
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        args, kwargs = apprise_obj.notify.call_args
        assert "new from stdin" in kwargs["body"]
        assert "@@ -0,0 +1 @@" in kwargs["body"]
        assert "Notification sent" in out.out


def test_notify_file_used_when_no_stdin(tmp_path, monkeypatch, capsys):
    make_config(
        tmp_path,
        """
[channels]
foo = 'apprise://devnull/'
""",
    )
    file_path = tmp_path / "file14.txt"
    file_path.write_text("file content\n")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch("apprise.Apprise") as mock_apprise:
        apprise_obj = MagicMock()
        mock_apprise.return_value = apprise_obj
        apprise_obj.notify.return_value = True
        code = run_cli(
            ["notify", "--channel", "foo", "--file", str(file_path)],
            monkeypatch,
            tmp_path,
        )
        out = capsys.readouterr()
        assert code == 0
        args, kwargs = apprise_obj.notify.call_args
        assert "file content" in kwargs["body"]
        assert "Notification sent" in out.out


def test_notify_missing_required_arguments(monkeypatch, capsys):
    # No --file
    monkeypatch.setattr(sys, "argv", ["telediff", "notify", "--channel", "foo"])
    with pytest.raises(SystemExit) as excinfo:
        telediff_main()
    out = capsys.readouterr()
    assert excinfo.value.code == 2  # argparse error
    assert "usage:" in out.err or "usage:" in out.out
