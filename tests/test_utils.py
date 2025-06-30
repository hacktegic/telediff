import os
import pytest
from telediff import util


def test_is_text_file_with_text(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("hello world\nthis is a test\n")
    assert util.is_text_file(str(file_path)) is True


def test_is_text_file_with_binary(tmp_path):
    file_path = tmp_path / "test.bin"
    file_path.write_bytes(b"\x00\x01\x02\x03\x04")
    assert util.is_text_file(str(file_path)) is False


def test_cache_file_name_unique():
    name1 = util.cache_file_name("chan1", "/tmp/foo.txt")
    name2 = util.cache_file_name("chan2", "/tmp/foo.txt")
    name3 = util.cache_file_name("chan1", "/tmp/bar.txt")
    assert name1 != name2
    assert name1 != name3
    assert len(name1) == 64


# get_config_path and get_cache_path create dirs, but return the actual user dirs, so just check they exist


def test_get_config_path_and_cache_path_exist():
    config_dir = util.get_config_path()
    cache_dir = util.get_cache_path()
    assert os.path.isdir(config_dir)
    assert os.path.isdir(cache_dir)


def test_ensure_config_file_creates_file():
    config_file = util.ensure_config_file()
    assert os.path.isfile(config_file)
    with open(config_file) as f:
        content = f.read()
    assert "[channels]" in content


def test_load_channels_config_and_get_channel_url(tmp_path, monkeypatch):
    monkeypatch.setattr(util, "user_config_dir", lambda app: str(tmp_path / "config"))
    config_dir = util.get_config_path()
    config_file = os.path.join(config_dir, "config.toml")
    with open(config_file, "w") as f:
        f.write(
            """
[channels]
foo = 'apprise://url1'
bar = 'apprise://url2'
"""
        )
    channels = util.load_channels_config()
    assert channels["foo"] == "apprise://url1"
    assert channels["bar"] == "apprise://url2"
    assert util.get_channel_url("foo") == "apprise://url1"
    with pytest.raises(KeyError):
        util.get_channel_url("baz")


def test_load_channels_config_invalid(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = util.get_config_path()
    config_file = os.path.join(config_dir, "config.toml")
    with open(config_file, "w") as f:
        f.write("[notchannels]\nfoo = 'bar'\n")
    with pytest.raises(ValueError):
        util.load_channels_config()


def test_load_channels_config_malformed(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = util.get_config_path()
    config_file = os.path.join(config_dir, "config.toml")
    with open(config_file, "w") as f:
        f.write("not a toml file at all")
    with pytest.raises(RuntimeError):
        util.load_channels_config()


def test_is_text_file(tmp_path):
    text_file = tmp_path / "foo.txt"
    text_file.write_text("hello\nworld\n")
    bin_file = tmp_path / "foo.bin"
    bin_file.write_bytes(b"\x00\x01\x02")
    assert util.is_text_file(str(text_file))
    assert not util.is_text_file(str(bin_file))
