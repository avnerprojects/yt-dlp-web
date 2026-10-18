const $ = (sel) => document.querySelector(sel);

const els = {
  url: $("#url"),
  fetch: $("#fetch"),
  status: $("#status"),
  result: $("#result"),
  thumb: $("#thumb"),
  title: $("#title"),
  submeta: $("#submeta"),
  videoRes: $("#video-res"),
  bgRes: $("#bg-res"),
  audioQ: $("#audio-q"),
};

let currentUrl = "";

/* ---------- Status helpers ---------- */
function showStatus(msg, kind = "") {
  els.status.textContent = msg;
  els.status.className = `status ${kind}`.trim();
  els.status.hidden = false;
}
function hideStatus() {
  els.status.hidden = true;
}

/* ---------- Fetch metadata ---------- */
async function fetchInfo() {
  const url = els.url.value.trim();
  if (!url) {
    showStatus("Paste a YouTube URL first.", "error");
    return;
  }

  els.fetch.disabled = true;
  els.result.hidden = true;
  showStatus("Reading video…", "loading");

  try {
    const res = await fetch(`/api/info?url=${encodeURIComponent(url)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");

    currentUrl = url;
    renderResult(data);
    hideStatus();
    els.result.hidden = false;
  } catch (err) {
    showStatus(err.message, "error");
  } finally {
    els.fetch.disabled = false;
  }
}

/* ---------- Render ---------- */
function renderResult(data) {
  els.thumb.src = data.thumbnail || "";
  els.thumb.style.display = data.thumbnail ? "block" : "none";

  // Title links back to the video (opens in a new tab).
  els.title.textContent = "";
  const link = document.createElement("a");
  link.href = currentUrl;
  link.target = "_blank";
  link.rel = "noopener";
  link.textContent = data.title || "Untitled";
  els.title.appendChild(link);

  const bits = [data.uploader, data.duration].filter(Boolean);
  els.submeta.textContent = bits.join(" · ");

  // Video + silent-video resolutions share the same list.
  const resOptions = data.video_resolutions
    .map(
      (v) =>
        `<option value="${v.height}">${v.label}${
          v.filesize ? ` · ${v.filesize}` : ""
        }</option>`
    )
    .join("");
  els.videoRes.innerHTML = resOptions || `<option value="1080">Best available</option>`;
  els.bgRes.innerHTML = resOptions || `<option value="1080">Best available</option>`;

  // Audio options.
  els.audioQ.innerHTML =
    data.audio_options
      .map((a) => `<option value="${a.format_id}">${a.label}${a.filesize ? ` · ${a.filesize}` : ""}</option>`)
      .join("") || `<option value="bestaudio/best">Best available</option>`;
}

/* ---------- Tabs ---------- */
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("is-active"));
    document.querySelectorAll(".pane").forEach((p) => p.classList.remove("is-active"));
    tab.classList.add("is-active");
    $(`[data-pane="${tab.dataset.mode}"]`).classList.add("is-active");
  });
});

/* ---------- Download ---------- */
document.querySelectorAll("[data-download]").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (!currentUrl) return;
    const mode = btn.dataset.download;
    let quality = "";
    if (mode === "video") quality = els.videoRes.value;
    else if (mode === "background") quality = els.bgRes.value;
    else if (mode === "audio") quality = els.audioQ.value;

    const params = new URLSearchParams({ url: currentUrl, mode });
    if (quality) params.set("quality", quality);

    showStatus("Preparing your download… this can take a moment for large files.", "loading");
    // Let the browser handle the file transfer via a hidden navigation.
    const frame = document.createElement("iframe");
    frame.style.display = "none";
    frame.src = `/api/download?${params.toString()}`;
    document.body.appendChild(frame);
    // Clear the loading note after the request has had time to start.
    setTimeout(hideStatus, 4000);
  });
});

/* ---------- Audio info modal ---------- */
const audioModal = $("#audio-modal");
$("#audio-info-btn").addEventListener("click", () => {
  audioModal.hidden = false;
});
$("#audio-modal-close").addEventListener("click", () => {
  audioModal.hidden = true;
});
audioModal.addEventListener("click", (e) => {
  if (e.target === audioModal) audioModal.hidden = true; // click backdrop to close
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") audioModal.hidden = true;
});

/* ---------- Events ---------- */
els.fetch.addEventListener("click", fetchInfo);
els.url.addEventListener("keydown", (e) => {
  if (e.key === "Enter") fetchInfo();
});
