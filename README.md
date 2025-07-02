# telediff

![](telediff.gif)

Telediff is a CLI tool to send notifications when a file (or the output of your script) changes, with diff tracking and many notification channels (including Slack, WhatsApp, Telegram, Google Chat, Microsoft Teams, Pushover and [100+ others](https://github.com/caronc/apprise/wiki))

## Installation

### With pipx
```sh
pipx install telediff
```

### With uv
```sh
uv tool install telediff
```

### With docker

```sh
docker run --rm \
  -v "$HOME/.config/telediff:/app/.config/telediff" \
  -v "$HOME/.cache/telediff:/app/.cache/telediff" \
  ghcr.io/hacktegic/telediff:latest telediff --help
```

## Configuration

Run `telediff create-config` to create the default config and print its path.

Default config looks like this:

```toml
[channels]
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
```

You can use `telediff test -c yourchannel` to send a test notification.

## Usage


```
telediff --help
usage: telediff [-h] {test,clear-cache,notify,create-config} ...

Send notifications if a file/stream changes (with diff tracking in ~/.cache).

positional arguments:
  {test,clear-cache,notify,create-config}
                        Subcommands
    test                Send a test notification for a channel
    clear-cache         Remove all cached state
    notify              Send notification if file/stream changes
    create-config       Create the default config file and output its location

options:
  -h, --help            show this help message and exit
```

### telediff notify

```
telediff notify --help
usage: telediff notify [-h] --channel CHANNEL [--title TITLE] [--body BODY]
                       [--body-prepend BODY_PREPEND]
                       [--body-append BODY_APPEND]
                       [--title-prepend TITLE_PREPEND]
                       [--title-append TITLE_APPEND] --file FILE
                       [--max-length MAX_LENGTH] [--no-path-in-body]
                       [--no-color] [--attach]

options:
  -h, --help            show this help message and exit
  --channel, -c CHANNEL
                        Channel to send notification to
  --title, -t TITLE     Title for notification (default: 'telediff update')
  --body, -b BODY       Body for notification (default: file contents or diff)
  --body-prepend BODY_PREPEND
                        Text to prepend to the notification body (default:
                        empty)
  --body-append BODY_APPEND
                        Text to append to the notification body (default:
                        empty)
  --title-prepend TITLE_PREPEND
                        Text to prepend to the notification title (default:
                        empty)
  --title-append TITLE_APPEND
                        Text to append to the notification title (default:
                        empty)
  --file, -f FILE       Path to the file to monitor for changes. If the file
                        does not exist, contents of STDIN are taken and
                        written to this path. If STDIN is provided, it always
                        replaces the file contents. Notification is sent if
                        the file (or STDIN) changes compared to the cached
                        copy.
  --max-length MAX_LENGTH
                        Max body length (default: 0=channel-specific limit)
  --no-path-in-body     Do not include the file path in the notification body
  --no-color            Disable colored and emoji output for this notification
  --attach              Attach the diff as a file if supported by the channel
                        (text files only)
```

### telediff test

```
telediff test --help
usage: telediff test [-h] --channel CHANNEL [--title TITLE]

options:
  -h, --help            show this help message and exit
  --channel, -c CHANNEL
                        Channel to test
  --title, -t TITLE     Title for test notification (default: 'telediff test')
```