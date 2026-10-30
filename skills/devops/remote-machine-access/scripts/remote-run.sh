#!/usr/bin/env bash
# remote-run.sh - run a LOCAL script file on a REMOTE ssh host without quote collision.
#
# Problem this solves: inlining a multi-line remote body in an ssh one-liner
# collides with ssh's own shell quoting. Any parenthesis or nested quote in the
# script dies with:
#     bash: -c: line 1: syntax error near unexpected token `('
# and each retry costs a round trip. Base64 the body and decode on the far side:
# the payload becomes quote-inert and survives any content.
#
# Usage:
#   remote-run.sh <ssh-alias> <local-script>                     # plain
#   remote-run.sh <ssh-alias> <local-script> --sudo              # sudo (keyless / NOPASSWD)
#   remote-run.sh <ssh-alias> <local-script> --sudo --pass PW    # sudo with password (expect)
#
# The script is STREAMED, never copied to disk on the remote - nothing to clean
# up afterwards. Output goes to stdout; redirect it when the caller needs to
# parse it (`remote-run.sh ... > out.txt 2>&1`), because some callers (code
# execution sandboxes in particular) do not relay a child process's stdout.
#
# Prerequisite: the host is already reachable keyless (see
# references/password-ssh-from-macos.md) and has a ~/.ssh/config alias.

set -euo pipefail

ALIAS="${1:?usage: remote-run.sh <ssh-alias> <local-script> [--sudo] [--pass PW]}"
SCRIPT="${2:?missing local script path}"
shift 2

MODE="plain"; PASS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sudo) MODE="sudo"; shift ;;
    --pass) PASS="${2:?--pass needs a value}"; MODE="sudo-pass"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$SCRIPT" ]] || { echo "no such script: $SCRIPT" >&2; exit 2; }
B64="$(base64 < "$SCRIPT" | tr -d '\n')"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"

case "$MODE" in
  plain)
    exec ssh $SSH_OPTS "$ALIAS" "echo $B64 | base64 -d | bash"
    ;;
  sudo)
    exec ssh $SSH_OPTS "$ALIAS" "echo $B64 | base64 -d | sudo bash"
    ;;
  sudo-pass)
    # macOS has no sshpass; /usr/bin/expect is always present.
    command -v expect >/dev/null || { echo "expect not found" >&2; exit 2; }
    EXP="$(mktemp -t rrun.XXXXXX.exp)"
    # Written to a file, not inlined in `expect -c`: an inline expect program hits
    # the very quoting problem this wrapper exists to avoid.
    cat > "$EXP" <<'EXPEOF'
#!/usr/bin/expect -f
set timeout 600
set alias [lindex $argv 0]
set b64   [lindex $argv 1]
set pass  [lindex $argv 2]
spawn ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 $alias \
  "echo $b64 | base64 -d | sudo -S -p PWPROMPT bash"
expect {
  -re "PWPROMPT"        { send "$pass\r"; exp_continue }
  -re "(?i)assword:"    { send "$pass\r"; exp_continue }
  eof
}
EXPEOF
    chmod +x "$EXP"
    trap 'rm -f "$EXP"' EXIT
    exec "$EXP" "$ALIAS" "$B64" "$PASS"
    ;;
esac
