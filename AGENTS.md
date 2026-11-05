# Project agent instructions

## Shareable agent setup

Read `.codex/README.md` before adding or changing skills, MCP servers, or agent setup.
Install requested project skills in `.agents/skills/` and keep shared MCP settings
in `.codex/config.toml`. Preserve upstream licenses and record the source version
or commit when installing or updating third-party skills.

Use repository-relative paths, commands on PATH, and environment variable names
in shared files. Keep personal executable paths, credentials, tokens, account
settings, project trust entries, and session history out of committed files.
Keep machine-specific configuration in the user's own Codex settings or environment.
Do not copy a user's global Codex configuration into this repository.

Keep Codex setup documentation and ignore rules in `.codex/README.md` and
`.codex/.gitignore`. Do not change the root `README.md` or root `.gitignore` for
agent setup unless the user explicitly requests it.

Use only tools available in the current session. Prepare optional helper tools
or multi-agent features only when the requested task requires them.

<!-- postman-cli:installation:start -->
For API engineering tasks, use the locally installed Postman CLI. Prefer
`postman` on PATH; otherwise check the current user's local bin directory for
the executable. Do not assume it is installed on every team member's machine
or record a personal absolute executable path in shared instructions.
<!-- postman-cli:installation:end -->

## Superpowers

At the start of each conversation in this repository, read and follow
`.agents/skills/using-superpowers/SKILL.md` and its Codex platform reference.
Use the relevant installed Superpowers skills for development tasks.
Direct user instructions take precedence over skill instructions.

## Context7

Use the `context7` MCP server for current library and framework documentation
when implementing, configuring, or debugging code that depends on those APIs.
Match documentation to the dependency versions used by this project.
