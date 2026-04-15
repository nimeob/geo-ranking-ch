#!/usr/bin/env node

/**
 * Check authoritative Easyname DNS answers for a hostname.
 *
 * Default use case (Issue #904):
 *   node scripts/check_easyname_authoritative_dns.js \
 *     --host api.dev.georanking.ch \
 *     --zone georanking.ch \
 *     --expect-cname swisstopo-dev-vpc-alb-989918850.eu-central-1.elb.amazonaws.com
 */

const dns = require('dns');

function usage() {
  return [
    'Usage: node scripts/check_easyname_authoritative_dns.js [options]',
    '',
    'Options:',
    '  --host <hostname>        Hostname to resolve (default: api.dev.georanking.ch)',
    '  --zone <zone>            DNS zone for SOA lookup (default: georanking.ch)',
    '  --expect-cname <target>  Expected CNAME target',
    '  -h, --help               Show this help and exit',
  ].join('\n');
}

function parseArgs(argv) {
  const args = {};
  const valueOptions = new Set(['--host', '--zone', '--expect-cname']);

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];

    if (token === '-h' || token === '--help') {
      args.help = true;
      continue;
    }

    if (!token.startsWith('--')) {
      throw new Error(`Unknown positional argument: ${token}`);
    }

    const eqIndex = token.indexOf('=');
    if (eqIndex > 0) {
      const optionName = token.slice(0, eqIndex);
      const inlineValue = token.slice(eqIndex + 1);
      const normalizedInlineValue = inlineValue.trim();
      if (!valueOptions.has(optionName)) {
        throw new Error(`Unknown option: ${optionName}`);
      }
      if (!normalizedInlineValue || normalizedInlineValue.startsWith('-')) {
        throw new Error(`Missing value for ${optionName}`);
      }
      args[optionName.slice(2)] = inlineValue;
      continue;
    }

    if (!valueOptions.has(token)) {
      throw new Error(`Unknown option: ${token}`);
    }

    const next = argv[i + 1];
    const normalizedNext = typeof next === 'string' ? next.trim() : '';
    if (!normalizedNext || normalizedNext.startsWith('-')) {
      throw new Error(`Missing value for ${token}`);
    }

    const key = token.slice(2);
    args[key] = next;
    i += 1;
  }

  return args;
}

function resolveWith(resolver, method, value) {
  return new Promise((resolve) => {
    resolver[method](value, (err, result) => {
      if (err) {
        resolve({ ok: false, error: err.code || err.message });
        return;
      }
      resolve({ ok: true, result });
    });
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(`${usage()}\n`);
    return;
  }

  const host = args.host || 'api.dev.georanking.ch';
  const zone = args.zone || 'georanking.ch';
  const expectedCname = (args['expect-cname'] || '').replace(/\.$/, '');

  const nameservers = [
    { name: 'ns1.easyname.eu', ip: '77.244.243.4' },
    { name: 'ns2.easyname.eu', ip: '77.244.244.138' },
  ];

  const defaultResolver = dns.promises;
  const report = {
    generated_at_utc: new Date().toISOString(),
    host,
    zone,
    expected_cname: expectedCname || null,
    nameservers,
    authoritative_answers: [],
    consistency: {
      same_cname_on_all_authoritative_ns: false,
      expected_cname_matches: expectedCname ? false : null,
    },
    target_resolution: null,
  };

  for (const ns of nameservers) {
    const resolver = new dns.Resolver();
    resolver.setServers([ns.ip]);

    const cname = await resolveWith(resolver, 'resolveCname', host);
    const soa = await resolveWith(resolver, 'resolveSoa', zone);

    report.authoritative_answers.push({
      nameserver: ns.name,
      nameserver_ip: ns.ip,
      cname,
      soa,
    });
  }

  const cnameValues = report.authoritative_answers
    .map((entry) => {
      if (!entry.cname.ok || !Array.isArray(entry.cname.result) || entry.cname.result.length === 0) {
        return null;
      }
      return entry.cname.result[0].replace(/\.$/, '');
    })
    .filter(Boolean);

  const uniqueCnameValues = [...new Set(cnameValues)];
  report.consistency.same_cname_on_all_authoritative_ns =
    uniqueCnameValues.length === 1 && cnameValues.length === nameservers.length;

  if (expectedCname) {
    report.consistency.expected_cname_matches =
      report.consistency.same_cname_on_all_authoritative_ns && uniqueCnameValues[0] === expectedCname;
  }

  const resolvedTarget = uniqueCnameValues[0] || expectedCname;
  if (resolvedTarget) {
    try {
      const ips = await defaultResolver.resolve4(resolvedTarget);
      report.target_resolution = {
        target: resolvedTarget,
        ips,
      };
    } catch (err) {
      report.target_resolution = {
        target: resolvedTarget,
        error: err.code || err.message,
      };
    }
  }

  const success = report.consistency.same_cname_on_all_authoritative_ns &&
    (report.consistency.expected_cname_matches !== false);

  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  process.exit(success ? 0 : 1);
}

if (require.main === module) {
  main().catch((err) => {
    process.stderr.write(`[easyname-dns] ERROR ${err.message}\n`);
    process.stderr.write(`${usage()}\n`);
    process.exit(2);
  });
}

module.exports = {
  parseArgs,
  usage,
};
