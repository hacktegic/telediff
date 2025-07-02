import argparse
import os
import shutil
import apprise
import difflib
import sys
from telediff import util


# Color and emoji helpers
class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def colorize(text, color, no_color):
    if no_color:
        return text
    return f"{color}{text}{Color.RESET}"


def emoji(label, no_color):
    if no_color:
        return ""
    emojis = {
        "success": "✅ ",
        "fail": "❌ ",
        "info": "ℹ️ ",
        "diff": "📝 ",
        "binary": "📦 ",
        "nochange": "🟢 ",
        "cache": "🗑️ ",
    }
    return emojis.get(label, "")


def main():
    parser = argparse.ArgumentParser(
        prog="telediff",
        description="Send notifications if a file/stream changes (with diff tracking in ~/.cache).",
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Subcommands"
    )

    # test command
    test_parser = subparsers.add_parser(
        "test", help="Send a test notification for a channel"
    )
    test_parser.add_argument("--channel", "-c", required=True, help="Channel to test")
    test_parser.add_argument(
        "--title",
        "-t",
        default="telediff test",
        help="Title for test notification (default: 'telediff test')",
    )
    test_parser.set_defaults(func=cmd_test)

    # clear-cache command
    clear_cache_parser = subparsers.add_parser(
        "clear-cache", help="Remove all cached state"
    )
    clear_cache_parser.set_defaults(func=cmd_clear_cache)

    # notify command
    notify_parser = subparsers.add_parser(
        "notify", help="Send notification if file/stream changes"
    )
    notify_parser.add_argument(
        "--channel", "-c", required=True, help="Channel to send notification to"
    )
    notify_parser.add_argument(
        "--title",
        "-t",
        default="telediff update",
        help="Title for notification (default: 'telediff update')",
    )
    notify_parser.add_argument(
        "--body",
        "-b",
        default=None,
        help="Body for notification (default: file contents or diff)",
    )
    notify_parser.add_argument(
        "--body-prepend",
        default="",
        help="Text to prepend to the notification body (default: empty)",
    )
    notify_parser.add_argument(
        "--body-append",
        default="",
        help="Text to append to the notification body (default: empty)",
    )
    notify_parser.add_argument(
        "--title-prepend",
        default="",
        help="Text to prepend to the notification title (default: empty)",
    )
    notify_parser.add_argument(
        "--title-append",
        default="",
        help="Text to append to the notification title (default: empty)",
    )
    notify_parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="Path to the file to monitor for changes. If the file does not exist, contents of STDIN are taken and written to this path. If STDIN is provided, it always replaces the file contents. Notification is sent if the file (or STDIN) changes compared to the cached copy.",
    )
    notify_parser.add_argument(
        "--max-length",
        type=int,
        default=0,
        help="Max body length (default: 0=channel-specific limit)",
    )
    notify_parser.add_argument(
        "--no-path-in-body",
        action="store_true",
        help="Do not include the file path in the notification body",
    )
    notify_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored and emoji output for this notification",
    )
    notify_parser.add_argument(
        "--attach",
        action="store_true",
        help="Attach the diff as a file if supported by the channel (text files only)",
    )
    notify_parser.set_defaults(func=cmd_notify)

    # create-config command
    create_config_parser = subparsers.add_parser(
        "create-config", help="Create the default config file and output its location"
    )
    create_config_parser.set_defaults(func=cmd_create_config)

    args = parser.parse_args()
    try:
        args.func(args)
        sys.exit(0)
    except SystemExit as e:
        # Allow explicit sys.exit() to propagate
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_test(args):
    try:
        url = util.get_channel_url(args.channel)
    except Exception as e:
        print(
            colorize(emoji("fail", False) + f"Error: {e}", Color.RED, False),
            file=sys.stderr,
        )

        sys.exit(1)
    apobj = apprise.Apprise()
    apobj.add(url)
    title = args.title
    body = "This is a test notification from telediff."
    success = apobj.notify(title=title, body=body)
    if success:
        print(
            colorize(
                emoji("success", False)
                + f"Test notification sent to channel '{args.channel}'.",
                Color.GREEN,
                False,
            )
        )
        sys.exit(0)
    else:
        print(
            colorize(
                emoji("fail", False)
                + f"Failed to send notification to channel '{args.channel}'.",
                Color.RED,
                False,
            ),
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_clear_cache(args):
    cache_dir = util.get_cache_path()
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        print(
            colorize(
                emoji("cache", False) + f"Cleared telediff cache at {cache_dir}",
                Color.GREEN,
                False,
            )
        )
        sys.exit(0)
    else:
        print(
            colorize(
                emoji("info", False) + f"No cache found at {cache_dir}",
                Color.YELLOW,
                False,
            )
        )
        sys.exit(0)


def cmd_notify(args):
    no_color = getattr(args, "no_color", False)
    try:
        url = util.get_channel_url(args.channel)
    except Exception as e:
        print(
            colorize(emoji("fail", no_color) + f"Error: {e}", Color.RED, no_color),
            file=sys.stderr,
        )

        sys.exit(1)
    apobj = apprise.Apprise()
    apobj.add(url)
    file_path = os.path.abspath(args.file)
    file_display = f"File: {file_path}\n" if not args.no_path_in_body else ""
    cache_dir = util.get_cache_path()
    cache_name = util.cache_file_name(args.channel, file_path)
    cache_file = os.path.join(cache_dir, cache_name)

    # Determine channel limit safely
    channel_limit = 1600
    attachment_support = False
    title_support = True
    if getattr(apobj, "servers", None) and len(apobj.servers) > 0:
        channel_limit = getattr(apobj.servers[0], "body_maxlen", 1600)
        attachment_support = getattr(apobj.servers[0], "attachment_support", False)
        title_support = getattr(apobj.servers[0], "title_maxlen", 0) > 0
    max_length = args.max_length

    if max_length < 1:
        max_length = channel_limit
    elif max_length > channel_limit:
        print(
            colorize(
                emoji("fail", Color.YELLOW)
                + f"Max length {args.max_length} exceeds channel limit "
                f"{channel_limit}. Adjusting to {channel_limit}.",
                Color.RED,
                no_color,
            ),
            file=sys.stderr,
        )
        max_length = channel_limit

    body_prepend = args.body_prepend or ""
    body_append = args.body_append or ""
    title_prepend = args.title_prepend or ""
    title_append = args.title_append or ""
    # Prioritize stdin if not a tty
    if not sys.stdin.isatty():
        content = sys.stdin.read()
        # Always update the file with stdin content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    is_text = util.is_text_file(file_path)
    # Read file content as text or bytes
    if is_text:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    else:
        with open(file_path, "rb") as f:
            content_bytes = f.read()
    # Helper to maybe attach diff
    import tempfile

    def maybe_attachment(diff_text):
        if args.attach and attachment_support and is_text and diff_text:
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=".txt", mode="w", encoding="utf-8"
            )
            tmp.write(diff_text)
            tmp.close()
            return tmp.name
        return None

    # If no cache, only send contents if text, otherwise send generic message
    if not os.path.exists(cache_file):
        if args.body is not None:
            msg = file_display + args.body if file_display else args.body
            attachments = None
        elif is_text:
            # Show diff from empty string
            diff = difflib.unified_diff(
                [],
                content.splitlines(),
                fromfile="previous",
                tofile="current",
                lineterm="",
            )
            diff_text = "\n".join(diff)
            msg = file_display + diff_text
            attachments = maybe_attachment(diff_text)
        else:
            msg = file_display + (
                emoji("binary", no_color) + "File created (binary or unknown type)."
                if not no_color
                else "File created (binary or unknown type)."
            )
            attachments = None
        msg = body_prepend + msg + body_append
        notify_title = title_prepend + args.title + title_append
        if not title_support:
            max_length -= len(notify_title) * 2
        if max_length > 0:
            msg = msg[:max_length]
        notify_kwargs = dict(title=notify_title, body=msg)
        if attachments:
            notify_kwargs["attach"] = attachments
        sent = apobj.notify(**notify_kwargs)
        if not sent and attachments:
            sent = apobj.notify(title=notify_title, body=msg)
        if sent:
            print(
                colorize(
                    emoji("success", no_color)
                    + f"Notification sent (new file) to channel '{args.channel}'.",
                    Color.GREEN,
                    no_color,
                )
            )
            if is_text:
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(cache_file, "wb") as f:
                    f.write(content_bytes)
            sys.exit(0)
        else:
            print(
                colorize(
                    emoji("fail", no_color)
                    + f"Failed to send notification to channel '{args.channel}'.",
                    Color.RED,
                    no_color,
                ),
                file=sys.stderr,
            )
            sys.exit(1)
    # If file is text, diff
    if is_text:
        with open(cache_file, "r", encoding="utf-8", errors="replace") as f:
            cached = f.read()
        if cached != content:
            diff = difflib.unified_diff(
                cached.splitlines(),
                content.splitlines(),
                fromfile="previous",
                tofile="current",
                lineterm="",
            )
            diff_text = "\n".join(diff)
            if args.body is not None:
                msg = file_display + args.body if file_display else args.body
                attachments = None
            else:
                msg = file_display + (
                    emoji("diff", no_color) + diff_text if not no_color else diff_text
                )
                attachments = maybe_attachment(diff_text)
            msg = body_prepend + msg + body_append
            notify_title = title_prepend + args.title + title_append
            if max_length > 0:
                msg = msg[:max_length]
            notify_kwargs = dict(title=notify_title, body=msg)
            if attachments:
                notify_kwargs["attach"] = attachments
            sent = apobj.notify(**notify_kwargs)
            if not sent and attachments:
                sent = apobj.notify(title=notify_title, body=msg)
            if sent:
                print(
                    colorize(
                        emoji("success", no_color)
                        + f"Notification sent (diff) to channel '{args.channel}'.",
                        Color.GREEN,
                        no_color,
                    )
                )
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(content)
                sys.exit(0)
            else:
                print(
                    colorize(
                        emoji("fail", no_color)
                        + f"Failed to send notification to channel '{args.channel}'.",
                        Color.RED,
                        no_color,
                    ),
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print(
                colorize(
                    emoji("nochange", no_color)
                    + "No change detected; no notification sent.",
                    Color.CYAN,
                    no_color,
                )
            )
            sys.exit(0)
    else:
        # Not a text file, compare bytes
        with open(cache_file, "rb") as f:
            cached_bytes = f.read()
        if cached_bytes != content_bytes:
            if args.body is not None:
                msg = file_display + args.body if file_display else args.body
            else:
                msg = file_display + (
                    emoji("binary", no_color) + "File changed (binary or unknown type)."
                    if not no_color
                    else "File changed (binary or unknown type)."
                )
            msg = body_prepend + msg + body_append
            notify_title = title_prepend + args.title + title_append
            if not title_support:
                max_length -= len(notify_title) * 2
            if max_length > 0:
                msg = msg[:max_length]
            sent = apobj.notify(title=notify_title, body=msg)
            if sent:
                print(
                    colorize(
                        emoji("success", no_color)
                        + f"Notification sent (binary/unknown) to channel '{args.channel}'.",
                        Color.GREEN,
                        no_color,
                    )
                )
                with open(cache_file, "wb") as f:
                    f.write(content_bytes)
                sys.exit(0)
            else:
                print(
                    colorize(
                        emoji("fail", no_color)
                        + f"Failed to send notification to channel '{args.channel}'.",
                        Color.RED,
                        no_color,
                    ),
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print(
                colorize(
                    emoji("nochange", no_color)
                    + "No change detected; no notification sent.",
                    Color.CYAN,
                    no_color,
                )
            )
            sys.exit(0)


def cmd_create_config(args):
    config_dir = util.get_config_path()
    config_file = os.path.join(config_dir, "config.toml")

    if os.path.exists(config_file):
        print(
            colorize(
                emoji("fail", False)
                + f"Config file already exists at {config_file} , skipping creation.",
                Color.RED,
                False,
            )
        )
        sys.exit(1)

    config_file = util.ensure_config_file()
    print(
        colorize(
            emoji("success", False) + f"Config file created at {config_file}",
            Color.GREEN,
            False,
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
