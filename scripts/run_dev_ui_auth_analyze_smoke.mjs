#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

let cliOptions = null;
try {
  cliOptions = parseCliArgs(process.argv.slice(2));
} catch (error) {
  const message = error instanceof Error ? error.message : String(error || 'unknown error');
  console.error(`[dev-ui-auth-analyze-smoke] ERROR ${message}`);
  printUsage(process.stderr);
  process.exit(2);
}

if (cliOptions.mode === 'help') {
  printUsage(process.stdout);
  process.exit(0);
}

if (cliOptions.mode === 'error') {
  console.error(`[dev-ui-auth-analyze-smoke] ERROR unknown_cli_args=${cliOptions.unknownArgs.join(',')}`);
  printUsage(process.stderr);
  process.exit(2);
}

const repoRoot = process.cwd();
const configuredOutDir = String(cliOptions.evidenceDir || process.env.DEV_UI_SMOKE_EVIDENCE_DIR || '').trim();
const outDir = configuredOutDir
  ? path.resolve(repoRoot, configuredOutDir)
  : path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

const baseOrigin = normalizeOrigin(
  canonicalizeLegacyDevUiOrigin(cliOptions.baseUrl || process.env.BASE_URL || 'https://www.dev.georanking.ch')
) || 'https://www.dev.georanking.ch';
const allowedOriginOverrides = String(process.env.DEV_UI_SMOKE_ALLOWED_ORIGINS || '').trim();
const allowedOrigins = resolveAllowedOrigins(baseOrigin, allowedOriginOverrides);
const allowedAuthorizeHostOverrides = String(process.env.DEV_UI_SMOKE_ALLOWED_AUTHORIZE_HOSTS || '').trim();
const allowedAuthorizeHosts = resolveAllowedAuthorizeHosts(
  baseOrigin,
  allowedOrigins,
  allowedAuthorizeHostOverrides
);
const allowedAuthorizeHostSet = new Set(allowedAuthorizeHosts);
const guiPath = normalizeGuiPath(cliOptions.guiPath || process.env.DEV_UI_SMOKE_GUI_PATH || '/gui');
const expectedPostLoginPath = resolveCanonicalGuiSuccessor(guiPath);
const expectedPostLoginTarget = parseRelativeUrl(expectedPostLoginPath);
const loginReason = String(cliOptions.loginReason || process.env.DEV_UI_SMOKE_LOGIN_REASON || 'manual_login').trim() || 'manual_login';
const loginStartUrl = `${baseOrigin}/login?next=${encodeURIComponent(guiPath)}&reason=${encodeURIComponent(loginReason)}&start=1`;

const username = String(cliOptions.username || process.env.DEV_UI_SMOKE_USERNAME || '').trim();
const password = String(cliOptions.password || process.env.DEV_UI_SMOKE_PASSWORD || '');
const allowLoginStartFallbackOnMissingCredentials = cliOptions.forceLoginStartFallback || isTruthy(
  process.env.DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS
);

const explicitRunMarker = String(cliOptions.runId || process.env.DEV_UI_SMOKE_RUN_ID || '').trim();
const githubRunNumber = String(process.env.GITHUB_RUN_NUMBER || '').trim();
const githubRunAttempt = String(process.env.GITHUB_RUN_ATTEMPT || '').trim() || '1';
const githubRunId = String(process.env.GITHUB_RUN_ID || '').trim();
const runMarkerSource = explicitRunMarker
  ? 'DEV_UI_SMOKE_RUN_ID'
  : githubRunNumber
    ? 'GITHUB_RUN_NUMBER+GITHUB_RUN_ATTEMPT'
    : githubRunId
      ? 'GITHUB_RUN_ID+GITHUB_RUN_ATTEMPT'
      : 'timestamp';
const runMarker =
  explicitRunMarker
  || (githubRunNumber ? `${githubRunNumber}-${githubRunAttempt}` : '')
  || (githubRunId ? `${githubRunId}-${githubRunAttempt}` : '')
  || stamp;
const artifactRunToken = sanitizeFileToken(runMarker) || 'run';
const stampToken = sanitizeFileToken(stamp);
const appendRunTokenToArtifactName = Boolean(artifactRunToken && artifactRunToken !== stampToken);

const addressFile = (cliOptions.addressFile || process.env.DEV_UI_SMOKE_ADDRESS_FILE)
  ? path.resolve(repoRoot, String(cliOptions.addressFile || process.env.DEV_UI_SMOKE_ADDRESS_FILE))
  : path.join(repoRoot, 'scripts', 'smoke', 'ch_live_addresses.txt');

const timeoutMs = parsePositiveInt(cliOptions.timeoutMs || process.env.DEV_UI_SMOKE_TIMEOUT_MS, 60_000);
const headless = typeof cliOptions.headless === 'boolean' ? cliOptions.headless : !isTruthy(process.env.DEV_UI_SMOKE_HEADFUL);

function parseCliArgs(args) {
  let mode = 'run';
  const options = {
    baseUrl: '',
    guiPath: '',
    username: '',
    password: '',
    addressFile: '',
    runId: '',
    timeoutMs: '',
    loginReason: '',
    evidenceDir: '',
    headless: null,
    forceLoginStartFallback: false,
    unknownArgs: [],
  };

  const consumeValue = (currentFlag, inlineValue, argv, index) => {
    if (inlineValue !== null) return inlineValue;
    const next = argv[index + 1];
    if (typeof next !== 'string' || next.startsWith('--')) {
      throw new Error(`missing_value_for_${currentFlag}`);
    }
    return next;
  };

  const unknownArgs = [];

  for (let i = 0; i < args.length; i += 1) {
    const raw = String(args[i] || '').trim();
    if (!raw) continue;

    if (raw === '--help' || raw === '-h') {
      mode = 'help';
      continue;
    }

    if (
      raw === '--fallback-login-start-on-missing-creds'
      || raw === '--fallback-login-start'
      || raw === '--allow-login-start-fallback'
    ) {
      options.forceLoginStartFallback = true;
      continue;
    }

    const eqIdx = raw.indexOf('=');
    const flag = eqIdx >= 0 ? raw.slice(0, eqIdx) : raw;
    const inlineValue = eqIdx >= 0 ? raw.slice(eqIdx + 1) : null;

    switch (flag) {
      case '--base-url':
        options.baseUrl = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--gui-path':
        options.guiPath = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--username':
        options.username = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--password':
        options.password = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--address-file':
        options.addressFile = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--run-id':
        options.runId = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--timeout-ms':
        options.timeoutMs = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--login-reason':
        options.loginReason = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--output-dir':
      case '--evidence-dir':
        options.evidenceDir = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--headless':
        options.headless = true;
        break;
      case '--headful':
        options.headless = false;
        break;
      default:
        unknownArgs.push(flag);
    }
  }

  if (mode === 'help') {
    return {
      mode: 'help',
      ...options,
      unknownArgs: [],
    };
  }

  if (unknownArgs.length > 0) {
    return {
      mode: 'error',
      ...options,
      unknownArgs,
    };
  }

  return {
    mode,
    ...options,
    unknownArgs: [],
  };
}

function printUsage(stream) {
  stream.write(
    [
      'Usage: node scripts/run_dev_ui_auth_analyze_smoke.mjs [options]',
      '',
      'Options:',
      '  -h, --help                                   Show this help and exit.',
      '  --base-url <url>                             BASE_URL override (default: https://www.dev.georanking.ch).',
      '  --gui-path <path>                            DEV_UI_SMOKE_GUI_PATH override (default: /gui).',
      '  --username <value>                           DEV_UI_SMOKE_USERNAME override.',
      '  --password <value>                           DEV_UI_SMOKE_PASSWORD override.',
      '  --address-file <path>                        DEV_UI_SMOKE_ADDRESS_FILE override.',
      '  --run-id <token>                             DEV_UI_SMOKE_RUN_ID override.',
      '  --timeout-ms <ms>                            DEV_UI_SMOKE_TIMEOUT_MS override (default: 60000).',
      '  --login-reason <text>                        DEV_UI_SMOKE_LOGIN_REASON override (default: manual_login).',
      '  --output-dir <path> | --evidence-dir <path> DEV_UI_SMOKE_EVIDENCE_DIR override.',
      '  --headless | --headful                       Browser mode override.',
      '  --fallback-login-start                       Force login-start fallback mode when credentials are missing.',
      '  --fallback-login-start-on-missing-creds      Alias for --fallback-login-start.',
      '  --allow-login-start-fallback                 Legacy alias for --fallback-login-start.',
      '',
      'Environment:',
      '  BASE_URL                                                Optional base origin (default: https://www.dev.georanking.ch).',
      '  DEV_UI_SMOKE_ALLOWED_ORIGINS                            Optional comma-separated origin allowlist for post-login + callback host hops.',
      '  DEV_UI_SMOKE_ALLOWED_AUTHORIZE_HOSTS                    Optional comma-separated host/URL allowlist for absolute authorize redirects.',
      '  DEV_UI_SMOKE_USERNAME / DEV_UI_SMOKE_PASSWORD           Required for full live login + analyze smoke.',
      '  DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS=1    Enable degraded login-start fallback without credentials.',
    ].join('\n') + '\n'
  );
}

function parsePositiveInt(raw, fallback) {
  const value = Number.parseInt(String(raw || ''), 10);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function isTruthy(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'on';
}

function normalizeOrigin(rawOrigin) {
  try {
    const parsed = new URL(String(rawOrigin || '').trim());
    const protocol = parsed.protocol.toLowerCase();
    if (protocol !== 'http:' && protocol !== 'https:') {
      return '';
    }

    const hostname = String(parsed.hostname || '').trim().toLowerCase();
    if (!hostname) {
      return '';
    }

    const port = String(parsed.port || '').trim();
    const isDefaultPort = (protocol === 'https:' && (port === '' || port === '443'))
      || (protocol === 'http:' && (port === '' || port === '80'));
    const portSegment = isDefaultPort ? '' : `:${port}`;
    return `${protocol}//${hostname}${portSegment}`;
  } catch {
    return '';
  }
}

function isUnsupportedLegacyDevUiHostname(hostname) {
  const normalized = String(hostname || '').trim().toLowerCase();
  return normalized === 'dev.georanking.ch' || normalized === 'dev.geo-ranking.ch';
}

function canonicalizeLegacyDevUiOrigin(rawOrigin) {
  const candidate = String(rawOrigin || '').trim();
  if (!candidate) return candidate;

  try {
    const parsed = new URL(candidate);
    if (!isUnsupportedLegacyDevUiHostname(parsed.hostname)) {
      return candidate;
    }

    parsed.hostname = `www.${parsed.hostname}`;
    return parsed.toString();
  } catch {
    return candidate;
  }
}

function isIpLiteralHostname(hostname) {
  return /^\d{1,3}(?:\.\d{1,3}){3}$/.test(hostname);
}

function expandGeoHostVariants(hostname) {
  const normalized = String(hostname || '').trim().toLowerCase();
  if (!normalized) return [];

  const variants = new Set([normalized]);
  if (normalized.includes('geo-ranking')) {
    variants.add(normalized.replaceAll('geo-ranking', 'georanking'));
  }
  if (normalized.includes('georanking')) {
    variants.add(normalized.replaceAll('georanking', 'geo-ranking'));
  }

  return Array.from(variants);
}

function expandHostnameAliases(hostname) {
  const normalized = String(hostname || '').trim().toLowerCase();
  if (!normalized) return [];

  const aliases = new Set();
  const canToggleWww = normalized.includes('.') && !isIpLiteralHostname(normalized) && normalized !== 'localhost';

  const addWithGeoVariants = (candidate) => {
    for (const variant of expandGeoHostVariants(candidate)) {
      if (isUnsupportedLegacyDevUiHostname(variant)) {
        continue;
      }
      aliases.add(variant);
    }
  };

  addWithGeoVariants(normalized);

  if (canToggleWww) {
    if (normalized.startsWith('www.') && normalized.length > 4) {
      addWithGeoVariants(normalized.slice(4));
    } else {
      addWithGeoVariants(`www.${normalized}`);
    }
  }

  return Array.from(aliases);
}

function normalizeHostToken(rawHost) {
  const candidate = String(rawHost || '').trim();
  if (!candidate) return '';

  try {
    const parsed = new URL(candidate.includes('://') ? candidate : `https://${candidate}`);
    const hostname = String(parsed.hostname || '').trim().toLowerCase();
    return hostname;
  } catch {
    return candidate.replace(/^\[|\]$/g, '').toLowerCase();
  }
}

function resolveAllowedOrigins(primaryOrigin, rawOverrides) {
  const allowed = new Set();

  const addOrigin = (value) => {
    const normalized = normalizeOrigin(value);
    if (!normalized) return;

    try {
      const parsed = new URL(normalized);
      const protocol = parsed.protocol;
      const portSegment = parsed.port ? `:${parsed.port}` : '';

      for (const hostVariant of expandHostnameAliases(parsed.hostname)) {
        allowed.add(`${protocol}//${hostVariant}${portSegment}`);
      }
    } catch {
      allowed.add(normalized);
    }
  };

  addOrigin(primaryOrigin);

  const overrides = String(rawOverrides || '')
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);
  for (const override of overrides) {
    addOrigin(override);
  }

  return Array.from(allowed);
}

function resolveAllowedAuthorizeHosts(primaryOrigin, originAllowlist, rawOverrides) {
  const allowedHosts = new Set();

  const addHostSeeds = (hostToken) => {
    const normalizedHost = normalizeHostToken(hostToken);
    if (!normalizedHost) return;

    if (normalizedHost.startsWith('auth.') && normalizedHost.length > 5) {
      allowedHosts.add(normalizedHost);
      addHostSeeds(normalizedHost.slice(5));
      return;
    }

    const seedHosts = normalizedHost.startsWith('www.') && normalizedHost.length > 4
      ? [normalizedHost, normalizedHost.slice(4)]
      : [normalizedHost];

    for (const seedHost of seedHosts) {
      for (const hostVariant of expandGeoHostVariants(seedHost)) {
        if (!isUnsupportedLegacyDevUiHostname(hostVariant)) {
          allowedHosts.add(hostVariant);
        }
        allowedHosts.add(`auth.${hostVariant}`);
      }
    }
  };

  addHostSeeds(primaryOrigin);
  for (const origin of originAllowlist || []) {
    addHostSeeds(origin);
  }

  const overrides = String(rawOverrides || '')
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);
  for (const override of overrides) {
    addHostSeeds(override);
  }

  return Array.from(allowedHosts);
}

function isAllowedOrigin(value) {
  const normalized = normalizeOrigin(value);
  if (!normalized) {
    return false;
  }
  return allowedOrigins.includes(normalized);
}

function normalizeGuiPath(rawPath) {
  const value = String(rawPath || '').trim() || '/gui';
  return value.startsWith('/') ? value : `/${value}`;
}

function parseRelativeUrl(rawPath) {
  const input = String(rawPath || '').trim() || '/gui';
  try {
    const parsed = new URL(input, 'https://example.invalid');
    const normalizedPathname = parsed.pathname.startsWith('/')
      ? parsed.pathname
      : `/${parsed.pathname}`;
    return {
      pathname: normalizedPathname,
      search: parsed.search,
    };
  } catch {
    const normalizedFallback = normalizeGuiPath(input);
    return {
      pathname: normalizedFallback,
      search: '',
    };
  }
}

function resolveCanonicalGuiSuccessor(pathname) {
  const target = parseRelativeUrl(pathname);
  if (target.pathname === '/gui/jobs') return `/jobs${target.search}`;
  if (target.pathname.startsWith('/gui/jobs/')) {
    return `/jobs${target.pathname.slice('/gui/jobs'.length)}${target.search}`;
  }
  return `${target.pathname}${target.search}`;
}

function isExpectedPostLoginUrl(value) {
  try {
    const parsed = new URL(String(value || ''));
    if (!isAllowedOrigin(parsed.origin)) return false;
    if (parsed.pathname !== expectedPostLoginTarget.pathname) return false;
    if (!expectedPostLoginTarget.search) return true;
    return parsed.search === expectedPostLoginTarget.search;
  } catch {
    return false;
  }
}

function sanitizeFileToken(value) {
  return String(value || '')
    .trim()
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);
}

function buildArtifactPath(extension) {
  const runSuffix = appendRunTokenToArtifactName ? `-${artifactRunToken}` : '';
  return path.join(outDir, `dev-ui-auth-analyze-smoke-${stamp}${runSuffix}.${extension}`);
}

async function loadChromium() {
  try {
    const playwrightModule = await import('playwright');
    const chromium = playwrightModule?.chromium;
    if (!chromium) {
      throw new Error('chromium export missing');
    }
    return chromium;
  } catch (error) {
    const normalized = normalizeError(error);
    throw new Error(
      `Playwright Chromium nicht verfügbar. Installiere die Node-Abhängigkeiten mit \`npm ci\` `
      + `und anschließend Browser-Binaries via \`npx playwright install --with-deps chromium\`. `
      + `Ursache: ${normalized.name}: ${normalized.message}`
    );
  }
}

function normalizeError(error) {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack || '',
    };
  }
  return {
    name: 'Error',
    message: String(error || 'unknown error'),
    stack: '',
  };
}

function safeJsonParse(raw) {
  if (typeof raw !== 'string' || raw.trim() === '') {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function selectAddressIndex(poolSize, marker) {
  if (!Number.isFinite(poolSize) || poolSize <= 0) {
    return 0;
  }

  const normalized = String(marker || '').trim();
  const runTuple = normalized.match(/^(\d+)(?:\D+(\d+))?$/);
  if (runTuple) {
    const primary = Number.parseInt(runTuple[1], 10);
    const attempt = Number.parseInt(runTuple[2] || '1', 10);
    if (Number.isFinite(primary) && Number.isFinite(attempt) && attempt > 0) {
      return Math.abs((primary + attempt - 1) % poolSize);
    }
  }

  const numericChunks = normalized.match(/\d+/g);
  if (numericChunks && numericChunks.length) {
    let rolling = 0;
    for (const chunk of numericChunks) {
      const value = Number.parseInt(chunk, 10);
      if (!Number.isFinite(value)) continue;
      rolling = (rolling * 31 + Math.abs(value)) % poolSize;
    }
    return rolling;
  }

  const digest = crypto.createHash('sha256').update(normalized || stamp, 'utf8').digest('hex');
  const asInt = Number.parseInt(digest.slice(0, 12), 16);
  return Number.isFinite(asInt) ? asInt % poolSize : 0;
}

async function readAddressPool(filePath) {
  const raw = await fs.readFile(filePath, 'utf8');
  const addresses = raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'));

  if (!addresses.length) {
    throw new Error(`Adresspool leer: ${filePath}`);
  }
  return addresses;
}

function isIdpLoginUrl(value) {
  try {
    const parsed = new URL(String(value || ''));
    const host = parsed.hostname.toLowerCase();
    const pathname = parsed.pathname.toLowerCase();
    if (!host.includes('auth.')) return false;
    return pathname === '/login' || pathname.endsWith('/login');
  } catch {
    return false;
  }
}

function isAnalyzeRequestUrl(value) {
  try {
    const parsed = new URL(String(value || ''));
    return parsed.pathname === '/analyze' || parsed.pathname.endsWith('/analyze');
  } catch {
    return false;
  }
}

function isExpectedAuthCallbackRedirect(value) {
  try {
    const parsed = new URL(String(value || ''), baseOrigin);
    return isAllowedOrigin(parsed.origin) && parsed.pathname === '/auth/callback';
  } catch {
    return false;
  }
}

function parseAuthAuthorizeRedirect(value) {
  const result = {
    isAuthAuthorizeUrl: false,
    responseTypeCode: false,
    clientIdPresent: false,
    redirectUriMatchesAuthCallback: false,
    authorizeHostAllowed: false,
    authorizeHost: '',
  };

  try {
    const parsed = new URL(String(value || ''));
    const host = parsed.hostname.toLowerCase();
    const pathname = parsed.pathname.toLowerCase();

    result.authorizeHost = host;
    result.authorizeHostAllowed = allowedAuthorizeHostSet.has(host);
    if (!result.authorizeHostAllowed) {
      return result;
    }

    const responseType = String(parsed.searchParams.get('response_type') || '').trim().toLowerCase();
    result.responseTypeCode = responseType === 'code';
    result.clientIdPresent = String(parsed.searchParams.get('client_id') || '').trim().length > 0;
    result.redirectUriMatchesAuthCallback = isExpectedAuthCallbackRedirect(parsed.searchParams.get('redirect_uri'));

    if (pathname === '/oauth2/authorize' || pathname.endsWith('/oauth2/authorize')) {
      result.isAuthAuthorizeUrl = true;
      return result;
    }

    if (pathname === '/login' || pathname.endsWith('/login')) {
      result.isAuthAuthorizeUrl = parsed.searchParams.has('response_type') && parsed.searchParams.has('client_id');
      return result;
    }

    return result;
  } catch {
    return result;
  }
}

function buildLoginStartFallbackHint() {
  const envName = baseOrigin.toLowerCase().includes('staging') ? 'staging' : 'dev';
  return [
    `BASE_URL="${baseOrigin}" \\`,
    `./scripts/smoke/run_login_start_smoke_bundle.sh --base-url "$BASE_URL" --env-name ${envName}`,
  ].join('\n');
}

const MAX_LOGIN_START_FALLBACK_REDIRECT_HOPS = 6;

function isRedirectStatus(status) {
  return Number.isFinite(status) && status >= 300 && status < 400;
}

function isAuthorizeContractSatisfied(contract) {
  return Boolean(
    contract
      && contract.isAuthAuthorizeUrl
      && contract.authorizeHostAllowed
      && contract.responseTypeCode
      && contract.clientIdPresent
      && contract.redirectUriMatchesAuthCallback
  );
}

function normalizePathname(value) {
  const raw = String(value || '').trim() || '/';
  if (raw === '/') return '/';
  return raw.replace(/\/+$/, '') || '/';
}

function isIntermediateLoginRedirectUrl(value) {
  try {
    const parsed = new URL(String(value || ''));
    const pathname = normalizePathname(parsed.pathname.toLowerCase());
    return pathname === '/login' || pathname === '/auth/login';
  } catch {
    return false;
  }
}

function classifyFetchRequestFailure(error) {
  const causeCode = String(error?.cause?.code || '').trim().toUpperCase();
  const errorCode = String(error?.code || '').trim().toUpperCase();
  const message = String(error?.message || '').trim().toLowerCase();
  const causeMessage = String(error?.cause?.message || '').trim().toLowerCase();

  const tlsCodes = new Set([
    'CERT_HAS_EXPIRED',
    'UNABLE_TO_VERIFY_LEAF_SIGNATURE',
    'DEPTH_ZERO_SELF_SIGNED_CERT',
    'SELF_SIGNED_CERT_IN_CHAIN',
    'ERR_TLS_CERT_ALTNAME_INVALID',
    'CERT_SIGNATURE_FAILURE',
    'UNABLE_TO_GET_ISSUER_CERT_LOCALLY',
  ]);
  const dnsCodes = new Set(['ENOTFOUND', 'EAI_AGAIN']);
  const timeoutCodes = new Set(['ETIMEDOUT', 'UND_ERR_CONNECT_TIMEOUT', 'UND_ERR_HEADERS_TIMEOUT']);
  const connectionCodes = new Set(['ECONNREFUSED', 'ECONNRESET', 'EHOSTUNREACH', 'ENETUNREACH']);

  const candidateCodes = [causeCode, errorCode].filter(Boolean);

  const normalizeSuffix = (value, fallback) => {
    const cleaned = String(value || '')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
    return cleaned || fallback;
  };

  const hasTlsMessage = [message, causeMessage].some((entry) => entry.includes('certificate') || entry.includes('tls'));

  if (candidateCodes.some((code) => tlsCodes.has(code)) || hasTlsMessage) {
    const suffix = normalizeSuffix(causeCode || errorCode || causeMessage, 'tls');
    return `request_failed_tls_${suffix}`;
  }
  if (candidateCodes.some((code) => dnsCodes.has(code))) {
    const suffix = normalizeSuffix(causeCode || errorCode, 'dns');
    return `request_failed_dns_${suffix}`;
  }
  if (candidateCodes.some((code) => timeoutCodes.has(code))) {
    const suffix = normalizeSuffix(causeCode || errorCode, 'timeout');
    return `request_failed_timeout_${suffix}`;
  }
  if (candidateCodes.some((code) => connectionCodes.has(code))) {
    const suffix = normalizeSuffix(causeCode || errorCode, 'connection');
    return `request_failed_connection_${suffix}`;
  }

  if (message.includes('fetch failed') || causeMessage.includes('fetch failed')) {
    return 'request_failed_fetch';
  }

  return 'request_failed_unknown';
}

async function fetchSingleRedirectProbe(requestUrl) {
  try {
    const response = await fetch(requestUrl, {
      method: 'GET',
      redirect: 'manual',
      headers: {
        Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      },
    });

    const location = String(response.headers.get('location') || '').trim();
    const status = response.status;
    let absoluteLocation = '';

    if (location) {
      try {
        absoluteLocation = new URL(location, requestUrl).toString();
      } catch {
        absoluteLocation = '';
      }
    }

    const authorizeContract = parseAuthAuthorizeRedirect(absoluteLocation);
    return {
      requestUrl,
      status,
      location: absoluteLocation,
      authorizeContract,
      requestError: null,
    };
  } catch (error) {
    const normalizedError = normalizeError(error);
    const causeCode = String(error?.cause?.code || '').trim();
    const reason = classifyFetchRequestFailure(error);
    return {
      requestUrl,
      status: 0,
      location: '',
      authorizeContract: parseAuthAuthorizeRedirect(''),
      requestError: {
        ...normalizedError,
        code: causeCode,
        reason,
      },
    };
  }
}

async function probeLoginRedirect(url) {
  const redirectChain = [];
  const visited = new Set([String(url)]);
  let currentRequestUrl = String(url);

  for (let hop = 0; hop <= MAX_LOGIN_START_FALLBACK_REDIRECT_HOPS; hop += 1) {
    const probe = await fetchSingleRedirectProbe(currentRequestUrl);
    redirectChain.push({
      requestUrl: probe.requestUrl,
      status: probe.status,
      location: probe.location,
      requestError: probe.requestError,
    });

    if (probe.requestError) {
      return {
        ok: false,
        reason: probe.requestError.reason || 'request_failed_unknown',
        requestUrl: String(url),
        finalRequestUrl: probe.requestUrl,
        status: probe.status,
        location: probe.location,
        authorizeContract: probe.authorizeContract,
        requestError: probe.requestError,
        redirectHopCount: hop,
        redirectChain,
      };
    }

    if (
      isRedirectStatus(probe.status)
      && probe.location
      && isAuthorizeContractSatisfied(probe.authorizeContract)
    ) {
      return {
        ok: true,
        reason: 'ok',
        requestUrl: String(url),
        finalRequestUrl: probe.requestUrl,
        status: probe.status,
        location: probe.location,
        authorizeContract: probe.authorizeContract,
        requestError: null,
        redirectHopCount: hop,
        redirectChain,
      };
    }

    if (!isRedirectStatus(probe.status)) {
      return {
        ok: false,
        reason: `unexpected_status_${probe.status}`,
        requestUrl: String(url),
        finalRequestUrl: probe.requestUrl,
        status: probe.status,
        location: probe.location,
        authorizeContract: probe.authorizeContract,
        requestError: null,
        redirectHopCount: hop,
        redirectChain,
      };
    }

    if (!probe.location) {
      return {
        ok: false,
        reason: 'missing_location_header',
        requestUrl: String(url),
        finalRequestUrl: probe.requestUrl,
        status: probe.status,
        location: probe.location,
        authorizeContract: probe.authorizeContract,
        requestError: null,
        redirectHopCount: hop,
        redirectChain,
      };
    }

    if (!isIntermediateLoginRedirectUrl(probe.location)) {
      return {
        ok: false,
        reason: 'non_login_redirect_target',
        requestUrl: String(url),
        finalRequestUrl: probe.requestUrl,
        status: probe.status,
        location: probe.location,
        authorizeContract: probe.authorizeContract,
        requestError: null,
        redirectHopCount: hop,
        redirectChain,
      };
    }

    if (hop >= MAX_LOGIN_START_FALLBACK_REDIRECT_HOPS) {
      return {
        ok: false,
        reason: 'redirect_hop_limit_exceeded',
        requestUrl: String(url),
        finalRequestUrl: probe.requestUrl,
        status: probe.status,
        location: probe.location,
        authorizeContract: probe.authorizeContract,
        requestError: null,
        redirectHopCount: hop,
        redirectChain,
      };
    }

    if (visited.has(probe.location)) {
      return {
        ok: false,
        reason: 'redirect_loop_detected',
        requestUrl: String(url),
        finalRequestUrl: probe.requestUrl,
        status: probe.status,
        location: probe.location,
        authorizeContract: probe.authorizeContract,
        requestError: null,
        redirectHopCount: hop,
        redirectChain,
      };
    }

    visited.add(probe.location);
    currentRequestUrl = probe.location;
  }

  return {
    ok: false,
    reason: 'redirect_hop_limit_exceeded',
    requestUrl: String(url),
    finalRequestUrl: currentRequestUrl,
    status: 0,
    location: '',
    authorizeContract: parseAuthAuthorizeRedirect(''),
    requestError: null,
    redirectHopCount: MAX_LOGIN_START_FALLBACK_REDIRECT_HOPS,
    redirectChain,
  };
}

async function runLoginStartFallbackProbe(startedAtUtc) {
  const entryUrl = `${baseOrigin}/login?next=${encodeURIComponent(guiPath)}&reason=${encodeURIComponent(loginReason)}`;

  const startProbe = await probeLoginRedirect(loginStartUrl);
  const entryProbe = await probeLoginRedirect(entryUrl);

  const checks = {
    fallbackEnabled: true,
    startRedirectToAuthAuthorize: startProbe.ok,
    entryRedirectToAuthAuthorize: entryProbe.ok,
    startRedirectAuthorizeHostAllowed: Boolean(startProbe?.authorizeContract?.authorizeHostAllowed),
    entryRedirectAuthorizeHostAllowed: Boolean(entryProbe?.authorizeContract?.authorizeHostAllowed),
    startRedirectResponseTypeCode: Boolean(startProbe?.authorizeContract?.responseTypeCode),
    entryRedirectResponseTypeCode: Boolean(entryProbe?.authorizeContract?.responseTypeCode),
    startRedirectClientIdPresent: Boolean(startProbe?.authorizeContract?.clientIdPresent),
    entryRedirectClientIdPresent: Boolean(entryProbe?.authorizeContract?.clientIdPresent),
    startRedirectUriMatchesAuthCallback: Boolean(startProbe?.authorizeContract?.redirectUriMatchesAuthCallback),
    entryRedirectUriMatchesAuthCallback: Boolean(entryProbe?.authorizeContract?.redirectUriMatchesAuthCallback),
  };

  const ok = Object.values(checks).every((value) => value === true);

  const payload = {
    startedAtUtc,
    finishedAtUtc: new Date().toISOString(),
    target: {
      baseOrigin,
      allowedOrigins,
      allowedAuthorizeHosts,
      guiPath,
      expectedPostLoginPath,
      loginStartUrl,
    },
    runtime: {
      browser: 'none-login-start-fallback',
      headless,
      timeoutMs,
      runMarker,
      runMarkerSource,
      githubRunNumber,
      githubRunAttempt,
      githubRunId,
    },
    credentials: {
      usernameMasked: maskUsername(username),
    },
    degradedMode: {
      active: true,
      reason: 'missing_live_credentials',
      envFlag: 'DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS',
    },
    loginStartFallback: {
      startProbe,
      entryProbe,
    },
    checks,
    ok,
  };

  const evidencePath = await writeEvidence(payload);
  emitSmokeSummary(payload, evidencePath);
  return ok;
}

function analyzePayloadCompleteness(payload) {
  const result = payload && typeof payload === 'object' ? payload.result : null;
  const data = result && typeof result === 'object' ? result.data : null;
  const modules = data && typeof data === 'object' ? data.modules : null;

  const hasSuitability = Boolean(
    modules
      && typeof modules === 'object'
      && (modules.suitability_light || (modules.summary_compact && modules.summary_compact.suitability_light))
  );
  const hasMatch = Boolean(modules && typeof modules === 'object' && modules.match);
  const matchedAddress =
    (data && data.entity && (data.entity.matched_address || data.entity.query)) ||
    '';

  const moduleCount = modules && typeof modules === 'object' ? Object.keys(modules).length : 0;

  const complete = Boolean(
    payload
      && payload.ok === true
      && result
      && typeof result === 'object'
      && data
      && typeof data === 'object'
      && modules
      && typeof modules === 'object'
      && moduleCount > 0
      && hasSuitability
      && hasMatch
      && String(matchedAddress || '').trim().length > 0
  );

  return {
    complete,
    moduleCount,
    hasSuitability,
    hasMatch,
    matchedAddress: String(matchedAddress || '').trim(),
    requestId: payload && payload.request_id ? String(payload.request_id) : '',
  };
}

async function locateFirstVisible(page, selectors, timeout) {
  for (const selector of selectors) {
    const visibleLocator = page.locator(`${selector}:visible`).first();
    try {
      await visibleLocator.waitFor({ state: 'visible', timeout: Math.max(1_000, timeout) });
      return visibleLocator;
    } catch {
      // try next selector
    }
  }
  throw new Error(`Kein sichtbares Element für Selektoren gefunden: ${selectors.join(', ')}`);
}

async function collectUiSnapshot(page) {
  return page.evaluate(() => {
    const phaseEl = document.querySelector('#phase-pill');
    const resultsMetaEl = document.querySelector('#results-meta');
    const errorBoxEl = document.querySelector('#error-box');
    const rows = Array.from(document.querySelectorAll('#results-body tr'));
    const nonEmptyRows = rows.filter((row) => {
      const emptyCell = row.querySelector('td.results-empty-cell');
      return !emptyCell;
    });

    return {
      phaseText: phaseEl ? String(phaseEl.textContent || '').trim() : '',
      phaseState: phaseEl ? String(phaseEl.getAttribute('data-phase') || '').trim() : '',
      resultsMetaText: resultsMetaEl ? String(resultsMetaEl.textContent || '').trim() : '',
      errorBoxText:
        errorBoxEl && !errorBoxEl.hasAttribute('hidden') ? String(errorBoxEl.textContent || '').trim() : '',
      resultRowCount: nonEmptyRows.length,
    };
  });
}

async function waitForTerminalUiSignal(page, timeout) {
  const handle = await page.waitForFunction(() => {
    const phaseEl = document.querySelector('#phase-pill');
    const errorBoxEl = document.querySelector('#error-box');
    const rows = Array.from(document.querySelectorAll('#results-body tr'));
    const nonEmptyRows = rows.filter((row) => !row.querySelector('td.results-empty-cell'));

    const phaseState = phaseEl ? String(phaseEl.getAttribute('data-phase') || '').trim().toLowerCase() : '';
    const phaseText = phaseEl ? String(phaseEl.textContent || '').trim().toLowerCase() : '';
    const errorBoxVisible = Boolean(errorBoxEl && !errorBoxEl.hasAttribute('hidden'));

    if (phaseState === 'success' || phaseState === 'error') {
      return {
        reason: `phase_${phaseState}`,
        phaseState,
        phaseText,
        resultRowCount: nonEmptyRows.length,
        errorBoxVisible,
      };
    }

    if (errorBoxVisible) {
      return {
        reason: 'error_box_visible',
        phaseState,
        phaseText,
        resultRowCount: nonEmptyRows.length,
        errorBoxVisible,
      };
    }

    if (nonEmptyRows.length > 0) {
      return {
        reason: 'results_rows_rendered',
        phaseState,
        phaseText,
        resultRowCount: nonEmptyRows.length,
        errorBoxVisible,
      };
    }

    return null;
  }, undefined, { timeout });

  return handle.jsonValue();
}

async function waitForAnalyzeShellVisible(page, timeout) {
  await page.locator('#analyze-form').waitFor({ state: 'visible', timeout });
}

async function ensureAnalyzeShellReady(page, baseOrigin, timeout) {
  const quickProbeTimeout = Math.max(1_000, Math.min(8_000, Math.floor(timeout / 6)));

  try {
    await waitForAnalyzeShellVisible(page, quickProbeTimeout);
    return {
      recovered: false,
      strategy: 'already_visible',
      urlAfterRecovery: page.url(),
    };
  } catch {
    // continue with recovery path
  }

  const analyzeMenuLink = page.locator('a[role="menuitem"][href="/gui"]:visible').first();
  if (await analyzeMenuLink.count()) {
    await Promise.all([
      page.waitForURL(
        (url) => {
          try {
            const parsed = new URL(String(url));
            return isAllowedOrigin(parsed.origin) && parsed.pathname === '/gui';
          } catch {
            return false;
          }
        },
        { timeout }
      ),
      analyzeMenuLink.click(),
    ]);

    await waitForAnalyzeShellVisible(page, timeout);
    return {
      recovered: true,
      strategy: 'menuitem_to_gui',
      urlAfterRecovery: page.url(),
    };
  }

  await page.goto(`${baseOrigin}/gui`, { waitUntil: 'domcontentloaded' });
  await waitForAnalyzeShellVisible(page, timeout);
  return {
    recovered: true,
    strategy: 'direct_goto_gui',
    urlAfterRecovery: page.url(),
  };
}

function maskUsername(value) {
  if (!value) return '';
  if (value.length <= 2) return `${value[0] || '*'}*`;
  return `${value[0]}***${value[value.length - 1]}`;
}

async function writeEvidence(payload) {
  await fs.mkdir(outDir, { recursive: true });
  const outJson = buildArtifactPath('json');
  await fs.writeFile(outJson, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  console.log(path.relative(repoRoot, outJson));
  return outJson;
}

function collectFailedChecks(checks) {
  if (!checks || typeof checks !== 'object') return [];
  return Object.entries(checks)
    .filter(([, value]) => value !== true)
    .map(([name]) => name);
}

function toSummaryToken(value) {
  const normalized = String(value ?? '').trim();
  return normalized === '' ? '-' : normalized.replace(/\s+/g, '_').slice(0, 200);
}

function emitSmokeSummary(payload, evidencePath) {
  const evidenceRelPath = evidencePath ? path.relative(repoRoot, evidencePath) : '-';
  const guiPathToken = toSummaryToken(payload?.target?.guiPath);
  const runMarkerToken = toSummaryToken(payload?.runtime?.runMarker);

  if (payload?.ok === true) {
    const analyzeStatus = toSummaryToken(payload?.analyze?.responseStatus);
    const resultsCount = toSummaryToken(payload?.uiState?.resultRowCount);
    const terminalSignal = toSummaryToken(payload?.uiState?.terminalUiSignal?.reason);
    const modeToken = payload?.degradedMode?.active ? 'mode=login_start_fallback' : 'mode=live_auth_analyze';
    console.log(
      `[dev-ui-auth-analyze-smoke] PASS gui_path=${guiPathToken} run_marker=${runMarkerToken}`
      + ` ${modeToken} analyze_status=${analyzeStatus} results=${resultsCount} terminal_signal=${terminalSignal}`
      + ` evidence=${evidenceRelPath}`
    );
    return;
  }

  if (payload?.error) {
    const errorName = toSummaryToken(payload.error.name);
    const errorMessage = toSummaryToken(payload.error.message);
    console.error(
      `[dev-ui-auth-analyze-smoke] ERROR gui_path=${guiPathToken} run_marker=${runMarkerToken}`
      + ` error=${errorName}:${errorMessage} evidence=${evidenceRelPath}`
    );
    return;
  }

  const failedChecks = collectFailedChecks(payload?.checks);
  const failedChecksToken = failedChecks.length ? failedChecks.join(',') : '-';
  const analyzeStatus = toSummaryToken(payload?.analyze?.responseStatus);
  const phaseState = toSummaryToken(payload?.uiState?.phaseState);
  const terminalSignal = toSummaryToken(payload?.uiState?.terminalUiSignal?.reason);
  const guardSignals = Array.isArray(payload?.guardSignals?.sessionExpiredSignals)
    ? payload.guardSignals.sessionExpiredSignals.join(',')
    : '';
  const guardSignalsToken = guardSignals ? toSummaryToken(guardSignals) : '-';
  const startProbeReason = toSummaryToken(payload?.loginStartFallback?.startProbe?.reason);
  const entryProbeReason = toSummaryToken(payload?.loginStartFallback?.entryProbe?.reason);

  console.error(
    `[dev-ui-auth-analyze-smoke] FAIL gui_path=${guiPathToken} run_marker=${runMarkerToken}`
    + ` failed_checks=${failedChecksToken} analyze_status=${analyzeStatus}`
    + ` phase=${phaseState} terminal_signal=${terminalSignal}`
    + ` start_reason=${startProbeReason} entry_reason=${entryProbeReason}`
    + ` guard_signals=${guardSignalsToken} evidence=${evidenceRelPath}`
  );
}

async function run() {
  const startedAtUtc = new Date().toISOString();

  if (!username || !password) {
    if (allowLoginStartFallbackOnMissingCredentials) {
      return runLoginStartFallbackProbe(startedAtUtc);
    }

    const fallbackHint = buildLoginStartFallbackHint();
    throw new Error(
      'Fehlende Credentials: DEV_UI_SMOKE_USERNAME und DEV_UI_SMOKE_PASSWORD sind für echten Live-Login erforderlich. '
      + 'Optionaler degraded Fallback: setze DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS=1 oder führe aus:\n'
      + fallbackHint
    );
  }

  const addressPool = await readAddressPool(addressFile);
  const addressIndex = selectAddressIndex(addressPool.length, runMarker);
  const selectedAddress = addressPool[addressIndex];

  const chromium = await loadChromium();
  const browser = await chromium.launch({ headless });
  const context = await browser.newContext({
    locale: 'de-CH',
    viewport: { width: 1536, height: 960 },
  });
  const page = await context.newPage();

  const flowResponses = [];
  page.on('response', (response) => {
    try {
      const url = new URL(response.url());
      if (url.pathname === '/analyze' || url.pathname === '/auth/me' || url.pathname.startsWith('/auth/')) {
        flowResponses.push({
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        });
      }
    } catch {
      // ignore malformed URLs
    }
  });

  let idpLoginUrl = '';
  let postLoginUrl = '';
  let finalUrl = '';
  let authMeStatus = null;
  let authMeBody = null;
  let analyzeRequestPayload = null;
  let analyzeResponseBody = null;
  let analyzeResponseStatus = null;
  let analyzeResponseUrl = '';
  let phaseText = '';
  let phaseState = '';
  let resultsMetaText = '';
  let errorBoxText = '';
  let resultRowCount = 0;
  let terminalUiSignal = null;
  let terminalUiSignalTimeout = false;
  let analyzeShellRecovery = null;
  let screenshotRelPath = '';

  try {
    await page.goto(loginStartUrl, { waitUntil: 'domcontentloaded' });

    await page.waitForURL((url) => isIdpLoginUrl(String(url)), { timeout: timeoutMs });
    idpLoginUrl = page.url();

    const usernameField = await locateFirstVisible(
      page,
      ['input[name="username"]', '#username', 'input[type="email"]', 'input[name="email"]'],
      timeoutMs
    );
    const passwordField = await locateFirstVisible(
      page,
      ['input[name="password"]', '#password', 'input[type="password"]'],
      timeoutMs
    );

    await usernameField.fill(username);
    await passwordField.fill(password);

    const submitButton = await locateFirstVisible(
      page,
      ['button[type="submit"]', 'input[type="submit"]', 'button[name="signInSubmitButton"]', 'input[name="signInSubmitButton"]'],
      timeoutMs
    );

    await Promise.all([
      page.waitForURL(
        (url) => isExpectedPostLoginUrl(url),
        { timeout: timeoutMs }
      ),
      submitButton.click(),
    ]);

    postLoginUrl = page.url();
    analyzeShellRecovery = await ensureAnalyzeShellReady(page, baseOrigin, timeoutMs);

    const authMeEval = await page.evaluate(async () => {
      const response = await fetch('/auth/me', {
        method: 'GET',
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      let parsed = null;
      try {
        parsed = await response.json();
      } catch {
        parsed = null;
      }
      return {
        status: response.status,
        body: parsed,
      };
    });
    authMeStatus = authMeEval.status;
    authMeBody = authMeEval.body;

    await page.locator('#query').fill(selectedAddress);
    await page.locator('#intelligence-mode').selectOption('basic');

    const analyzeRequestPromise = page.waitForRequest(
      (request) => request.method() === 'POST' && isAnalyzeRequestUrl(request.url()),
      { timeout: timeoutMs }
    );
    const analyzeResponsePromise = page.waitForResponse(
      (response) => response.request().method() === 'POST' && isAnalyzeRequestUrl(response.url()),
      { timeout: timeoutMs }
    );

    await Promise.all([analyzeRequestPromise, analyzeResponsePromise, page.locator('#submit-btn').click()]);

    const analyzeRequest = await analyzeRequestPromise;
    const analyzeResponse = await analyzeResponsePromise;

    analyzeResponseStatus = analyzeResponse.status();
    analyzeResponseUrl = analyzeResponse.url();

    const requestRaw = analyzeRequest.postData() || '';
    analyzeRequestPayload = safeJsonParse(requestRaw);

    try {
      analyzeResponseBody = await analyzeResponse.json();
    } catch {
      const responseText = await analyzeResponse.text().catch(() => '');
      analyzeResponseBody = safeJsonParse(responseText) || { _raw: responseText.slice(0, 2_000) };
    }

    try {
      terminalUiSignal = await waitForTerminalUiSignal(page, timeoutMs);
    } catch {
      terminalUiSignalTimeout = true;
    }

    const uiSnapshot = await collectUiSnapshot(page);
    phaseText = uiSnapshot.phaseText;
    phaseState = uiSnapshot.phaseState;
    resultsMetaText = uiSnapshot.resultsMetaText;
    errorBoxText = uiSnapshot.errorBoxText;
    resultRowCount = uiSnapshot.resultRowCount;

    finalUrl = page.url();

    await fs.mkdir(outDir, { recursive: true });
    const screenshotPath = buildArtifactPath('png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    screenshotRelPath = path.relative(repoRoot, screenshotPath);
  } finally {
    if (!screenshotRelPath) {
      try {
        await fs.mkdir(outDir, { recursive: true });
        const fallbackScreenshotPath = buildArtifactPath('png');
        await page.screenshot({ path: fallbackScreenshotPath, fullPage: true });
        screenshotRelPath = path.relative(repoRoot, fallbackScreenshotPath);
      } catch {
        // ignore screenshot fallback errors
      }
    }

    await context.close();
    await browser.close();
  }

  const analyzeCompleteness = analyzePayloadCompleteness(analyzeResponseBody);
  const authMeAuthenticated =
    authMeStatus === 200
    && authMeBody
    && typeof authMeBody === 'object'
    && (authMeBody.authenticated === true || authMeBody.ok === true);

  const submittedQuery =
    analyzeRequestPayload && typeof analyzeRequestPayload === 'object' && typeof analyzeRequestPayload.query === 'string'
      ? analyzeRequestPayload.query.trim()
      : '';
  const submittedAddressMatches = submittedQuery === selectedAddress;

  const has401DuringAnalyzeFlow = flowResponses.some((entry) => {
    if (entry.status !== 401) return false;
    return entry.url.includes('/analyze') || entry.url.includes('/auth/me');
  });

  const responseTextForGuards = JSON.stringify(analyzeResponseBody || {}).toLowerCase();
  const sessionExpiredSignals = [
    'session_expired',
    'no_session',
    'idle-fallback',
    'idle_fallback',
    'auth_required',
    'unauthorized',
  ].filter((token) => responseTextForGuards.includes(token));

  const phaseStateNormalized = String(phaseState || '').trim().toLowerCase();
  const phaseTextNormalized = String(phaseText || '').trim().toLowerCase();
  const terminalUiSignalReason = terminalUiSignal && terminalUiSignal.reason ? String(terminalUiSignal.reason) : '';

  const noIdleFallback = resultRowCount > 0 && phaseStateNormalized !== 'idle' && !phaseTextNormalized.includes('idle');

  const loginReturnedToRequestedGuiPath = isExpectedPostLoginUrl(postLoginUrl);

  const checks = {
    loginRedirectToIdP: isIdpLoginUrl(idpLoginUrl),
    loginReturnedToRequestedGuiPath,
    // Backward-compatibility alias for older dashboards/evidence readers.
    loginReturnedToGui: loginReturnedToRequestedGuiPath,
    authMeAuthenticated,
    selectedAddressIsSwiss: selectedAddress.includes(',') && /\b\d{4}\b/.test(selectedAddress),
    addressSubmittedExactly: submittedAddressMatches,
    analyzeHttpOk: analyzeResponseStatus === 200,
    analyzePayloadOkFlag: Boolean(analyzeResponseBody && analyzeResponseBody.ok === true),
    analyzePayloadComplete: analyzeCompleteness.complete,
    terminalUiSignalObserved: Boolean(terminalUiSignalReason),
    phaseSuccessOrResultsReady: phaseStateNormalized === 'success' || resultRowCount > 0,
    resultsRendered: resultRowCount > 0,
    noErrorBox: !errorBoxText,
    no401AnalyzeFlow: !has401DuringAnalyzeFlow,
    noSessionExpiredSignals: sessionExpiredSignals.length === 0,
    noIdleFallback,
  };

  const ok = Object.values(checks).every((value) => value === true);

  const payload = {
    startedAtUtc,
    finishedAtUtc: new Date().toISOString(),
    target: {
      baseOrigin,
      allowedOrigins,
      allowedAuthorizeHosts,
      guiPath,
      expectedPostLoginPath,
      loginStartUrl,
    },
    runtime: {
      browser: 'playwright-chromium',
      headless,
      timeoutMs,
      runMarker,
      runMarkerSource,
      githubRunNumber,
      githubRunAttempt,
      githubRunId,
    },
    credentials: {
      usernameMasked: maskUsername(username),
    },
    addressSelection: {
      file: path.relative(repoRoot, addressFile),
      poolSize: addressPool.length,
      index: addressIndex,
      selectedAddress,
      runMarker,
      runMarkerSource,
    },
    login: {
      idpLoginUrl,
      postLoginUrl,
      finalUrl,
      authMeStatus,
      authMeAuthenticated,
      authMeBody,
    },
    analyze: {
      requestUrl: analyzeResponseUrl,
      responseStatus: analyzeResponseStatus,
      requestQuery: submittedQuery,
      requestPayload: analyzeRequestPayload,
      responsePayload: analyzeResponseBody,
      completeness: analyzeCompleteness,
    },
    uiState: {
      phaseText,
      phaseState,
      resultsMetaText,
      errorBoxText,
      resultRowCount,
      terminalUiSignal,
      terminalUiSignalTimeout,
      analyzeShellRecovery,
    },
    flowResponses,
    guardSignals: {
      sessionExpiredSignals,
    },
    checks,
    artifacts: {
      screenshot: screenshotRelPath,
    },
    ok,
  };

  const evidencePath = await writeEvidence(payload);
  emitSmokeSummary(payload, evidencePath);
  return ok;
}

run()
  .then((ok) => {
    if (!ok) {
      process.exit(1);
    }
  })
  .catch(async (error) => {
    const payload = {
      startedAtUtc: new Date().toISOString(),
      finishedAtUtc: new Date().toISOString(),
      target: {
        baseOrigin,
        allowedOrigins,
        allowedAuthorizeHosts,
        guiPath,
        expectedPostLoginPath,
        loginStartUrl,
      },
      runtime: {
        browser: 'playwright-chromium',
        headless,
        timeoutMs,
        runMarker,
        runMarkerSource,
        githubRunNumber,
        githubRunAttempt,
        githubRunId,
      },
      credentials: {
        usernameMasked: maskUsername(username),
      },
      error: normalizeError(error),
      ok: false,
    };

    const evidencePath = await writeEvidence(payload);
    emitSmokeSummary(payload, evidencePath);
    process.exit(1);
  });
