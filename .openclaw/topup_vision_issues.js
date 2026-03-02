#!/usr/bin/env node
/*
  Issue top-up generator for geo-ranking-ch.

  Intent:
  - Keep a small buffer of product/dev issues available.
  - STRICT SAFETY: do not generate staging/prod/deploy/rollout/promote work while the project is in dev-only mode.

  Usage:
    node .openclaw/topup_vision_issues.js .openclaw/vision_issue_queue.json

  Queue format: JSON array of objects:
    {
      "title": "...",
      "body": "...",
      "labels": ["backlog","status:todo","priority:P2","enhancement"],
      "env": "dev"
    }
*/

const fs = require('fs');
const cp = require('child_process');

function die(msg) {
  console.error(msg);
  process.exit(1);
}

function sh(cmd, opts = {}) {
  return cp.execSync(cmd, {
    stdio: ['ignore', 'pipe', 'pipe'],
    encoding: 'utf8',
    ...opts,
  });
}

function getGithubTokenEnv() {
  // Prefer existing token if present.
  if (process.env.GITHUB_TOKEN && process.env.GITHUB_TOKEN.trim()) {
    return { ...process.env };
  }
  // Mint via GH App helper if available.
  try {
    const token = sh('bash -lc "./scripts/gh_app_token.sh"').trim();
    if (!token) throw new Error('empty token');
    return { ...process.env, GITHUB_TOKEN: token };
  } catch (e) {
    // Fall back: gh might be already authenticated in the environment.
    return { ...process.env };
  }
}

const queuePath = process.argv[2];
if (!queuePath) die('Usage: node .openclaw/topup_vision_issues.js <queue.json>');

if (!fs.existsSync(queuePath)) {
  die(`Queue file not found: ${queuePath}`);
}

const raw = fs.readFileSync(queuePath, 'utf8');
let queue;
try {
  queue = JSON.parse(raw);
} catch {
  die(`Queue is not valid JSON: ${queuePath}`);
}
if (!Array.isArray(queue)) die('Queue must be a JSON array');

const cfg = {
  repo: process.env.GITHUB_REPO || 'nimeob/geo-ranking-ch',
  minOpen: Number(process.env.ISSUE_TOPUP_MIN_OPEN || 5),
  maxOpen: Number(process.env.ISSUE_TOPUP_MAX_OPEN || 12),
  allowedEnvs: (process.env.ISSUE_TOPUP_ALLOWED_ENVS || 'dev')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean),
  // Block any issue that even hints at non-dev rollout.
  blockedPatterns: [
    /\bstaging\b/i,
    /\bprod\b/i,
    /\bproduction\b/i,
    /\bdeploy\b/i,
    /\bdeployment\b/i,
    /\broll\s*out\b/i,
    /\bpromot(e|ion)\b/i,
    /\bterraform\b/i,
    /\bkubernetes\b/i,
    /\bhelm\b/i,
  ],
};

const env = getGithubTokenEnv();

function ghJson(args) {
  const out = cp.execSync(`gh ${args}`, { encoding: 'utf8', env });
  return JSON.parse(out);
}

function gh(args) {
  return cp.execSync(`gh ${args}`, { encoding: 'utf8', env, stdio: ['ignore', 'pipe', 'pipe'] });
}

function isBlockedItem(item) {
  const t = `${item.title || ''}\n${item.body || ''}`;
  return cfg.blockedPatterns.some((re) => re.test(t));
}

function isAllowedEnv(item) {
  const e = (item.env || 'dev').toString().trim();
  return cfg.allowedEnvs.includes(e);
}

function normalizeItem(item) {
  if (!item || typeof item !== 'object') return null;
  const title = (item.title || '').toString().trim();
  if (!title) return null;

  const labels = Array.isArray(item.labels) ? item.labels.map(String) : [];
  const envName = (item.env || 'dev').toString().trim();

  // Support either a free-form body or structured fields.
  const body = (item.body || '').toString();
  const context = (item.context || '').toString();
  const scope = Array.isArray(item.scope) ? item.scope.map(String) : [];
  const dod = Array.isArray(item.dod) ? item.dod.map(String) : [];
  const notes = (item.notes || '').toString();

  return { title, body, labels, env: envName, context, scope, dod, notes };
}

function renderIssueBody(item) {
  // If a free-form body is provided, keep it (but normalize escaping).
  const raw = (item.body || '').trim();
  if (raw) {
    return raw
      .replace(/\\n/g, "\n")
      .replace(/\\t/g, "\t")
      .replace(/\\`/g, "`");
  }

  const lines = [];
  lines.push(`**Env:** ${item.env} (dev-only)`);
  if ((item.context || '').trim()) {
    lines.push('');
    lines.push('## Kontext');
    lines.push(item.context.trim());
  }

  if (item.scope && item.scope.length) {
    lines.push('');
    lines.push('## Scope');
    for (const s of item.scope) lines.push(`- ${s}`);
  }

  if (item.dod && item.dod.length) {
    lines.push('');
    lines.push('## DoD');
    for (const d of item.dod) lines.push(`- [ ] ${d}`);
  }

  if ((item.notes || '').trim()) {
    lines.push('');
    lines.push('## Notes');
    lines.push(item.notes.trim());
  }

  lines.push('');
  lines.push('---');
  lines.push('**Guardrail:** Bitte keine Staging/Prod/Deploy/Promotion-Arbeit in diesem Issue.');

  return lines.join('\n');
}

// 1) Count open issues.
let open;
try {
  open = ghJson(`issue list -R ${cfg.repo} --state open --limit 200 --json number,title`).length;
} catch (e) {
  die(`Failed to list issues via gh. Auth/config problem? ${e?.message || e}`);
}

if (open >= cfg.minOpen) {
  // Nothing to do.
  process.exit(0);
}

const canCreate = Math.max(0, cfg.maxOpen - open);
if (canCreate === 0) process.exit(0);

const created = [];
const skipped = [];

while (created.length < canCreate && queue.length > 0) {
  const item = normalizeItem(queue[0]);
  queue.shift();

  if (!item) {
    skipped.push({ reason: 'invalid', item: null });
    continue;
  }
  if (!isAllowedEnv(item)) {
    skipped.push({ reason: `env-not-allowed:${item.env}`, item: item.title });
    continue;
  }
  if (isBlockedItem(item)) {
    skipped.push({ reason: 'blocked-pattern(staging/prod/deploy/etc)', item: item.title });
    continue;
  }

  const labelArgs = item.labels.length
    ? `--label ${item.labels.map((l) => JSON.stringify(l)).join(' --label ')}`
    : '';

  const body = renderIssueBody(item) || '(no description)';

  if (process.env.DRY_RUN === '1') {
    created.push({ title: item.title, dryRun: true });
    continue;
  }

  try {
    gh(
      `issue create -R ${cfg.repo} --title ${JSON.stringify(item.title)} --body ${JSON.stringify(body)} ${labelArgs}`
    );
    created.push({ title: item.title });
  } catch (e) {
    die(`Failed to create issue "${item.title}": ${e?.message || e}`);
  }
}

// Persist updated queue.
fs.writeFileSync(queuePath, JSON.stringify(queue, null, 2) + '\n', 'utf8');

// Silent success (cron expects no output unless error).
process.exit(0);
