import { readFile } from 'node:fs/promises';
const html = await readFile(new URL('../../../src/openrouter_image_mcp/ui/settings.html', import.meta.url), 'utf8')
  .catch(error => { if (error.code === 'ENOENT') return '<!doctype html><body></body>'; throw error; });
export const view = (changes = {}) => ({ settings_id: 'settings-1', revision: 1, general_default: 'google/example',
  family_defaults: { google: 'google/example', openai: '', open_weight: '' }, onboarding_completed: false,
  workspace_id: 'workshop', cohort: 'Class A', image_models: [], models: [
    { id: 'google/example', name: 'Gemini Example', family: 'google', context_length: 4096, created: Math.floor(Date.now() / 1000) - 86400, pricing: { prompt: '0.000001', completion: '0.000002' } },
    { id: 'openai/example', name: 'GPT Example', family: 'openai', context_length: 8192, created: Math.floor(Date.now() / 1000) - 86400, pricing: { prompt: '0.000003', completion: '0.000004' } },
    { id: 'qwen/qwen-example', name: 'Qwen Example', family: 'open_weight', context_length: 16384, created: Math.floor(Date.now() / 1000) - 86400, pricing: { prompt: '0', completion: '0' } },
  ], ...changes });
export const settings = (changes = {}) => ({ content: [], _meta: { sidecarSettings: view(changes) } });
export const failure = text => ({ isError: true, content: [{ type: 'text', text }] });
export const demoResult = (changes = {}) => ({ content: [], _meta: { advisorResult: { job_id: 'demo-1', status: 'completed', answer: 'A short synthetic answer.', model: 'google/example', cost_usd: 0.0001, ...changes } } });
export async function openSettings(page, { initial = { content: [], structuredContent: { mode: 'onboarding' } }, responses = {}, capabilities = { serverTools: {} }, delay = 0, maxHeight = 0 } = {}) {
  const requests = [];
  page.on('request', request => requests.push(request.url()));
  await page.route('**/*', route => route.abort());
  await page.setContent('<iframe title="Sidecar settings" sandbox="allow-scripts" style="width:700px;height:700px;border:0"></iframe>');
  await page.evaluate(({ html, initial, responses, capabilities, delay, maxHeight }) => {
    window.hostMessages = []; window.toolCounts = {}; window.activeFetches = 0; window.maxActiveFetches = 0;
    const iframe = document.querySelector('iframe');
    const reply = (id, value) => iframe.contentWindow.postMessage({ jsonrpc: '2.0', id, ...value }, '*');
    window.notify = (method, params) => iframe.contentWindow.postMessage({ jsonrpc: '2.0', method, params }, '*');
    window.addEventListener('message', event => {
      if (event.source !== iframe.contentWindow) return;
      const message = event.data; window.hostMessages.push(message);
      if (message.method === 'ui/initialize') {
        reply(message.id, { result: { protocolVersion: '2026-01-26', hostInfo: { name: 'Offline settings host', version: '1' }, hostCapabilities: capabilities, hostContext: { theme: 'light', displayMode: 'inline' } } });
        if (initial) window.notify('ui/notifications/tool-result', initial);
      }
      if (message.method === 'ui/notifications/size-changed') iframe.style.height = `${maxHeight > 0 ? Math.min(message.params.height, maxHeight) : message.params.height}px`;
      if (message.method === 'ui/message') reply(message.id, { result: {} });
      if (message.method === 'tools/call') {
        const name = message.params.name; const index = window.toolCounts[name] ?? 0; window.toolCounts[name] = index + 1;
        const sequence = responses[name] ?? (name === 'get_sidecar_settings' ? [{ content: [], _meta: { sidecarSettings: window.defaultView } }] : []);
        let next = sequence[Math.min(index, sequence.length - 1)] ?? { isError: true, content: [] };
        if (name === 'set_sidecar_preferences' && !responses[name]) {
          const args = message.params.arguments;
          window.defaultView = { ...window.defaultView, ...args, revision: args.expected_revision + 1,
            family_defaults: { ...window.defaultView.family_defaults, ...args.family_defaults } };
          next = { content: [], structuredContent: window.defaultView };
        }
        if (name === 'get_advisor_result' || name === 'get_sidecar_demo') { window.activeFetches++; window.maxActiveFetches = Math.max(window.activeFetches, window.maxActiveFetches); }
        setTimeout(() => {
          if (name === 'get_advisor_result' || name === 'get_sidecar_demo') window.activeFetches--;
          reply(message.id, next.rpcError ? { error: next.rpcError } : { result: next });
        }, delay);
      }
    });
    window.defaultView = responses.defaultView;
    iframe.srcdoc = html;
  }, { html, initial, responses: { defaultView: view(), ...responses }, capabilities, delay, maxHeight });
  return { viewer: page.frameLocator('iframe'), requests };
}
export const calls = (page, name) => page.evaluate(tool => window.hostMessages.filter(message => message.method === 'tools/call' && message.params.name === tool).map(message => message.params.arguments), name);
