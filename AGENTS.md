# AGENTS.md

Guide for any agent (human or AI) working on the **[DBAH] Organized Crime** modpack.

## What this repo is

A [packwiz](https://packwiz.infra.link/) manifest for a NeoForge 1.21.1 / SpongeNeo modpack.
GitHub Pages serves the contents of `main` at `https://bennysc.github.io/oc/`, so
`https://bennysc.github.io/oc/pack.toml` is the live URL that clients and the
server install from. **Anything merged to `main` ships immediately.**

Top-level layout:

- `pack.toml` — pack manifest. Pinned MC + NeoForge versions and the SHA-256 of `index.toml`.
- `index.toml` — manifest of every metafile under `mods/` and `config/` plus their hashes.
- `mods/*.pw.toml` — one metafile per mod, pointing at a CurseForge / Modrinth / direct URL download.
- `mods/plugins/` — SpongeNeo plugins (loaded as plugins, not Forge mods).
- `config/` — server- and client-shared mod configs.
- `infra/egg-spongeneo-packwiz.json` — Pterodactyl/Pelican egg the panel uses to provision the server.

## Working with packwiz

Install the CLI once: <https://packwiz.infra.link/installation/>. All commands run from the repo root.

| Goal | Command |
|---|---|
| Add a CurseForge mod | `packwiz curseforge add <slug-or-url>` |
| Add a Modrinth mod | `packwiz modrinth add <slug-or-url>` |
| Remove a mod | `packwiz remove <name>` |
| Bump every mod to its latest matching version | `packwiz update --all` |
| Recompute every hash and rewrite `index.toml` + `pack.toml` | `packwiz refresh` |
| Sanity-check the pack ([see Validation](#validation)) | `packwiz refresh && git diff --exit-code` |

**Always run `packwiz refresh` after manually editing any `.toml`.** The CI job rejects PRs whose
`pack.toml` / `index.toml` hashes are not in sync — the same condition that produces
`Failed to process index file: java.lang.IllegalArgumentException: Unexpected hex string`
in `packwiz-installer` on the client/server.

Per-mod side (`client` / `server` / `both`) lives in each `mods/*.pw.toml`. Client-only renderers
(JEI, Embeddium, Xaero's, chat-heads, buildpaste) must stay `client` so the server doesn't try to
load them.

## Where to check logs

| Surface | Where | What it tells you |
|---|---|---|
| **Server console** | `dopey.panel.gg` → server → Console / Logs tab | NeoForge boot, mod load order, crashes, in-game `/say` output |
| **Local client** | Prism Launcher → the **[DBAH] Organized Crime** instance → **Minecraft Log** | Client crashes, missing client-side mods, Embeddium / shader issues |
| **Pack install** | Same Prism log, look for `[packwiz-installer]` lines | Hash mismatches, 404s, side filtering |

If the panel is paywalled when sharing externally, paste log excerpts to <https://logs.panel.gg>
(the panel's own paste service) and link the share URL.

## After updating the pack

Order matters — server first, then clients re-sync on next launch:

1. **Merge the PR to `main`.** GitHub Pages publishes within ~30 seconds.
2. **Restart the server** in `dopey.panel.gg`: hit **Restart** (not Stop+Start; restart re-runs the
   packwiz bootstrap in the egg's startup command, which re-syncs from `pack.toml`).
3. **Watch the console** for `Done (NN.NNNs)! For help, type "help"`. If packwiz fails, the server
   log shows the exact metafile that broke — fix it on a branch and re-merge.
4. **On each client**, open Prism → launch the **[DBAH] Organized Crime** instance. The pre-launch
   command runs `packwiz-installer-bootstrap.jar` against the same `pack.toml` and pulls any deltas
   before Minecraft starts. No manual file copying.

If a client launches without restarting the server first, mod-version mismatches will reject the
connection at login with `Connection refused: Mod rejections [...]`.

## Validation

Two layers run on every PR (see `.github/workflows/validate.yml`):

1. **`packwiz refresh` round-trip** — proves `pack.toml.hash` matches `sha256(index.toml)` and
   every `index.toml` entry matches `sha256(<metafile>)`. A non-empty `git diff` after refresh = fail.
2. **`scripts/validate-pack.py`** — structural checks that packwiz itself doesn't enforce:
   pinned MC + NeoForge versions present, every metafile has a valid `side`, every download has a
   non-empty hash + valid `hash-format`, no mod is listed twice, no orphaned files in `mods/`.

Run both locally before pushing:

```sh
packwiz refresh && git diff --exit-code -- pack.toml index.toml
python scripts/validate-pack.py
```

## Branch + PR rules

- `main` is protected. No direct pushes. Open a PR.
- CI (`validate`) must pass before merge.
- Keep PRs small — one mod add/remove/bump per PR makes rollback trivial when something breaks
  on the live server.

## Memory for AI agents

If you're an AI agent and the user asks you to remember pack-specific facts (e.g. "we never bump
NeoForge without bumping SpongeNeo too"), save them as `feedback` or `project` memories per your
host's memory system. Don't write them into this file — this file is for workflow, not transient
context.
