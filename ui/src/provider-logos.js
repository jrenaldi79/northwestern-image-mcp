import gemini from './assets/provider-gemini.svg';
import openai from './assets/provider-openai.svg';
import grok from './assets/provider-grok.svg';
import glm from './assets/provider-glm.svg';
import qwen from './assets/provider-qwen.svg';
import kimi from './assets/provider-kimi.svg';
import minimax from './assets/provider-minimax.svg';
import deepseek from './assets/provider-deepseek.svg';
const logos = { gemini, openai, grok, glm, qwen, kimi, minimax, deepseek };
const vendors = {google:'gemini', openai:'openai', 'x-ai':'grok', 'z-ai':'glm', thudm:'glm', qwen:'qwen', moonshotai:'kimi', minimax:'minimax', deepseek:'deepseek'};
export function providerLogo(node, model) {
  node.replaceChildren();
  const brand = vendors[typeof model === 'string' ? model.split('/')[0] : ''];
  node.hidden = !brand;
  if (!brand) return;
  const image = document.createElement('img'); image.src = logos[brand]; image.alt = ''; image.setAttribute('aria-hidden', 'true');
  image.className = 'provider-logo'; node.append(image);
}
