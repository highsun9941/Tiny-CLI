#!/usr/bin/env bash
# 이름이 같은 PyPI 패키지와 혼동하지 않도록 이 저장소의 소스에서 설치한다.
# 명령 실패·미정의 변수·파이프 중간 실패를 감지해 불완전한 설치를 성공으로 보고하지 않는다.
set -euo pipefail

tiny_install_error() {
    # 오류는 stderr로 보내 파이프나 호출 스크립트가 일반 출력과 구분할 수 있게 한다.
    printf 'Tiny-CLI: %s\n' "$*" >&2
    exit 1
}

tiny_install_main() {
    # 사용자 영역을 기본값으로 삼아 sudo 없이 설치한다. 재설치도 같은 경로를 사용한다.
    local tiny_ref="${TINY_CLI_REF:-main}"
    local tiny_install_dir="${TINY_CLI_INSTALL_DIR:-${HOME}/.local/share/tiny-cli}"
    local tiny_bin_dir="${TINY_CLI_BIN_DIR:-${HOME}/.local/bin}"
    local tiny_uv tiny_source tiny_temp

    # CLI의 --ref가 환경변수보다 우선한다. 도움말은 다운로드·디렉터리 생성 전에 처리한다.
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --ref)
                [ "$#" -ge 2 ] || tiny_install_error '--ref requires a branch, tag, or commit.'
                tiny_ref="$2"
                shift 2
                ;;
            -h|--help)
                # 인용한 heredoc 구분자로 도움말 안의 내용을 셸이 확장하지 않게 한다.
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

    # 지원하는 셸 환경과 필요한 다운로드 명령을 먼저 확인한다. WSL은 Linux로 판별된다.
    case "$(uname -s)" in
        Linux|Darwin) ;;
        *) tiny_install_error 'Use Linux, macOS, or WSL. See README for source installation.' ;;
    esac
    command -v curl >/dev/null 2>&1 || tiny_install_error 'curl is required.'
    # ref를 아카이브 URL에 넣으므로 허용 문자를 제한하고 상위 경로 표기를 거절한다.
    [[ "$tiny_ref" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]] && [[ "$tiny_ref" != *..* ]] \
        || tiny_install_error 'Invalid Git ref.'
    # 실행 위치에 따라 설치 대상이 달라지지 않도록 절대 경로를 요구한다.
    [[ "$tiny_install_dir" = /* && "$tiny_bin_dir" = /* ]] \
        || tiny_install_error 'Install and bin directories must be absolute paths.'

    mkdir -p "$tiny_install_dir" "$tiny_bin_dir"
    # 심볼릭 링크 등을 해소한 경로로 맞춰 uv의 설치 기록과 실행 경로를 재설치 때도 일치시킨다.
    tiny_install_dir="$(cd "$tiny_install_dir" && pwd -P)"
    tiny_bin_dir="$(cd "$tiny_bin_dir" && pwd -P)"

    # 이전에 준비한 전용 uv → PATH의 uv → 새 다운로드 순서로 불필요한 설치를 줄인다.
    if [ -x "$tiny_install_dir/uv/uv" ]; then
        tiny_uv="$tiny_install_dir/uv/uv"
    elif command -v uv >/dev/null 2>&1; then
        tiny_uv="$(command -v uv)"
    else
        printf 'Installing uv for Tiny-CLI...\n'
        tiny_temp="$(mktemp -d)"
        # EXIT 시점에는 지역변수 수명이 끝날 수 있어 임시 경로를 지금 인용해 trap에 넣는다.
        # 성공·실패 모두 다운로드한 임시 설치 파일을 정리한다.
        trap "rm -rf -- $(printf '%q' "$tiny_temp")" EXIT
        # 먼저 파일로 내려받아 curl 성공을 확인한 뒤 실행한다. 실패한 다운로드를 실행하지 않는다.
        curl --proto '=https' --tlsv1.2 -fsSL https://astral.sh/uv/install.sh \
            -o "$tiny_temp/uv-install.sh" \
            || tiny_install_error 'Could not download uv. Check your connection and try again.'
        # uv를 프로젝트 전용 경로에 두고 셸 프로필은 수정하지 않도록 설치 위치를 지정한다.
        UV_UNMANAGED_INSTALL="$tiny_install_dir/uv" sh "$tiny_temp/uv-install.sh" \
            || tiny_install_error 'Could not install uv.'
        tiny_uv="$tiny_install_dir/uv/uv"
        [ -x "$tiny_uv" ] || tiny_install_error 'The uv installer did not produce an executable.'
    fi

    # Git 명령이 없는 환경에서도 브랜치·태그·커밋의 소스를 받을 수 있도록 아카이브를 사용한다.
    tiny_source="https://github.com/highsun9941/Tiny-CLI/archive/${tiny_ref}.tar.gz"
    printf 'Installing Tiny-CLI (%s)...\n' "$tiny_ref"
    # Python과 도구 환경을 다른 uv 애플리케이션과 분리한다.
    # --no-config로 주변 uv 설정의 영향을 줄이고 --managed-python으로 Python 3.12를 준비한다.
    # --reinstall은 업데이트를 반영한다. --force를 쓰지 않아 다른 tiny 명령의 덮어쓰기는 uv가 거절한다.
    UV_TOOL_DIR="$tiny_install_dir/tools" \
    UV_TOOL_BIN_DIR="$tiny_bin_dir" \
    UV_PYTHON_INSTALL_DIR="$tiny_install_dir/python" \
    "$tiny_uv" --no-config tool install --python 3.12 --managed-python \
        --reinstall "$tiny_source" \
        || tiny_install_error 'Installation failed. If tiny already exists, remove it with its original installer or choose TINY_CLI_BIN_DIR.'

    # API 키가 필요 없는 도움말 실행으로 설치된 진입점이 실제로 시작되는지 확인한다.
    "$tiny_bin_dir/tiny" --help >/dev/null \
        || tiny_install_error 'The installed tiny command could not start.'
    printf '\nTiny-CLI is installed: %s/tiny\n' "$tiny_bin_dir"
    # PATH의 항목 경계를 함께 비교해 경로 일부만 겹치는 경우를 구분한다.
    # 셸 프로필을 자동 수정하지 않고, 필요한 경우 인용된 export 명령을 안내한다.
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

# 파이프로 읽을 때도 함수 정의를 모두 받은 뒤 설치를 시작하도록 호출을 맨 끝에 둔다.
tiny_install_main "$@"
