const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { URL } = require('node:url');

function loadPlaywright() {
  const explicit = process.env.CHECKPOINT_RUNTIME_PLAYWRIGHT_MODULE;
  const candidates = [
    explicit,
    'D:/midscene/node_modules/playwright',
    'playwright',
  ].filter(Boolean);
  const errors = [];
  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch (error) {
      errors.push(`${candidate}: ${error.message}`);
    }
  }
  throw new Error(`Unable to load Playwright. Tried: ${errors.join(' | ')}`);
}

function sanitizeHeaders(headers) {
  const sanitized = {};
  for (const [key, value] of Object.entries(headers || {})) {
    const lowered = key.toLowerCase();
    if (['authorization', 'cookie', 'set-cookie', 'proxy-authorization'].includes(lowered)) {
      sanitized[key] = '<redacted>';
    } else {
      sanitized[key] = value;
    }
  }
  return sanitized;
}

function safeUrl(raw) {
  try {
    const parsed = new URL(raw);
    const pathValue = parsed.pathname || '/';
    return {
      path: pathValue,
      path_sha256: crypto.createHash('sha256').update(pathValue).digest('hex'),
      query_keys: [...parsed.searchParams.keys()].sort(),
    };
  } catch {
    return { path: '<invalid>', path_sha256: null, query_keys: [] };
  }
}

function sanitizeErrorDetail(value) {
  return String(value || '')
    .replace(/https?:\/\/[^\s"')]+/gi, '<url-redacted>')
    .replace(/\u001b\[[0-9;]*m/g, '');
}

function requestSignature(request) {
  const safe = safeUrl(request.url());
  let bodyKeys = [];
  const body = request.postData();
  if (body) {
    try {
      const parsed = JSON.parse(body);
      bodyKeys = Object.keys(parsed || {}).sort();
    } catch {}
  }
  return {
    method: request.method().toUpperCase(),
    path_sha256: safe.path_sha256,
    content_type: (request.headers()['content-type'] || '').split(';', 1)[0].trim().toLowerCase(),
    query_keys: safe.query_keys,
    body_keys: bodyKeys,
  };
}

function matchesReadonlyPost(request, signature, count) {
  const actual = requestSignature(request);
  const expected = {
    method: signature.method,
    path_sha256: signature.path_sha256,
    content_type: String(signature.content_type || '').split(';', 1)[0].trim().toLowerCase(),
    query_keys: [...(signature.query_keys || [])].sort(),
    body_keys: [...(signature.body_keys || signature.payload_keys || [])].sort(),
  };
  return count < signature.max_requests_per_session && JSON.stringify(actual) === JSON.stringify(expected);
}

async function assertPage(page, assertions, bucket, prefix) {
  if (assertions.title_contains) {
    const title = await page.title();
    bucket.assertions.push({ name: `${prefix}-title`, expected: assertions.title_contains, actual: title, passed: title.includes(assertions.title_contains) });
  }
  if (assertions.url_contains) {
    const parsed = new URL(page.url());
    const expected = assertions.url_contains;
    const domainAssertion = expected.includes('.') && !expected.includes('/');
    const passed = domainAssertion ? parsed.hostname.includes(expected) : parsed.pathname.includes(expected);
    bucket.assertions.push({ name: `${prefix}-url`, expected, actual: passed ? '<matched>' : '<not-matched>', passed });
  }
  if (assertions.visible_text) {
    const locator = page.getByText(assertions.visible_text, { exact: false }).first();
    const visible = await locator.isVisible({ timeout: 10000 }).catch(() => false);
    bucket.assertions.push({ name: `${prefix}-visible-text`, expected: assertions.visible_text, actual: visible, passed: visible });
  }
}

function buildLocator(page, locatorDef) {
  if (!locatorDef) return null;
  if (locatorDef.strategy === 'text') {
    return page.getByText(locatorDef.value, { exact: locatorDef.exact !== false });
  }
  if (locatorDef.strategy === 'role') {
    return page.getByRole(locatorDef.role, { name: locatorDef.value, exact: locatorDef.exact !== false });
  }
  if (locatorDef.strategy === 'test_id') {
    return page.getByTestId(locatorDef.value);
  }
  if (locatorDef.strategy === 'css') {
    return page.locator(locatorDef.value);
  }
  throw new Error(`Unsupported locator strategy: ${locatorDef.strategy}`);
}

async function main() {
  const inputPath = process.argv[2];
  const payload = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const output = {
    schema_version: 'checkpoint-runtime.playwright-output.v1',
    run_id: payload.run_id,
    correlation_id: payload.correlation_id,
    result: 'unknown',
    blocked_requests: [],
    responses: [],
    request_failures: [],
    assertions: [],
    artifacts: [],
    failure_attribution: null,
    semantic_readonly_post_count: 0,
    semantic_readonly_post_decisions: [],
  };
  const { chromium } = loadPlaywright();
  let browser;
  let context;
  try {
    browser = await chromium.launch({ headless: true });
    const contextOptions = { viewport: { width: 1280, height: 900 } };
    if (payload.proxy_server) {
      contextOptions.proxy = { server: payload.proxy_server };
    }
    context = await browser.newContext(contextOptions);
    await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
    await context.route('**/*', async route => {
      const method = route.request().method().toUpperCase();
      if (method === 'POST' && (payload.readonly_post_signatures || []).some(signature => matchesReadonlyPost(route.request(), signature, output.semantic_readonly_post_count))) {
        output.semantic_readonly_post_count += 1;
        const signature = requestSignature(route.request());
        output.semantic_readonly_post_decisions.push({ decision: 'allowed', ...signature, count: output.semantic_readonly_post_count });
        await route.continue();
        return;
      }
      if ((payload.forbidden_methods || []).includes(method)) {
        output.blocked_requests.push({ method, ...safeUrl(route.request().url()) });
        await route.abort('blockedbyclient');
        return;
      }
      await route.continue();
    });
    const page = await context.newPage();
    page.on('response', response => {
      output.responses.push({
        ...safeUrl(response.url()),
        status: response.status(),
        headers: sanitizeHeaders(response.headers()),
      });
    });
    page.on('requestfailed', request => {
      output.request_failures.push({
        method: request.method(),
        ...safeUrl(request.url()),
        failure: request.failure(),
      });
    });

    const baseUrl = process.env[payload.base_url_ref || 'CHECKPOINT_RUNTIME_BASE_URL'];
    if (!baseUrl) throw new Error('Missing in-memory base URL');
    await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await assertPage(page, payload.module_assertions, output, 'module');
    const routeCheck = output.assertions.find(item => item.name === 'module-url');
    const uiChecks = output.assertions.filter(item => ['module-title', 'module-visible-text'].includes(item.name) && item.passed);
    output.module_signature = {
      ok: Boolean(routeCheck && routeCheck.passed && uiChecks.length >= 2),
      route_verified: Boolean(routeCheck && routeCheck.passed),
      ui_features_verified: uiChecks.map(item => item.name),
      readonly_network_evidence_ref: null,
      entry_midscene_calls: 0,
    };
    output.assertions.push({ name: 'module-signature', expected: 'route + two UI features', actual: output.module_signature, passed: output.module_signature.ok });
    output.link_count = await page.locator('a').count().catch(() => 0);
    await page.screenshot({ path: payload.before_screenshot, fullPage: true });
    output.artifacts.push({ type: 'screenshot', path: payload.before_screenshot });

    if (payload.button) {
      const locator = buildLocator(page, payload.button.locator);
      await locator.click({ timeout: 15000 });
      await page.waitForLoadState('domcontentloaded', { timeout: 30000 }).catch(() => {});
      await assertPage(page, payload.button.result_assertions, output, 'button');
      await page.screenshot({ path: payload.after_screenshot, fullPage: true });
      output.artifacts.push({ type: 'screenshot', path: payload.after_screenshot });
    }

    await context.tracing.stop({ path: payload.trace_path });
    output.artifacts.push({ type: 'trace', path: payload.trace_path });
    const failed = output.assertions.filter(item => !item.passed);
    output.result = failed.length ? 'failed' : 'passed';
    if (failed.length) {
      output.failure_attribution = {
        layer: 'assertion',
        failure_type: 'assertion_mismatch',
        detail: failed.map(item => item.name).join(', '),
        confidence: 1,
      };
    }
    await context.close();
  } catch (error) {
    if (context) {
      await context.tracing.stop({ path: payload.trace_path }).then(() => {
        output.artifacts.push({ type: 'trace', path: payload.trace_path });
      }).catch(() => {});
    }
    const detail = sanitizeErrorDetail(error && error.stack ? error.stack : error);
    const isNetwork = detail.includes('ERR_CONNECTION') || detail.includes('ERR_TUNNEL') || detail.includes('net::');
    output.result = 'failed';
    output.failure_attribution = {
      layer: isNetwork ? 'env' : 'runtime',
      failure_type: isNetwork ? 'network_error' : 'unexpected',
      detail,
      confidence: 1,
    };
  } finally {
    if (context) await context.close().catch(() => {});
    if (browser) await browser.close().catch(() => {});
    fs.writeFileSync(payload.output_path, JSON.stringify(output, null, 2), 'utf8');
  }
  process.exit(output.result === 'passed' ? 0 : 1);
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
