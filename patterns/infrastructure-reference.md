# Pattern: Infrastructure Reference

An **infrastructure reference** is an appendix in a project's `AGENTS.md` that lists live identifiers, API endpoints, auth requirements, runner hosts, and ops shortcuts. It is reference material for agents and humans who need to interact with the project's external systems.

## When to include one

- Projects that interact with named external systems: Jira, Linear, Railway, AWS, Supabase, Discord, GitHub-as-infra, Tailscale, vendor APIs, or fixed-host services.
- Projects where operators need to know which resource, account, or environment is authoritative.
- Projects still in pre-launch state that will need this later; a stub section reserves the shape.
- Put it near the bottom of `AGENTS.md` under `## Infrastructure Reference` or `## Ops Reference`.

## Shape

Prefer short tables over prose. Organize by external system, platform, or host class.

Minimal stub (early-stage project):

````md
## Infrastructure Reference

### Discord
| Item | Value |
|---|---|
| Guild ID | `960634531159896064` |
| Guild name | Humility |

### Hosting
Platform decisions will be recorded in `DECISIONS.md` as they are made.
````

Full shape (established project):

````md
## Infrastructure Reference

### Jira
| Item | Value |
|---|---|
| Project | `RFQ` |
| Instance URL | `https://example.atlassian.net` |
| Service account | `rfq-bot@example.com` |
| Auth env var | `JIRA_API_KEY` |

### Railway
| Item | Value |
|---|---|
| Production service | `rfq-api` |
| Staging service | `rfq-api-staging` |
| Deploy command | `railway up --service rfq-api` |

### AWS
| Item | Value |
|---|---|
| Region | `us-east-1` |
| Report bucket | `rfq-e2e-reports` |
| Auth | AWS SSO profile `rfq-ops` |

### Shell snippets
```bash
# Tail the production log
railway logs --service rfq-api --tail 100

# Run a one-off Jira query
curl -u "$JIRA_USER:$JIRA_API_KEY" \
  "$JIRA_URL/rest/api/3/search?jql=project=RFQ"
```
````

## What belongs here

- Stable identifiers: project codes, guild IDs, service names, bucket names, account aliases, runner labels, hostnames.
- Endpoints and base URLs agents must call.
- Auth expectations: env-var names, SSO profile names, service accounts, or where the secret is sourced from.
- Short operational snippets that save repeated lookup.

## Rules

- One canonical place per identifier. If a Jira project code appears in ten prompts, it belongs here and other docs should reference this section.
- Secrets never go in the reference. Env-var names and where to find the secret are fine; the secret value is not.
- Keep it updated. A stale guild ID, URL, or account name silently breaks agents.
- Prefer live identifiers over explanatory prose.
- If the project only has one or two concrete facts today, keep the stub small instead of inventing placeholder systems.

## Anti-patterns

- Embedding credentials or tokens.
- Repeating the same identifier in multiple docs with no authoritative source.
- Mixing future architecture proposals with live operational facts.
- Letting shell snippets grow into a runbook.

## Exemplars

- `/home/nes/work/AGENTS.md` — fullest shape with Jira, Railway, AWS, Tailscale, endpoints, auth, hosts, and shell snippets.
- `/home/nes/projects/server-manager/AGENTS.md` — minimal stub appropriate for a pre-launch project.

The project file owns the actual identifiers. This pattern doc only describes when and how to create the section.
