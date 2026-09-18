#!/usr/bin/env bash
# Install from this repository, never from the unrelated PyPI tiny-cli package.
set -euo pipefail

tiny_install_error() {
    printf 'Tiny-CLI: %s\n' "$*" >&2
    exit 1
}

tiny_install_main() {
    local tiny_ref="${TINY_CLI_REF:-main}"
    local tiny_install_dir="${TINY_CLI_INSTALL_DIR:-${HOME}/.local/share/tiny-cli}"
    local tiny_bin_dir="${TINY_CLI_BIN_DIR:-${HOME}/.local/bin}"
    local tiny_uv tiny_source tiny_temp

    while [ "$#" -gt 0 ]; do
        case "$1" in
            --ref)
                [ "$#" -ge 2 ] || tiny_install_error '--ref requires a branch, tag, or commit.'
                tiny_ref="$2"
                shift 2
                ;;
            -h|--help)
                cat <<'USAGE'
Usage: bash install.sh [--ref BRANCH_TAG_OR_COMMIT]

Installs Tiny-CLI for Linux, macOS, or WSL using uv and Python 3.12.
If needed, uv and Python are downloaded automatically. No sudo is used.
Run the same command again to update. Shell profiles are not modified.

Environment:
  TINY_CLI_REF          Git ref to install (default: main)
  TINY_CLI_INSTALL_DIR  Runtime directory (default: ~/.local/share/tiny-cli)
  TINY_CLI_BIN_DIR      Command directory (default: ~/.local/bin)
USAGE
                return
                ;;
            *) tiny_install_error "Unknown option: $1 (see --help)." ;;
        esac
    done

    case "$(uname -s)" in
        Linux|Darwin) ;;
        *) tiny_install_error 'Use Linux, macOS, or WSL. See README for source installation.' ;;
    esac
    command -v curl >/dev/null 2>&1 || tiny_install_error 'curl is required.'
    [[ "$tiny_ref" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]] && [[ "$tiny_ref" != *..* ]] \
        || tiny_install_error 'Invalid Git ref.'
    [[ "$tiny_install_dir" = /* && "$tiny_bin_dir" = /* ]] \
        || tiny_install_error 'Install and bin directories must be absolute paths.'

    mkdir -p "$tiny_install_dir" "$tiny_bin_dir"
    # Canonical paths keep uv receipts and launchers stable across reinstallations.
    tiny_install_dir="$(cd "$tiny_install_dir" && pwd -P)"
    tiny_bin_dir="$(cd "$tiny_bin_dir" && pwd -P)"

    if [ -x "$tiny_install_dir/uv/uv" ]; then
        tiny_uv="$tiny_install_dir/uv/uv"
    elif command -v uv >/dev/null 2>&1; then
        tiny_uv="$(command -v uv)"
    else
        printf 'Installing uv for Tiny-CLI...\n'
        tiny_temp="$(mktemp -d)"
        # Expand the local path now; the EXIT trap runs after this function returns.
        trap "rm -rf -- $(printf '%q' "$tiny_temp")" EXIT
        curl --proto '=https' --tlsv1.2 -fsSL https://astral.sh/uv/install.sh \
            -o "$tiny_temp/uv-install.sh" \
            || tiny_install_error 'Could not download uv. Check your connection and try again.'
        UV_UNMANAGED_INSTALL="$tiny_install_dir/uv" sh "$tiny_temp/uv-install.sh" \
            || tiny_install_error 'Could not install uv.'
        tiny_uv="$tiny_install_dir/uv/uv"
        [ -x "$tiny_uv" ] || tiny_install_error 'The uv installer did not produce an executable.'
    fi

    tiny_source="https://github.com/highsun9941/Tiny-CLI/archive/${tiny_ref}.tar.gz"
    printf 'Installing Tiny-CLI (%s)...\n' "$tiny_ref"
    # Keep this application's tool environment separate from other uv tools.
    # uv refuses to overwrite an unrelated existing `tiny` executable.
    UV_TOOL_DIR="$tiny_install_dir/tools" \
    UV_TOOL_BIN_DIR="$tiny_bin_dir" \
    UV_PYTHON_INSTALL_DIR="$tiny_install_dir/python" \
    "$tiny_uv" --no-config tool install --python 3.12 --managed-python \
        --reinstall "$tiny_source" \
        || tiny_install_error 'Installation failed. If tiny already exists, remove it with its original installer or choose TINY_CLI_BIN_DIR.'

    "$tiny_bin_dir/tiny" --help >/dev/null \
        || tiny_install_error 'The installed tiny command could not start.'
    printf '\nTiny-CLI is installed: %s/tiny\n' "$tiny_bin_dir"
    case ":${PATH}:" in
        *":${tiny_bin_dir}:"*) printf 'Run: tiny\n' ;;
        *)
            printf 'Add the command directory to PATH in your shell. For bash/zsh:\n'
            printf '  export PATH=%q:"$PATH"\n' "$tiny_bin_dir"
            printf 'Then run: tiny\n'
            printf 'Add that export to your shell profile to keep it in future sessions.\n'
            ;;
    esac
    printf 'Configure a provider in ~/.config/tiny-cli/config.toml or set an API key.\n'
}

# Keep execution at the end so the script also works when piped into bash.
tiny_install_main "$@"
