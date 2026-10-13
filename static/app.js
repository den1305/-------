/* 前端交互：文字查询、离线语音合成播放、按住说话（离线语音识别）。 */

const $ = (sel) => document.querySelector(sel);
const queryInput = $("#query");
const askBtn = $("#ask");
const micBtn = $("#mic");
const hint = $("#hint");
const result = $("#result");
const audio = $("#r-audio");

let audioUrl = null;   // 当前音频的 objectURL，便于释放
let lastNarrate = { zh: "", en: "" };  // 最近一次查询的中/英朗读稿
let voiceLang = "zh";  // 当前朗读语言：zh / en

function setHint(text, isError) {
  hint.textContent = text || "";
  hint.classList.toggle("error", !!isError);
}

/* ---------------- 查询与展示 ---------------- */

async function ask(name) {
  const value = (name ?? queryInput.value).trim();
  if (!value) {
    setHint("请输入景点名称", true);
    return;
  }
  result.hidden = true;
  setHint("查询中…");

  try {
    const resp = await fetch("/api/intro", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: value }),
    });
    const data = await resp.json();

    if (!data.found) {
      renderNotFound(value, data);
      return;
    }
    renderResult(data);
    setHint("");
    lastNarrate = data.narrate || { zh: "", en: "" };
    playNarration(lastNarrate[voiceLang], voiceLang);
  } catch (err) {
    setHint("请求失败：" + err.message, true);
  }
}

function renderNotFound(name, data) {
  result.hidden = false;
  $("#r-name").textContent = "未收录：" + name;
  $("#r-meta").innerHTML = "";
  $("#zh-title").textContent = "中文介绍";
  $("#en-title").textContent = "English";
  lastNarrate = { zh: "", en: "" };
  stopAudio();
  renderGallery([]);

  const suggestions = data.suggestions || [];
  const zhMsg = suggestions.length
    ? "本地词典中暂无该景点。你可能想找：" + suggestions.join("、")
    : "本地词典中暂无该景点，可在 data/spots.json 中补充。";
  const enMsg = suggestions.length
    ? "Not found in the local dictionary. Did you mean: " + suggestions.join(", ") + "?"
    : "Not found in the local dictionary. You can add it in data/spots.json.";

  fillLang("zh", { intro: zhMsg }, "");
  fillLang("en", { intro: enMsg }, "");
  setHint(data.error || "未收录该景点", true);
}

function renderResult(data) {
  const zh = data.zh || {};
  const en = data.en || {};
  result.hidden = false;
  $("#r-name").textContent = zh.name;
  $("#zh-title").textContent = "中文介绍";
  $("#en-title").textContent = "English · " + (en.name || "");

  const chips = [];
  if (zh.category) chips.push(zh.category);
  if (zh.location) chips.push(zh.location);
  (zh.tags || []).forEach((t) => chips.push(t));
  $("#r-meta").innerHTML = chips.map((c) => `<span class="chip">${escapeHtml(c)}</span>`).join("");

  fillLang("zh", zh);
  fillLang("en", en);
  renderGallery(zh.images, zh.name);

  if (data.match === "fuzzy" || data.match === "pinyin") {
    setHint("按相近名称匹配到「" + zh.name + "」");
  }
}

/* 渲染实景图片；没有图片时隐藏整个图片区。 */
function renderGallery(urls, alt) {
  const wrap = $("#gallery-wrap");
  const box = $("#gallery");
  const list = urls || [];
  box.innerHTML = "";
  wrap.hidden = list.length === 0;
  list.forEach((u) => {
    const link = document.createElement("a");
    link.className = "gallery-item";
    link.href = u;
    link.target = "_blank";
    link.rel = "noopener";
    const img = document.createElement("img");
    img.src = u;
    img.loading = "lazy";
    img.alt = (alt ? alt + " " : "") + "实景图片";
    link.appendChild(img);
    box.appendChild(link);
  });
}

/* 填充某一语言分栏（prefix: zh / en），placeholder 为缺失字段的占位符。 */
function fillLang(prefix, view, placeholder = "—") {
  const v = view || {};
  $("#" + prefix + "-intro").textContent = v.intro || placeholder;
  $("#" + prefix + "-history").textContent = v.history || placeholder;
  $("#" + prefix + "-open").textContent = v.open_info || placeholder;

  const list = $("#" + prefix + "-highlights");
  list.innerHTML = "";
  (v.highlights || []).forEach((h) => {
    const li = document.createElement("li");
    li.textContent = h;
    list.appendChild(li);
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

/* ---------------- 语音合成播放 ---------------- */

async function playNarration(text, lang = "en") {
  if (!text) return;
  stopAudio();
  setHint("语音合成中…");
  try {
    const resp = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      setHint(err.error || "语音合成失败", true);
      return;
    }
    const blob = await resp.blob();
    audioUrl = URL.createObjectURL(blob);
    audio.src = audioUrl;
    setHint("");
    await audio.play().catch(() => {}); // 自动播放被拦截时用户可手动点击
  } catch (err) {
    setHint("语音合成失败：" + err.message, true);
  }
}

function stopAudio() {
  audio.pause();
  audio.removeAttribute("src");
  if (audioUrl) {
    URL.revokeObjectURL(audioUrl);
    audioUrl = null;
  }
}

/* ---------------- 按住说话（录音 + 离线识别） ---------------- */

let recording = null;

async function startRecording() {
  if (recording) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setHint("当前浏览器不支持录音，请用文字输入", true);
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    const ctx = new AudioContext();
    const source = ctx.createMediaStreamSource(stream);
    const processor = ctx.createScriptProcessor(4096, 1, 1);
    const chunks = [];
    processor.onaudioprocess = (e) => {
      chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };
    source.connect(processor);
    processor.connect(ctx.destination);

    recording = { stream, ctx, source, processor, chunks, sampleRate: ctx.sampleRate };
    micBtn.classList.add("recording");
    setHint("正在录音… 松开结束");
  } catch (err) {
    setHint("无法访问麦克风：" + err.message, true);
  }
}

async function stopRecording() {
  if (!recording) return;
  const { stream, ctx, source, processor, chunks, sampleRate } = recording;
  recording = null;
  micBtn.classList.remove("recording");

  processor.disconnect();
  source.disconnect();
  stream.getTracks().forEach((t) => t.stop());
  await ctx.close();

  const merged = mergeChunks(chunks);
  if (merged.length < sampleRate * 0.2) {
    setHint("录音太短，请再说一次", true);
    return;
  }

  setHint("识别中…");
  const wav = await encodeWav16k(merged, sampleRate);
  try {
    const resp = await fetch("/api/asr", {
      method: "POST",
      headers: { "Content-Type": "audio/wav" },
      body: wav,
    });
    const data = await resp.json();
    if (data.text) {
      queryInput.value = data.text;
      ask(data.text);
    } else {
      setHint(data.error || "没听清，请再试一次", true);
    }
  } catch (err) {
    setHint("识别失败：" + err.message, true);
  }
}

function mergeChunks(chunks) {
  let total = 0;
  for (const c of chunks) total += c.length;
  const out = new Float32Array(total);
  let offset = 0;
  for (const c of chunks) {
    out.set(c, offset);
    offset += c.length;
  }
  return out;
}

/* 将任意采样率的单声道浮点采样重采样到 16kHz，并编码成 WAV Blob。 */
async function encodeWav16k(samples, sampleRate) {
  const target = 16000;
  const frames = Math.max(1, Math.ceil((samples.length * target) / sampleRate));
  const offline = new OfflineAudioContext(1, frames, target);
  const buffer = offline.createBuffer(1, samples.length, sampleRate);
  buffer.copyToChannel(samples, 0);
  const node = offline.createBufferSource();
  node.buffer = buffer;
  node.connect(offline.destination);
  node.start();
  const rendered = await offline.startRendering();
  return wavBlob(rendered.getChannelData(0), target);
}

function wavBlob(samples, sampleRate) {
  const len = samples.length;
  const buffer = new ArrayBuffer(44 + len * 2);
  const view = new DataView(buffer);
  const writeStr = (offset, str) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + len * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);          // PCM
  view.setUint16(22, 1, true);          // 单声道
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);          // 16bit
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, len * 2, true);
  let offset = 44;
  for (let i = 0; i < len; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return new Blob([view], { type: "audio/wav" });
}

/* ---------------- 事件绑定 ---------------- */

askBtn.addEventListener("click", () => ask());
queryInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") ask();
});
$("#replay").addEventListener("click", () => {
  playNarration(lastNarrate[voiceLang], voiceLang);
});

/* 朗读语言切换：切换后立即用新语言朗读当前景点 */
$("#voice-switch").addEventListener("click", (e) => {
  const btn = e.target.closest(".voice-btn");
  if (!btn) return;
  voiceLang = btn.dataset.lang;
  document.querySelectorAll("#voice-switch .voice-btn").forEach((b) => {
    b.classList.toggle("is-active", b === btn);
  });
  playNarration(lastNarrate[voiceLang], voiceLang);
});

micBtn.addEventListener("pointerdown", (e) => {
  e.preventDefault();
  startRecording();
});
window.addEventListener("pointerup", stopRecording);
window.addEventListener("pointercancel", stopRecording);
