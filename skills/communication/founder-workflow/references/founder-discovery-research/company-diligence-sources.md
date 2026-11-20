# Company / Project Diligence From Public Sources

For "who owns X", "background of these founders", "find all about <project>", "is this thing
real / live / dead". The job is not to summarise the marketing page — it is to establish what is
true now and separate it from what the company says about itself.

## Three classes of claim — never blend them

1. **Self-description** — the company site, docs, announcements, model cards.
2. **Third-party repetition** — press, Wikipedia, Crunchbase-style directories, AI-generated
   profile sites. These copy each other and lag reality by months.
3. **Live state** — registries, chains, repo activity, model registries, DNS. This one wins
   every conflict.

Answer from (3) where it exists, cite (1) for intent, and say out loud when (2) disagrees.
A diligence answer built only from (1) and (2) is a press release with extra steps.

## Probes, cheapest first

**GitHub org** — `curl -s https://api.github.com/orgs/<org>` gives `created_at`, `followers`,
`public_repos`, `blog`, `twitter_username`. Then:

```bash
curl -s "https://api.github.com/orgs/<org>/repos?per_page=100&sort=updated"   # stars, forks, pushed_at, license, archived
curl -s "https://api.github.com/repos/<org>/<repo>/contributors?per_page=100&anon=1"  # who actually built it
curl -s "https://api.github.com/repos/<org>/<repo>/releases?per_page=5"
```

The contributor leaderboard is the highest-signal artefact in the exercise: commit counts name the
real authors regardless of who the company credits. A top committer who is a founder means
in-house; a cluster of names belonging to one contracting firm means outsourced — confirm by
checking that firm's blog for a partnership announcement.

**Renamed repo?** An old path that 301s is a rename, and the redirect resolves the id:

```bash
curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}' https://api.github.com/repos/<org>/<old-name>
```

**Staleness is a finding.** Compare `pushed_at` and the last commit date against today. "No commits
in seven months, 138 open issues" answers "is this live" better than any roadmap post. Report the
date, not an adjective.

**HuggingFace org** — `curl -s "https://huggingface.co/api/models?author=<org>&limit=50"` returns
ids, `lastModified` and `downloads`. Download counts separate research artefacts from products:
tens of downloads means nobody is using it, whatever the announcement claimed. Read one model's
`LICENSE` from its file list — the copyright line names the entity that actually owns the work,
which is how you learn whether an impressive-sounding "foundation" is a separate legal body or
just a project brand inside the parent company.

**Is a "decentralized network" actually live?** Query the chain, do not read the docs. For a
Solana program id:

```bash
for net in mainnet-beta devnet testnet; do
  curl -s -m 25 -X POST https://api.$net.solana.com -H 'Content-Type: application/json' \
    -d '{"jsonrpc":"2.0","id":1,"method":"getAccountInfo","params":["<PROGRAM_ID>",{"encoding":"base64"}]}'
done
```

`value: null` = not deployed on that cluster. Deployed on devnet and absent from mainnet-beta is
the plain answer to "can anyone actually earn on this yet" — no, it is a test network and the
payout contracts are not on a chain that holds value. Take the program id from the repo
(`declare_id!("...")` in the Rust source), never from a blog post.

**Official site unreachable?** A domain that resolves but times out is itself a finding, and the
Wayback API usually still has the content:

```bash
curl -s "http://archive.org/wayback/available?url=<domain>"    # then fetch closest.url
```

When `docs.<domain>` is down, the docs are usually compiled from a directory in the repo
(`psyche-book/`, `docs/`, `website/`) — read the markdown from
`raw.githubusercontent.com/<org>/<repo>/main/<path>` and cite the repo instead of the dead site.

## Title drift and founder facts

- **Press and directories lag seat changes.** A CEO-to-CTO move leaves years of stale "CEO" pages
  behind, Wikipedia included. State which source claims which title, prefer the company's own most
  recent statement, and flag the disagreement rather than silently picking one.
- **A pseudonymous handle is not an affiliation.** A handle that resembles a company name is a
  nickname until a bio or employment record says otherwise — say the origin is undocumented
  instead of inventing a plausible one.
- **Read the money story for what it actually is.** A "token valuation" attached to a venture round
  comes from SAFT paperwork, not a traded price. If no token exists, say so plainly and name the
  scam surface: tokens already trading under the project's name are not the project's.

## Pitfalls

- **Assert the HTTP code before parsing a response, and give every URL its own temp file.** A curl
  that fails returns code `000` and an empty body while the previous run's file still sits at the
  same path — a later parse then prints an unrelated page as if it were the answer. Check
  `-w '%{http_code}'` (or use `-f`) first, and write to a per-URL filename.
- **GitHub release JSON can carry raw control characters.** Write the response to a file and parse
  it with python from disk; a tolerant one-shot pipe chokes on it and loses the payload.
- **Stars are accumulated attention; `pushed_at` is current work.** Do not present a dormant project
  as active, or an active one as abandoned, on stars alone. Quote the date.
