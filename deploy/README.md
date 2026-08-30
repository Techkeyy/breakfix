# Hosted deployment

The authorized hosted surface is a thin static frontend on Vercel and a
stdlib Python API behind Caddy on the existing `canned-vps` host. The API
delegates all analysis, proposal, approval, and verification behavior to the
existing BreakFix engine.

## Runtime boundary

- Only public HTTPS GitHub, GitLab, and Bitbucket repositories are accepted.
- The canonical demo is restricted to `https://github.com/Techkeyy/breakfix`.
- Each job runs in a disposable Docker container with a read-only root
  filesystem, no capabilities, no-new-privileges, 1 CPU, 768 MiB memory, 128
  processes, bounded temporary files, and a 15-minute host timeout.
- The only bind mounts are a read-only checked-out project, a controlled
  evidence directory, and the read-only request file during analysis.
- The provider environment is injected only into the engine container. The
  existing subprocess executor strips credentials before running target code.
- Hosted mode allows one active job at a time and bounds request, repository,
  clone, text, and public evidence sizes.
- Hosted change selection starts from a depth-1 clone. If a requested commit,
  range, or branch base is not present, Git history is acquired progressively
  at bounded depths of 16, 64, 256, and 1,024 commits, with a 180-second
  acquisition limit. Each Git subprocess is capped at 60 seconds and Git
  output at 2 MiB. The API records the requested reference, resolved full
  SHAs, and changed files in the public evidence projection.

## VPS installation

Install the service unit as `/etc/systemd/system/breakfix-api.service`, create
`/etc/breakfix/breakfix.env` with mode `0640` and group `breakfix`, build the
`breakfix-engine:latest` image from this repository, and create
`/var/lib/breakfix` owned by `breakfix:breakfix`. Append
`deploy/Caddyfile.breakfix` to the existing Caddy configuration only after
validating it, then reload Caddy and enable the service.

The provider env file is intentionally not stored in this repository.
