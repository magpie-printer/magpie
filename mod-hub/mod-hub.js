const GRID = document.querySelector("#mod-grid");
const COUNT = document.querySelector("#mod-count");
const STATUS = document.querySelector("#mod-status");
const SEARCH = document.querySelector("#mod-search");
const TEMPLATE = document.querySelector("#mod-card-template");
const BODY_DATA = document.body.dataset;
const GITHUB_REPO = BODY_DATA.githubRepo || "";
const GITHUB_BRANCH = BODY_DATA.githubBranch || "main";
const HAS_GITHUB = Boolean(GITHUB_REPO);
const GITHUB_BASE = HAS_GITHUB ? `https://github.com/${GITHUB_REPO}` : "";
const GITHUB_BLOB_BASE = HAS_GITHUB ? `${GITHUB_BASE}/blob/${GITHUB_BRANCH}/` : "";
const GITHUB_TREE_BASE = HAS_GITHUB ? `${GITHUB_BASE}/tree/${GITHUB_BRANCH}/` : "";

const repoLink = document.querySelector("#repo-link");
if (repoLink && HAS_GITHUB) {
  repoLink.href = `${GITHUB_BLOB_BASE}README.md`;
}

const STATE = {
  mods: [],
  filtered: [],
};

const MOD_JSON_PATH = "mods.json";

async function loadMods() {
  try {
    const payload = await loadPayload();
    STATE.mods = payload.mods ?? [];
    STATE.filtered = STATE.mods;
    render();
    if (payload.generated_at) {
      STATUS.textContent = `Last generated ${new Date(payload.generated_at).toLocaleString()}`;
    } else {
      STATUS.textContent = "Mod data loaded.";
    }
  } catch (err) {
    console.error("Unable to load mods.json", err);
    STATUS.textContent =
      "Unable to load mods.json. Did you run scripts/build_mod_hub.py or serve this folder via a local web server?";
  }
}

async function loadPayload() {
  const url = new URL(MOD_JSON_PATH, window.location.href);
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    if (url.protocol === "file:") {
      try {
        const module = await import("./mods.json", { assert: { type: "json" } });
        return module.default ?? module;
      } catch (importErr) {
        console.error("JSON import fallback also failed", importErr);
      }
    }
    throw err;
  }
}

function render() {
  GRID.innerHTML = "";
  STATE.filtered.forEach((mod) => GRID.appendChild(renderCard(mod)));
  COUNT.textContent = `${STATE.filtered.length} mod${STATE.filtered.length === 1 ? "" : "s"} shown`;
  if (!STATE.filtered.length) {
    GRID.innerHTML = `<p class="empty-state">No mods match that search yet.</p>`;
  }
}

const ABSOLUTE_URL = /^(?:[a-z]+:)?\/\//i;
const isLocalEnv =
  window.location.protocol === "file:" ||
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

function toAssetUrl(path) {
  if (!path) return "#";
  if (ABSOLUTE_URL.test(path)) return path;
  if (isLocalEnv) {
    return `../${path}`;
  }
  if (HAS_GITHUB) {
    return `https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/${encodePath(path)}`;
  }
  return path;
}

function encodePath(path) {
  return path
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

function githubBlob(path) {
  if (!HAS_GITHUB || !path) return toAssetUrl(path);
  return `${GITHUB_BLOB_BASE}${encodePath(path)}`;
}

function githubTree(path) {
  if (!HAS_GITHUB || !path) return toAssetUrl(path);
  return `${GITHUB_TREE_BASE}${encodePath(path)}`;
}

function renderCard(mod) {
  const clone = TEMPLATE.content.cloneNode(true);
  const card = clone.querySelector(".mod-card");
  const img = clone.querySelector("img");
  const meta = clone.querySelector(".mod-meta");
  const title = clone.querySelector("h2");
  const summary = clone.querySelector(".mod-summary");
  const primaryBtn = clone.querySelector(".mod-actions a");
  const secondaryBtn = clone.querySelector(".mod-actions a.button-secondary");

  const hero = mod.images?.[0];
  if (hero) {
    img.src = toAssetUrl(hero);
    img.alt = `${mod.name} preview`;
  } else {
    card.classList.add("mod-card--no-image");
    img.remove();
  }

  meta.textContent = mod.author ? `By ${mod.author}` : "Community contribution";
  title.textContent = mod.name;
  summary.textContent = mod.summary ?? "Documentation available inside the README.";
  primaryBtn.href = githubBlob(mod.readme);
  secondaryBtn.href = githubTree(mod.path);
  return clone;
}

function handleSearch(event) {
  const query = event.target.value.trim().toLowerCase();
  if (!query) {
    STATE.filtered = STATE.mods;
  } else {
    STATE.filtered = STATE.mods.filter((mod) => {
      return (
        (mod.name && mod.name.toLowerCase().includes(query)) ||
        (mod.summary && mod.summary.toLowerCase().includes(query)) ||
        (mod.author && mod.author.toLowerCase().includes(query))
      );
    });
  }
  render();
}

SEARCH.addEventListener("input", handleSearch);
loadMods();
