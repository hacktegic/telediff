import hashlib
from platformdirs import user_config_dir, user_cache_dir
import os
import tomllib
import mimetypes

APP_NAME = "telediff"
DEFAULT_CONFIG = """[channels]
# Format: user_friendly_channel_name = apprise_url
#
# The value is an Apprise URL (see https://github.com/caronc/apprise/wiki for all supported services).
#
# You do not need to pay for Apprise, and your messages do not go through them; it's just a library providing abstraction.
#
# Examples:
#
# telegramexample = "tgram://bottoken/ChatID"

# slackexample = "slack://TokenA/TokenB/TokenC/"

# msteamsexample = "msteams://TokenA/TokenB/TokenC/"

# pushoverexample = "pover://user@token"
"""


def get_config_path():
    """Return the path to the config directory, creating it if needed."""
    path = user_config_dir(APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def get_cache_path():
    """Return the path to the cache directory, creating it if needed."""
    path = user_cache_dir(APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def cache_file_name(channel: str, file_path: str) -> str:
    """Return a sha256-based cache file name for a channel and file path."""
    h = hashlib.sha256()
    h.update(channel.encode("utf-8"))
    h.update(file_path.encode("utf-8"))
    return h.hexdigest()


def ensure_config_file():
    """Ensure the config file exists, creating it with a default template if not."""
    config_dir = get_config_path()
    config_file = os.path.join(config_dir, "config.toml")
    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            f.write(DEFAULT_CONFIG)
    return config_file


def load_channels_config():
    """Load the [channels] section from the TOML config file and return a dict of channel name to Apprise URL."""
    config_file = ensure_config_file()
    try:
        with open(config_file, "rb") as f:
            config = tomllib.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to parse config file: {e}")
    if "channels" not in config or not isinstance(config["channels"], dict):
        raise ValueError("[channels] section missing or not a table in config.toml")
    return config["channels"]


def get_channel_url(channel_name: str) -> str:
    """Return the Apprise URL for a given channel name, or raise KeyError if not found."""
    channels = load_channels_config()
    url = channels.get(channel_name)
    if not url:
        raise KeyError(f"Channel '{channel_name}' not found in config.")
    return url


def is_text_file(filepath, chunk_size=2048):
    """Determine if a file is text by mime type, null bytes, and utf-8 decode check on the first chunk_size bytes."""
    mime, _ = mimetypes.guess_type(filepath)
    if mime and mime.startswith("text/"):
        return True
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(chunk_size)
            if b"\0" in chunk:
                return False
            chunk.decode("utf-8")
        return True
    except Exception:
        return False
