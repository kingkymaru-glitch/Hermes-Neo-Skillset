# Logging into a remote box with a password, from macOS

Use when sshd advertises `publickey,password` and the user has handed over the login.
Goal: use the password ONCE, leave a key behind, never need it again.

macOS has no `sshpass`. `/usr/bin/expect` is present — use it. Do not install anything to
solve this.

## Recipe 1 — probe one username, fail fast

```expect
#!/usr/bin/expect -f
set timeout 12
set user [lindex $argv 0]
set host [lindex $argv 1]
set pass [lindex $argv 2]
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/kh_probe \
  -o PreferredAuthentications=password -o PubkeyAuthentication=no \
  -o NumberOfPasswordPrompts=1 -o ConnectTimeout=8 $user@$host \
  "echo ===MARK===; hostname; whoami"
expect {
  -re "(?i)assword:"     { send "$pass\r"; exp_continue }
  -re "===MARK==="       { puts "\n>>> $user LOGIN SUCCESS"; exp_continue }
  -re "(?i)permission denied" { puts "\n>>> $user AUTH_FAIL"; exit 2 }
  timeout                { puts "\n>>> $user TIMEOUT"; exit 3 }
  eof
}
```

- `NumberOfPasswordPrompts=1` + one username per invocation: the sshd default is three
  attempts per connection, and a naive `for` loop can burn enough failures to lock the
  account. One guess, one connection.
- Drive the loop from the shell and grep the output for `>>>`, rather than trying to
  accumulate state inside expect — see the pitfall below.

## Recipe 2 — run a command with sudo

```expect
spawn ssh ... $user@$host "sudo -S -p PWPROMPT id 2>&1; echo EXIT=\$?"
expect {
  -re "(?i)$user@.*assword:" { send "$pass\r"; exp_continue }   # ssh's own prompt
  -re "PWPROMPT"               { send "$pass\r"; exp_continue }   # sudo's prompt
  eof
}
```

`sudo -S` reads the password from stdin and `-p` sets the prompt. Both prompts land in the
same expect stream, so the sudo prompt MUST be a distinctive string; matching a bare
`assword:` for both would answer sudo with the ssh password again and loop.

## Recipe 3 — install the key, then go keyless

Generate once on the Mac, then append the public half via an authenticated session:

```bash
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -C "neo@<mac-host>" -f ~/.ssh/id_ed25519
```

Remote command (idempotent — `grep -qF` before appending, or you stack duplicates):

```sh
mkdir -p ~/.ssh && chmod 700 ~/.ssh
grep -qF '<pubkey>' ~/.ssh/authorized_keys 2>/dev/null || echo '<pubkey>' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Then add an alias so later calls are just `ssh pc2`:

```
Host pc2
  HostName <ip>
  User pc2
  IdentityFile ~/.ssh/id_ed25519
  StrictHostKeyChecking accept-new
```

`chmod 600 ~/.ssh/config` — ssh ignores a group/world-writable config.

Prove it keyless with `ssh -o BatchMode=yes <alias> "echo KEYLESS_OK"`. `BatchMode` refuses
to prompt, so a printed marker is real proof; anything else means the key did not land.

## Pitfalls

- **A password-sudo wrapper can outlive its output and appear to hang.** With `ssh -tt` the
  remote shell may not close promptly after the script finishes (motd, profile, a lingering
  child), so an expect block waiting on `eof` sits until its timeout even though the work is
  done. For a long install: launch it in the background with a log file, then verify the
  RESULT on the box (`command -v`, `--version`, `systemctl is-active`) instead of waiting on
  the wrapper. Kill the stray expect once you stop waiting, and re-check the real state — the
  frozen local log is not evidence of a frozen install.
- **Test for passwordless sudo first.** `sudo -n true` costs one call; if it succeeds there
  is no reason to write an expect flow at all.
- **Do not try to buffer `expect_out` across `exp_continue`.** A script that appends
  `$expect_out(0,string)` inside the expect block and prints the buffer at the end reports
  an empty string even on success — the buffer is not carried the way it looks. Print a
  fixed line when the marker matches, and do the text processing in the shell afterwards.
- **`log_user 0` hides everything, including your own result.** It is the right way to keep
  the password out of the transcript, but you must flip it back with `log_user 1` before
  printing anything you want to read.
- **Write the expect script to a file and run it.** Multi-line expect programs inlined in a
  shell one-liner lose their quoting; `/tmp/x.exp` + `chmod +x` is what actually works.
- **A password handed over in chat is a finding, not a solution.** Say once, plainly, that
  it is weak and may be live on other tailnet boxes — one sentence, not a lecture. Then
  check whether it is the same password as sudo, and whether the login user is in the
  `sudo` group; both usually true, and both worth naming.
- **Do not change the password or system config on your own initiative.** Report the risk
  and let the user decide.
