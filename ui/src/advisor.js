import { App } from '@modelcontextprotocol/ext-apps';
import { renderMarkdown } from './markdown.js';
import { providerLogo } from './provider-logos.js';

const app = new App({ name: 'OpenRouter Sidecar advisor result', version: '1.0.0' }, {}, { autoResize: true });
const element = id => document.getElementById(id);
const answer = element('answer');
const preview = element('preview');
const terminal = new Set(['completed', 'failed', 'interrupted']);
const states = new Set(['queued', 'running', ...terminal]);
const pollInterval = 1000;
let connected = false;
let disposed = false;
let blocked = false;
let generation = 0;
let controller = new AbortController();
let original = null;
let renderedAnswer = '';
let summary = null;
let prepared = null;
let selection = '';
let summaryBusy = false;
let exportBusy = false;
let sendBusy = false;
let followUpBusy = false;
let sendRejected = false;
let fetchTail = Promise.resolve();
const timers = new Set();

const string = value => typeof value === 'string' ? value : '';
const stateLabel = status => string(status).charAt(0).toUpperCase() + string(status).slice(1);
const costLabel = cost => typeof cost === 'number' && Number.isFinite(cost) && cost >= 0
  ? `Cost: $${cost}` : 'Cost: unavailable';
const canCallTools = () => connected && !!app.getHostCapabilities()?.serverTools;
const canSend = () => connected && !!app.getHostCapabilities()?.message?.text;

function stopPolling() {
  for (const timer of timers) clearTimeout(timer);
  timers.clear();
  controller.abort();
  controller = new AbortController();
  generation++;
}

function setTheme(context) {
  if (context?.theme === 'light' || context?.theme === 'dark') document.documentElement.dataset.theme = context.theme;
}

function updateButtons() {
  const following = followUpBusy || summaryBusy || exportBusy || sendBusy;
  const canFollowUp = !disposed && !blocked && canCallTools() && original?.kind === 'answer'
    && original.status === 'completed' && !!string(original.chat_id) && !following;
  element('follow-up').disabled = disposed || (!original && !blocked) || !canCallTools();
  element('follow-up').readOnly = !canFollowUp;
  element('follow-up-send').disabled = !canFollowUp || !element('follow-up').value.trim();
  element('settings').disabled = !canCallTools() || disposed || followUpBusy;
  const available = !disposed && !blocked && !followUpBusy && !!original && !!string(original.answer).trim();
  element('prepare-full').disabled = !available || summaryBusy || sendBusy;
  element('prepare-selection').disabled = !available || summaryBusy || sendBusy || !selection.trim();
  element('summarize').disabled = !available || original.status !== 'completed' || summaryBusy || sendBusy || !canCallTools();
  element('export').disabled = !available || exportBusy || sendBusy || !canCallTools();
  preview.disabled = !prepared || summaryBusy || disposed || blocked || sendBusy;
  const ready = available && prepared && !!preview.value.trim() && !summaryBusy && !sendBusy;
  element('send').disabled = !ready || !canSend();
  element('copy').hidden = !prepared || (canSend() && !sendRejected);
  element('copy').disabled = !ready;
}

function showError(message) {
  element('error').textContent = message;
}

function suppressResult(message) {
  blocked = true;
  stopPolling();
  original = null;
  summary = null;
  prepared = null;
  selection = '';
  summaryBusy = exportBusy = sendBusy = followUpBusy = false;
  answer.textContent = '';
  renderedAnswer = '';
  preview.value = '';
  element('prompt').textContent = '';
  element('prompt-details').hidden = true;
  element('summary-text').textContent = '';
  element('summary-status').textContent = '';
  element('summary-error').textContent = '';
  element('preview-context').textContent = '';
  element('copy-text').value = '';
  element('copy-section').hidden = true;
  element('export-status').textContent = '';
  element('handoff-status').textContent = '';
  element('job-status').textContent = 'Result unavailable';
  showError(message);
  updateButtons();
}

function toolError(result) {
  return (result?.content ?? []).filter(item => item.type === 'text').map(item => string(item.text)).filter(Boolean).join('\n') || 'The host could not complete the request.';
}

function validateStatus(data, expectedId) {
  return data && typeof data.job_id === 'string' && data.job_id.length > 0 && states.has(data.status)
    && (!expectedId || data.job_id === expectedId);
}

function renderOriginal(data) {
  original = data;
  element('result-title').textContent = string(data.title);
  element('model').textContent = string(data.model);
  providerLogo(element('model-logo'), string(data.model));
  element('result-id').textContent = `Result: ${data.job_id}`;
  element('job-status').textContent = `${stateLabel(data.status)}${data.status === 'queued' || data.status === 'running' ? ' · Updating locally…' : ''}`;
  element('cost').textContent = costLabel(data.cost_usd);
  element('cleanup').textContent = data.cleanup_pending ? 'Cleanup pending' : '';
  element('prompt-details').hidden = typeof data.prompt !== 'string';
  element('prompt').textContent = string(data.prompt);
  const text = string(data.answer);
  // Keep a user's selection intact when a poll changes only metadata.
  if (renderedAnswer !== text) {
    selection = '';
    const wasAtBottom = answer.scrollHeight - answer.scrollTop - answer.clientHeight < 24;
    const wasEmpty = !renderedAnswer;
    const oldTop = answer.scrollTop;
    renderMarkdown(answer, text);
    // Do not pull a reader away from older text as streaming updates arrive.
    answer.scrollTop = !wasEmpty && wasAtBottom ? answer.scrollHeight : oldTop;
    renderedAnswer = text;
  }
  element('answer-state').textContent = data.status === 'completed' ? 'Completed answer'
    : text ? 'Partial answer · This result is not completed.' : 'Waiting for answer text…';
  element('answer-state').hidden = data.status === 'completed';
  showError(string(data.error));
  updateButtons();
}

function handoffHeader() {
  if (!prepared) return '';
  const suffix = prepared.summaryId ? `; summary ${prepared.summaryId}` : '';
  const partial = prepared.partial ? ' (partial result)' : '';
  return `Advisor ${prepared.kind}${partial} from ${prepared.model} (result ${prepared.sourceId}${suffix}):`;
}

function handoffText() { return `${handoffHeader()}\n\n${preview.value}`; }

function prepare(kind, text, summaryId = null) {
  if (!original || blocked || disposed) return;
  prepared = { kind, sourceId: original.job_id, model: string(original.model), summaryId, partial: original.status !== 'completed' };
  preview.value = text;
  sendRejected = false;
  element('preview-section').hidden = false;
  element('preview-context').textContent = 'Only the reviewed text below will be shared.';
  element('copy-section').hidden = true;
  element('copy-text').value = '';
  element('handoff-status').textContent = canSend() ? '' : 'This host does not support sending to the parent chat. Copy your reviewed message instead.';
  updateButtons();
}

function captureSelection() {
  if (disposed || blocked) return;
  const selected = window.getSelection();
  const range = selected?.rangeCount === 1 ? selected.getRangeAt(0) : null;
  selection = range && answer.contains(range.startContainer) && answer.contains(range.endContainer)
    ? selected.toString() : '';
  updateButtons();
}

async function callTool(name, jobId) {
  const signal = controller.signal;
  const request = () => {
    signal.throwIfAborted();
    return app.callServerTool({ name, arguments: { job_id: jobId } }, { signal, timeout: 15000 });
  };
  if (name !== 'get_advisor_result') return request();
  // Polling and explicit handoff checks share one serial queue. An edited
  // preview can be sent while partial text is streaming without overlapping
  // the app-only fetch that confirms ownership before leaving this viewer.
  const pending = fetchTail.then(request, request);
  fetchTail = pending.then(() => undefined, () => undefined);
  return pending;
}

async function verifyHandoff(snapshot, token) {
  try {
    if (!canCallTools()) throw new Error('This host cannot verify access to the result.');
    const ids = snapshot.summaryId && snapshot.summaryId !== snapshot.sourceId
      ? [snapshot.sourceId, snapshot.summaryId] : [snapshot.sourceId];
    for (const id of ids) {
      const result = await callTool('get_advisor_result', id);
      if (disposed || blocked || token !== generation) return false;
      if (result.isError) throw new Error(toolError(result));
      const data = result._meta?.advisorResult;
      if (!validateStatus(data, id) || typeof data.answer !== 'string' || typeof data.prompt !== 'string'
        || (id === snapshot.summaryId && (data.kind !== 'summary' || data.source_job_id !== snapshot.sourceId))) {
        throw new Error('The host could not verify the original result and summary.');
      }
    }
    // Do not render refreshes here: the text reviewed by the user is a snapshot.
    return true;
  } catch (error) {
    if (!disposed && !blocked && token === generation) {
      suppressResult(`Unable to verify access before handoff: ${string(error?.message) || 'Host request failed.'}`);
    }
    return false;
  }
}

function schedulePoll(jobId, isSummary, token) {
  const timer = setTimeout(() => {
    timers.delete(timer);
    if (!disposed && !blocked && token === generation) void poll(jobId, isSummary, token);
  }, pollInterval);
  timers.add(timer);
}

function renderSummary(data) {
  summary = data;
  element('summary-status').textContent = `Summary: ${stateLabel(data.status)} · ${costLabel(data.cost_usd)}${data.cleanup_pending ? ' · Cleanup pending' : ''}`;
  renderMarkdown(element('summary-text'), terminal.has(data.status) ? '' : string(data.answer));
  element('summary-error').textContent = string(data.error);
  if (terminal.has(data.status)) {
    summaryBusy = false;
    if (data.status === 'completed' && string(data.answer).trim()) {
      prepare('summary', data.answer, data.job_id);
    } else {
      element('summary-error').textContent = string(data.error) || 'Summary did not complete. Nothing was sent.';
    }
  }
  updateButtons();
}

async function poll(jobId, isSummary, token) {
  if (disposed || blocked || token !== generation) return;
  try {
    const result = await callTool('get_advisor_result', jobId);
    if (disposed || blocked || token !== generation) return;
    // An app-only fetch is the only source of display text. Never fall back to
    // public content/structuredContent when the UI-only envelope is missing.
    if (result.isError) { suppressResult(toolError(result)); return; }
    const data = result._meta?.advisorResult;
    if (!validateStatus(data, jobId) || typeof data.answer !== 'string' || typeof data.prompt !== 'string'
      || (isSummary && (data.kind !== 'summary' || data.source_job_id !== original?.job_id))) {
      suppressResult('The host returned an invalid advisor result. Reopen this result to try again.');
      return;
    }
    if (isSummary) renderSummary(data);
    else renderOriginal(data);
    if (!terminal.has(data.status)) schedulePoll(jobId, isSummary, token);
  } catch (error) {
    if (disposed || blocked || token !== generation) return;
    suppressResult(`Unable to retrieve this result: ${string(error?.message) || 'Host request failed.'}`);
  }
}

function beginPolling() {
  if (!original || disposed || blocked || !connected) return;
  if (!canCallTools()) {
    showError('This host cannot retrieve the local answer. Open the result in a host that supports app tools.');
    return;
  }
  void poll(original.job_id, false, generation);
}

function receiveResult(result) {
  if (disposed) return;
  stopPolling();
  if (result.isError) { suppressResult(toolError(result)); return; }
  const data = result.structuredContent;
  if (!validateStatus(data)) { suppressResult('No valid advisor result was supplied by the host.'); return; }
  blocked = false;
  original = null;
  summary = null;
  prepared = null;
  selection = '';
  summaryBusy = exportBusy = sendBusy = sendRejected = followUpBusy = false;
  preview.value = '';
  element('preview-section').hidden = true;
  element('prompt-details').open = false;
  element('summary-status').textContent = '';
  element('summary-error').textContent = '';
  element('summary-text').textContent = '';
  element('export-status').textContent = '';
  element('handoff-status').textContent = '';
  element('copy-text').value = '';
  element('copy-section').hidden = true;
  // Public tool data identifies the job; even unexpected public answer fields
  // must not be rendered. The first app-only fetch also rechecks ownership.
  const { prompt, answer: ignoredAnswer, ...status } = data;
  renderOriginal(status);
  beginPolling();
}

element('follow-up').addEventListener('input', updateButtons);
element('follow-up-send').addEventListener('click', async () => {
  const draft = element('follow-up').value.trim();
  if (element('follow-up-send').disabled || !draft || !original) return;
  const token = generation;
  const source = { ...original };
  followUpBusy = true;
  element('follow-up-status').textContent = 'Sending to advisor…';
  updateButtons();
  try {
    const result = await app.callServerTool({ name: 'send_advisor_message', arguments: {
      chat_id: source.chat_id, prompt: draft,
    } }, { signal: controller.signal, timeout: 15000 });
    if (disposed || blocked || token !== generation) return;
    if (result.isError) {
      suppressResult(toolError(result));
      element('follow-up-status').textContent = 'Follow-up not confirmed. Draft kept. Reopen the chat before trying again.';
      return;
    }
    const data = result.structuredContent;
    if (!validateStatus(data) || data.job_id === source.job_id || data.chat_id !== source.chat_id
      || data.kind !== 'answer' || data.model !== source.model) {
      suppressResult('The host returned an invalid follow-up job. Reopen the chat.');
      element('follow-up-status').textContent = 'Follow-up not confirmed. Draft kept.';
      return;
    }
    element('follow-up').value = '';
    answer.textContent = ''; renderedAnswer = ''; answer.scrollTop = 0;
    receiveResult(result);
    element('follow-up-status').textContent = 'Follow-up sent. The reply appears above.';
  } catch {
    if (disposed || blocked || token !== generation) return;
    // An uncertain submission may already have started inference. Never retry it.
    suppressResult('Unable to confirm the follow-up. Reopen the chat to check its status before retrying.');
    element('follow-up-status').textContent = 'Follow-up not confirmed. Draft kept; check the chat before resending.';
  } finally {
    if (!disposed && token === generation) { followUpBusy = false; updateButtons(); }
  }
});

element('prepare-selection').addEventListener('pointerdown', event => event.preventDefault());
element('settings').addEventListener('click', async () => {
  if (!canCallTools() || disposed) return;
  const text = 'Open Sidecar settings using open_sidecar_settings with mode settings.';
  if (!canSend()) {
    element('settings-request-section').hidden = false;
    element('settings-request').value = text;
    element('settings-status').textContent = 'Copy this request into the parent chat to open settings.';
    return;
  }
  element('settings').disabled = true;
  try {
    const result = await app.sendMessage({ role: 'user', content: [{ type: 'text', text }] }, { signal: controller.signal, timeout: 15000 });
    if (disposed) return;
    if (result.isError) throw new Error('Host rejected settings request');
    element('settings-status').textContent = 'Requested settings in the parent chat. No answer text was sent.';
  } catch {
    if (!disposed) {
      element('settings-request-section').hidden = false;
      element('settings-request').value = text;
      element('settings-status').textContent = 'Settings request was not confirmed. Copy this request into the parent chat.';
    }
  } finally { if (!disposed) updateButtons(); }
});
element('prepare-selection').addEventListener('click', () => {
  if (selection.trim()) prepare('selection', selection);
});
element('prepare-full').addEventListener('click', () => prepare('answer', string(original?.answer)));
document.addEventListener('selectionchange', captureSelection);
preview.addEventListener('input', () => {
  element('handoff-status').textContent = canSend() ? '' : 'This host does not support sending to the parent chat. Copy your reviewed message instead.';
  element('copy-section').hidden = true;
  updateButtons();
});

element('summarize').addEventListener('click', async () => {
  if (!original || original.status !== 'completed' || summaryBusy || !canCallTools()) return;
  const sourceId = original.job_id;
  const token = generation;
  summaryBusy = true;
  prepared = null;
  preview.value = '';
  element('preview-section').hidden = false;
  element('preview-context').textContent = `Preparing a summary of result ${sourceId} from ${string(original.model)}.`;
  element('summary-status').textContent = 'Summary: Queued · Uses a new advisor call and incurs cost.';
  element('summary-error').textContent = '';
  element('summary-text').textContent = '';
  element('handoff-status').textContent = '';
  element('copy-section').hidden = true;
  updateButtons();
  try {
    const result = await callTool('summarize_advisor_result', sourceId);
    if (disposed || blocked || token !== generation) return;
    // Tool failure may mean ownership/sign-in changed. Without a typed error
    // code, clear cached text rather than keep offering an unsafe handoff.
    if (result.isError) { suppressResult(toolError(result)); return; }
    const data = result.structuredContent;
    if (!validateStatus(data) || data.kind !== 'summary' || data.source_job_id !== sourceId || data.job_id === sourceId) {
      throw new Error('The host returned an invalid summary job.');
    }
    summary = data;
    element('summary-status').textContent = `Summary: ${stateLabel(data.status)} · ${costLabel(data.cost_usd)}`;
    // A summary body is fetched privately even when the enqueue status is terminal.
    await poll(summary.job_id, true, token);
  } catch (error) {
    if (disposed || blocked || token !== generation) return;
    summaryBusy = false;
    element('summary-status').textContent = 'Summary unavailable';
    element('summary-error').textContent = `${string(error?.message) || 'Summary request failed.'} Nothing was sent.`;
    updateButtons();
  }
});

element('export').addEventListener('click', async () => {
  if (!original || exportBusy || !canCallTools()) return;
  const token = generation;
  exportBusy = true;
  element('export-status').textContent = 'Saving Markdown…';
  updateButtons();
  try {
    // Always export the displayed original, including after preparing a summary.
    const result = await callTool('export_advisor_result', original.job_id);
    if (disposed || blocked || token !== generation) return;
    if (result.isError) { suppressResult(toolError(result)); return; }
    const path = result._meta?.advisorExport?.path;
    if (result.structuredContent?.saved !== true || typeof path !== 'string' || !path) throw new Error('The host did not confirm a saved file.');
    element('export-status').textContent = `Saved Markdown: ${path}`;
  } catch (error) {
    if (disposed || blocked || token !== generation) return;
    element('export-status').textContent = `Unable to save: ${string(error?.message) || 'Host request failed.'}`;
  } finally {
    if (token === generation) { exportBusy = false; updateButtons(); }
  }
});

element('send').addEventListener('click', async () => {
  if (!prepared || !preview.value.trim() || !canSend() || blocked || disposed || summaryBusy || sendBusy) return;
  const token = generation;
  const snapshot = { ...prepared };
  const text = handoffText();
  sendBusy = true;
  element('handoff-status').textContent = 'Verifying result access…';
  updateButtons();
  try {
    if (!await verifyHandoff(snapshot, token)) return;
    if (disposed || blocked || token !== generation) return;
    element('handoff-status').textContent = 'Sending…';
    // This explicit button handler is the only path to parent-chat content.
    const result = await app.sendMessage({ role: 'user', content: [{ type: 'text', text }] }, { signal: controller.signal, timeout: 15000 });
    if (disposed || blocked || token !== generation) return;
    if (result.isError) throw new Error('Host rejected the message.');
    element('handoff-status').textContent = 'Sent to parent chat.';
  } catch (error) {
    if (disposed || blocked || token !== generation) return;
    sendRejected = true;
    element('handoff-status').textContent = `${string(error?.message) || 'Unable to send.'} Nothing was confirmed sent. You can copy your reviewed message.`;
  } finally {
    if (token === generation) { sendBusy = false; updateButtons(); }
  }
});

element('copy').addEventListener('click', async () => {
  if (!prepared || !preview.value.trim() || blocked || disposed || summaryBusy || sendBusy) return;
  const token = generation;
  const snapshot = { ...prepared };
  const text = handoffText();
  sendBusy = true;
  element('handoff-status').textContent = 'Verifying result access…';
  updateButtons();
  try {
    if (!await verifyHandoff(snapshot, token)) return;
    if (disposed || blocked || token !== generation) return;
    element('copy-text').value = text;
    element('copy-section').hidden = false;
    element('copy-text').focus();
    element('copy-text').select();
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(text);
    if (disposed || blocked || token !== generation) return;
    element('handoff-status').textContent = 'Copied message. Paste it into the parent chat when ready.';
  } catch {
    if (disposed || blocked || token !== generation) return;
    element('handoff-status').textContent = 'Clipboard access is unavailable. Select and copy the message below, then paste it into the parent chat.';
  } finally {
    if (token === generation) { sendBusy = false; updateButtons(); }
  }
});

function dispose() {
  disposed = true;
  stopPolling();
  document.removeEventListener('selectionchange', captureSelection);
  updateButtons();
}

// Register before connecting: hosts can deliver an initial result immediately.
app.ontoolresult = receiveResult;
app.onhostcontextchanged = setTheme;
app.onteardown = async () => { dispose(); return {}; };
window.addEventListener('pagehide', dispose, { once: true });
app.connect().then(() => {
  if (disposed) return;
  connected = true;
  setTheme(app.getHostContext());
  updateButtons();
  beginPolling();
}).catch(error => {
  if (!disposed) suppressResult(`Unable to connect to the advisor host: ${string(error?.message) || 'Connection failed.'}`);
});
