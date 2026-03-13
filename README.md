# git-credential-manager

[Git Credential Manager](https://github.com/git-ecosystem/git-credential-manager) repackaged as Python wheels for easy installation via `pip` or `uv`.

## Install

```sh
uv tool install git-credential-manager
```

## Configure Git

```sh
git-credential-manager configure
```

Or manually:

```sh
git config --global credential.helper git-credential-manager
```

## Supported Platforms

| Platform | Wheel tag |
|----------|-----------|
| Linux x64 | `manylinux_2_17_x86_64` |
| Linux ARM64 | `manylinux_2_17_aarch64` |
| macOS x64 | `macosx_10_15_x86_64` |
| macOS ARM64 | `macosx_11_0_arm64` |
| Windows x64 | `win_amd64` |
| Windows ARM64 | `win_arm64` |
| Windows x86 | `win32` |

## How It Works

This package downloads the official GCM portable release archives from
[git-ecosystem/git-credential-manager](https://github.com/git-ecosystem/git-credential-manager/releases)
and repackages each `.tar.gz` / `.zip` as a platform-specific Python wheel.

A thin Python entry point (`console_scripts`) delegates to the native binary,
so `git-credential-manager` is available on `PATH` after install.

##

``` Example dev setup on Linux
tdnf install -y python3 python3-pip
python3 -m pip install uv
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
uv tool install rust-just
```

## License

This package redistributes Git Credential Manager under its
[MIT License](https://github.com/git-ecosystem/git-credential-manager/blob/main/LICENSE).
