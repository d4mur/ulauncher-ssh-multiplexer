# SSH Multiplexer for Xfce4 Terminal (Ulauncher Extension)

This Ulauncher extension enhances your SSH workflow with **Xfce4 Terminal**, allowing you to quickly launch one or more SSH sessions in separate tabs. It supports hosts defined in your `~/.ssh/config` or entered manually.

## Features

- Tailored for **Xfce4 Terminal**.
- Lists SSH hosts from your `~/.ssh/config`.
- Connect to any host in one or more terminal tabs.
- Accepts SSH hosts not defined in your config.
- Prompts for a password using `zenity` if no `IdentityFile` is configured.

## Usage

1. Open Ulauncher.
2. Type the extension keyword (default: `mssh`).
3. Select a host to connect in a single tab, or:
   - Type a number and part of a hostname (e.g., `3 myhost`) to open 3 tabs.
   - Type a number alone (e.g., `5`) to pick a host and open it in 5 tabs.
   - Type a full hostname directly (e.g., `remote.example.com`) to connect manually.

## Dependencies

This extension requires the following tools:

- `zenity`
- `sshpass`
- `xfce4-terminal`

## Installation

To install this extension:

1. Open Ulauncher.
2. Click the gear icon to open **Preferences**.
3. Go to the **Extensions** tab.
4. Click **Add Extension**.
5. Paste https://github.com/d4mur/ulauncher-ssh-multiplexer and confirm.

Ulauncher will download and activate the extension automatically.

## Configuration

You can configure the following options in the Ulauncher preferences:

- **SSH Multiplex Keyword** — Trigger word for the extension. Default: `mssh`.
- **Terminal Command** — Terminal executable. Default: `xfce4-terminal`.
- **Tab Option** — Option to open a new tab. Default: `--tab`.
- **Max SSH Tabs** — Max number of SSH connections allowed. Default: `10`.
- **Command Option** — Option to run a command in terminal. Default: `--command`.
- **SSH Command Template (password)** — Command used with `sshpass` when a password is required. Placeholders: `{password}`, `{host}`.  
  Default: `bash -c 'export SSHPASS={password}; sshpass -e ssh {host}; exec bash'`
- **SSH Command Template (no password)** — Command used when `IdentityFile` is present. Placeholder: `{host}`.  
  Default: `bash -c 'ssh {host}; exec bash'`
- **Language** — language for the labels. If not specified, system locale is used. Supported: `ar`, `de`, `en`, `es`, `fr`, `ja`, `hi`, `it`, `pl`, `pt`, `ru`, `uk`,`zh` .

## Security Notice

This extension uses `sshpass` to enable password-based SSH connections. This approach temporarily sets the password in the `SSHPASS` environment variable, which may be visible to other local processes during the execution window. While this is a common trade-off for automating SSH connections without `IdentityFile`, you should be aware of the implications on systems where multiple users have access or where untrusted processes may be running.

For improved security, it's strongly recommended to configure key-based authentication using an `IdentityFile` whenever possible.

## License

MIT
