/**
 * app.js — Clean UI & DOM Logic for FB Marketplace Bot
 */

let entries = [];
let entryIdCounter = 0;
const MAX_IMAGES = 10;

// Status Badge

function setStatus(msg, type = '') {
  const badge = document.getElementById('status-badge');
  if (!badge) return;
  badge.textContent = msg || 'Ready';
  badge.className = 'status-badge ' + type;
}

// Tab Switching Logic
function switchTab(tabId) {
  document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  
  const activeTab = document.querySelector(`.nav-tab[data-tab="${tabId}"]`);
  if (activeTab) activeTab.classList.add('active');
  
  const activeContent = document.getElementById(tabId);
  if (activeContent) activeContent.classList.add('active');
}
document.addEventListener('DOMContentLoaded', () => {
  const stop_btn = document.getElementById('btn-stop');
  if (stop_btn) stop_btn.disabled = true;
  loadSessionOnStartup();
});
function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

function openLightbox(src) {
  const img = document.getElementById('lightbox-img');
  if (img && src) {
    img.src = src;
    openModal('modal-lightbox');
  }
}

function disableControls() {
  ['btn-add', 'btn-save-fields', 'btn-run', 'btn-distribute', 'btn-failed', 'btn-load-fields', 'btn-renew', 'btn-delete-relist', 'btn-save-quick']
    .forEach(id => { const el = document.getElementById(id); if (el) el.disabled = true; });
  const stop_btn = document.getElementById('btn-stop');
  if (stop_btn) stop_btn.disabled = false;
}

function enableControls() {
  ['btn-add', 'btn-save-fields', 'btn-run', 'btn-distribute', 'btn-failed', 'btn-load-fields', 'btn-renew', 'btn-delete-relist', 'btn-save-quick']
    .forEach(id => { const el = document.getElementById(id); if (el) el.disabled = false; });
  setStatus('Ready');
}

function getWaitTimeSeconds(id='') {
  const val = parseInt(document.getElementById('wait-value'+id).value) || 2;
  const unit = document.getElementById('wait-unit'+id).value;
  if (unit === 'minutes') return val * 60;
  if (unit === 'hours') return val * 3600;
  return val;
}

function getMarketplace() {
  return document.getElementById('marketplace').value;
}

function updateCount() {
  const countEl = document.getElementById('product-count');
  if (countEl) countEl.textContent = entries.length;
  const statCountEl = document.getElementById('stat-count');
  if (statCountEl) statCountEl.textContent = entries.length;
  updateEmptyState();
}

function rerenderNumbers() {
  entries.forEach((e, i) => {
    const titleEl = document.getElementById(`card-title-${e.id}`);
    if (titleEl) titleEl.textContent = `Product Listing #${i + 1}`;
  });
  updateCount();
}

function updateEmptyState() {
  const list = document.getElementById('entries-list');
  const empty = document.getElementById('empty-state');
  if (entries.length === 0) {
    list.style.display = 'none';
    empty.style.display = 'flex';
  } else {
    list.style.display = 'flex';
    empty.style.display = 'none';
  }
}

function getPreviewUrl(src) {
  if (!src) return '';
  const clean = src.trim();
  if (clean.startsWith('http://') || clean.startsWith('https://') || clean.startsWith('data:')) {
    return clean;
  }
  const baseUrl = (typeof BASE_URL !== 'undefined') ? BASE_URL : window.location.origin;
  return `${baseUrl}/media-preview?path=${encodeURIComponent(clean)}`;
}

// Image Preview & Row Creation
function updateImagePreview(entryId, imgIndex, src) {
  const thumb = document.getElementById(`img-thumb-${entryId}-${imgIndex}`);
  if (!thumb) return;

  if (src && src.trim()) {
    const previewUrl = getPreviewUrl(src);
    thumb.src = previewUrl;
    thumb.style.display = 'block';
    thumb.onclick = () => openLightbox(previewUrl);
  } else {
    thumb.style.display = 'none';
    thumb.src = '';
    thumb.onclick = null;
  }
}

function buildImageRow(entryId, imgIndex) {
  const row = document.createElement('div');
  row.className = 'image-row';
  row.id = `img-row-${entryId}-${imgIndex}`;

  const thumb = document.createElement('img');
  thumb.className = 'img-preview-thumb';
  thumb.id = `img-thumb-${entryId}-${imgIndex}`;
  thumb.style.display = 'none';

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'input';
  input.placeholder = `Full image path (e.g. /home/shaeel/image.png)…`;
  input.id = `img-input-${entryId}-${imgIndex}`;
  input.oninput = () => updateImagePreview(entryId, imgIndex, input.value);

  const browseBtn = document.createElement('button');
  browseBtn.className = 'btn btn-secondary';
  browseBtn.textContent = 'Browse';
  browseBtn.onclick = () => triggerImageBrowse(entryId, imgIndex);

  const dropZone = document.createElement('div');
  dropZone.className = 'drop-zone';
  dropZone.textContent = '📂 Drop';
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => handleImageDrop(e, entryId, imgIndex));

  row.appendChild(thumb);
  row.appendChild(input);
  row.appendChild(browseBtn);
  row.appendChild(dropZone);

  if (imgIndex > 0) {
    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-ghost';
    removeBtn.textContent = '✕';
    removeBtn.onclick = () => removeImageRow(entryId, imgIndex);
    row.appendChild(removeBtn);
  }
  return row;
}

function addImageRow(entryId) {
  const entry = entries.find(e => e.id === entryId);
  if (!entry) return;
  if (entry.imageCount >= MAX_IMAGES) { alert(`Max ${MAX_IMAGES} images.`); return; }
  const idx = entry.imageCount;
  entry.imageCount++;
  const container = document.getElementById(`images-container-${entryId}`);
  container.appendChild(buildImageRow(entryId, idx));
}

function removeImageRow(entryId, imgIndex) {
  const row = document.getElementById(`img-row-${entryId}-${imgIndex}`);
  if (row) row.remove();
  const entry = entries.find(e => e.id === entryId);
  if (entry) entry.imageCount = Math.max(1, entry.imageCount - 1);
}

function handleImageDrop(e, entryId, imgIndex) {
  e.preventDefault();
  const zone = e.currentTarget;
  zone.classList.remove('drag-over');
  const files = e.dataTransfer.files || [];
  if (files.length > 0) {
    const file = files[0];
    const fullPath = file.path || file.name;
    const input = document.getElementById(`img-input-${entryId}-${imgIndex}`);
    if (input) {
      input.value = fullPath;
      updateImagePreview(entryId, imgIndex, fullPath);
    }
  }
}

// Native File Selector Trigger for Product Cards
async function triggerImageBrowse(entryId, imgIndex) {
  try {
    const paths = await browseNativeFiles();
    if (!paths || paths.length === 0) return;

    const firstInput = document.getElementById(`img-input-${entryId}-${imgIndex}`);
    if (firstInput) {
      firstInput.value = paths[0];
      updateImagePreview(entryId, imgIndex, paths[0]);
    }

    const entry = entries.find(e => e.id === entryId);
    for (let i = 1; i < paths.length && entry && entry.imageCount < MAX_IMAGES; i++) {
      addImageRow(entryId);
      const newIdx = entry.imageCount - 1;
      const input = document.getElementById(`img-input-${entryId}-${newIdx}`);
      if (input) {
        input.value = paths[i];
        updateImagePreview(entryId, newIdx, paths[i]);
      }
    }
  } catch (err) {
    console.error('File browse error:', err);
  }
}

async function triggerVideoBrowse(entryId) {
  try {
    const path = await browseNativeVideo();
    if (path) {
      document.getElementById(`video-input-${entryId}`).value = path;
    }
  } catch (err) {
    console.error('Video browse error:', err);
  }
}

// Native File Selector Trigger for Quick Field Modal
async function triggerQuickImageBrowse() {
  try {
    const paths = await browseNativeFiles();
    if (!paths || paths.length === 0) return;

    const txtArea = document.getElementById('quick-images');
    if (txtArea) {
      const cur = txtArea.value.trim();
      const newStr = paths.join(', ');
      txtArea.value = cur ? cur + '\n' + newStr : newStr;
    }
  } catch (err) {
    console.error('Quick image browse error:', err);
  }
}

async function triggerQuickVideoBrowse() {
  try {
    const path = await browseNativeVideo();
    if (!path) return;

    const txtArea = document.getElementById('quick-videos');
    if (txtArea) {
      const cur = txtArea.value.trim();
      txtArea.value = cur ? cur + '\n' + path : path;
    }
  } catch (err) {
    console.error('Quick video browse error:', err);
  }
}

// ── Default Helpers ──────────────────────────────────────────────────────────
function getDefaults() {
  const min = parseInt(document.getElementById('default-price-min')?.value) || 80;
  const max = parseInt(document.getElementById('default-price-max')?.value) || 100;
  const randomPrice = Math.floor(Math.random() * (max - min + 1)) + min;

  return {
    category: document.getElementById('default-category')?.value || 'Furniture',
    condition: document.getElementById('default-condition')?.value || 'New',
    availability: document.getElementById('default-availability')?.value || 'List as In Stock',
    price: String(randomPrice),
    meetup: document.getElementById('default-meetup')?.checked || false,
    pickup: document.getElementById('default-pickup')?.checked || false,
    dropoff: document.getElementById('default-dropoff')?.checked || false,
  };
}

function getRandomLocation() {
  const poolEl = document.getElementById('location-pool');
  if (!poolEl || !poolEl.value.trim()) return '';
  const locs = poolEl.value.split('|').map(s => s.trim()).filter(Boolean);
  if (locs.length === 0) return '';
  return locs[Math.floor(Math.random() * locs.length)];
}

// Add Product Card
function addField() {
  const id = ++entryIdCounter;
  entries.push({ id, imageCount: 1 });
  const defaults = getDefaults();

  const card = document.createElement('div');
  card.className = 'product-card';
  card.id = `card-${id}`;

  card.innerHTML = `
    <div class="card-header">
      <h3 id="card-title-${id}">Product Listing #${entries.length}</h3>
      <button class="btn btn-danger" style="padding:4px 10px;font-size:12px;" onclick="removeField(${id})">❌ Remove</button>
    </div>
    <div class="card-body">

      <!-- Media Section -->
      <div class="media-section">
        <div class="form-group">
          <label>Product Images (Up to ${MAX_IMAGES})</label>
          <div class="image-entries" id="images-container-${id}"></div>
          <button class="btn btn-secondary" style="margin-top:8px;font-size:12px;" onclick="addImageRow(${id})">➕ Add Image</button>
        </div>

        <div class="form-group">
          <label>Product Video (Optional)</label>
          <div class="image-row">
            <input id="video-input-${id}" class="input" type="text" placeholder="Full video path (e.g. /home/shaeel/video.mp4)…" />
            <button class="btn btn-secondary" onclick="triggerVideoBrowse(${id})">Browse</button>
            <div class="drop-zone" id="video-drop-${id}"
                 ondragover="event.preventDefault();this.classList.add('drag-over')"
                 ondragleave="this.classList.remove('drag-over')"
                 ondrop="handleVideoDrop(event,${id})">📂 Drop Video</div>
          </div>
        </div>
      </div>

      <!-- Fields Grid -->
      <div class="fields-grid-3">
        <div class="form-group">
          <label>Title</label>
          <input id="title-${id}" class="input" type="text" placeholder="Item title..." />
        </div>
        <div class="form-group">
          <label>Category</label>
          <input id="category-${id}" class="input" type="text" value="${defaults.category}" />
        </div>
        <div class="form-group">
          <label>Price</label>
          <input id="price-${id}" class="input" type="number" min="0" value="${defaults.price}" />
        </div>
        <div class="form-group">
          <label>Location <span style="font-size:10px;color:var(--text-muted);">(blank = use pool)</span></label>
          <input id="location-${id}" class="input" type="text" placeholder="Leave blank for random from pool" />
        </div>
        <div class="form-group">
          <label>Condition</label>
          <select id="condition-${id}" class="input">
            <option value="New" ${defaults.condition === 'New' ? 'selected' : ''}>New</option>
            <option value="Used - Like New" ${defaults.condition === 'Used - Like New' ? 'selected' : ''}>Used - Like New</option>
            <option value="Used - Good" ${defaults.condition === 'Used - Good' ? 'selected' : ''}>Used - Good</option>
            <option value="Used - Fair" ${defaults.condition === 'Used - Fair' ? 'selected' : ''}>Used - Fair</option>
          </select>
        </div>
        <div class="form-group">
          <label>Availability</label>
          <select id="availability-${id}" class="input">
            <option value="List as In Stock" ${defaults.availability === 'List as In Stock' ? 'selected' : ''}>List as In Stock</option>
            <option value="List as Single Item" ${defaults.availability === 'List as Single Item' ? 'selected' : ''}>List as Single Item</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label>Tags (Comma-separated)</label>
        <input id="tags-${id}" class="input" type="text" placeholder="furniture, sofa, home" />
      </div>

      <div class="form-group">
        <label>Description</label>
        <textarea id="desc-${id}" class="input" rows="3" placeholder="Full product description..."></textarea>
      </div>

      <!-- Options -->
      <div class="form-group">
        <label>Delivery & Pickup Options</label>
        <div class="checkbox-row">
          <label class="checkbox-item">
            <input type="checkbox" id="meetup-${id}" ${defaults.meetup ? 'checked' : ''} /> Public meetup
          </label>
          <label class="checkbox-item">
            <input type="checkbox" id="pickup-${id}" ${defaults.pickup ? 'checked' : ''} /> Door pickup
          </label>
          <label class="checkbox-item">
            <input type="checkbox" id="dropoff-${id}" ${defaults.dropoff ? 'checked' : ''} /> Door dropoff
          </label>
        </div>
      </div>

    </div>
  `;

  document.getElementById('entries-list').appendChild(card);
  const container = document.getElementById(`images-container-${id}`);
  container.appendChild(buildImageRow(id, 0));

  updateCount();
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  triggerAutoSave();
}

function removeField(id) {
  entries = entries.filter(e => e.id !== id);
  const card = document.getElementById(`card-${id}`);
  if (card) card.remove();
  rerenderNumbers();
  triggerAutoSave();
}

function handleVideoDrop(e, entryId) {
  e.preventDefault();
  document.getElementById(`video-drop-${entryId}`).classList.remove('drag-over');
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    const fullPath = files[0].path || files[0].name;
    document.getElementById(`video-input-${entryId}`).value = fullPath;
  }
}

// Quick Field Modal
function openSaveQuicklyModal() {
  openModal('modal-quick-save');
}

function parseQuickFields() {
  const parseLines = (id) => (document.getElementById(id)?.value || '').split('\n').map(l => l.trim()).filter(Boolean);

  const titles = parseLines('quick-titles');
  const categories = parseLines('quick-categories');
  const prices = parseLines('quick-prices');
  const locations = parseLines('quick-locations');
  const conditions = parseLines('quick-conditions');
  const availabilities = parseLines('quick-availabilities');
  const tagsList = parseLines('quick-tags');
  const imagesList = parseLines('quick-images');
  const videosList = parseLines('quick-videos');

  const rawDesc = document.getElementById('quick-descriptions')?.value || '';
  const descriptions = rawDesc.split('|||').map(d => d.trim()).filter(Boolean);

  const count = Math.max(
    titles.length, categories.length, prices.length,
    locations.length, conditions.length, availabilities.length,
    tagsList.length, imagesList.length, videosList.length, descriptions.length
  );

  if (count === 0) {
    alert('Please enter data into at least one field.');
    return null;
  }

  const result = [];
  for (let i = 0; i < count; i++) {
    const rawImgs = imagesList[i] || '';
    const parsedImgs = rawImgs.split(',').map(s => s.trim()).filter(Boolean);

    result.push({
      images: parsedImgs,
      video: videosList[i] || '',
      title: titles[i] || '',
      category: categories[i] || '',
      price: prices[i] || '0',
      location: locations[i] || '',
      condition: conditions[i] || '',
      availability: availabilities[i] || '',
      tags: (tagsList[i] || '').split(',').map(t => t.trim()).filter(Boolean),
      description: descriptions[i] || '',
      public_meetup: 0,
      door_pickup: 0,
      door_dropoff: 0,
    });
  }
  return result;
}

function applyQuickFieldsToUI() {
  const fields = parseQuickFields();
  if (!fields) return;

  fields.forEach(f => {
    addField();
    const entry = entries[entries.length - 1];
    const id = entry.id;

    if (f.images && f.images.length > 0) {
      const firstInput = document.getElementById(`img-input-${id}-0`);
      if (firstInput) {
        firstInput.value = f.images[0];
        updateImagePreview(id, 0, f.images[0]);
      }
      for (let i = 1; i < f.images.length && i < MAX_IMAGES; i++) {
        addImageRow(id);
        const input = document.getElementById(`img-input-${id}-${i}`);
        if (input) {
          input.value = f.images[i];
          updateImagePreview(id, i, f.images[i]);
        }
      }
    }

    const set = (fieldId, val) => {
      const el = document.getElementById(fieldId);
      if (el) el.value = val ?? '';
    };
    set(`title-${id}`, f.title);
    set(`category-${id}`, f.category);
    set(`price-${id}`, f.price);
    set(`location-${id}`, f.location);
    set(`condition-${id}`, f.condition);
    set(`availability-${id}`, f.availability);
    set(`tags-${id}`, (f.tags || []).join(', '));
    set(`desc-${id}`, f.description);
    set(`video-input-${id}`, f.video);
  });

  closeModal('modal-quick-save');
  setStatus(`Generated ${fields.length} listings from text`, 'success');
}

// Collect Data
function collectEntryData(entry) {
  const id = entry.id;
  const images = [];
  for (let i = 0; i < entry.imageCount; i++) {
    const el = document.getElementById(`img-input-${id}-${i}`);
    if (el && el.value.trim()) images.push(el.value.trim());
  }

  // Use individual location if set, otherwise pick randomly from pool
  let location = document.getElementById(`location-${id}`)?.value.trim() || '';
  if (!location) {
    location = getRandomLocation();
  }

  return {
    images,
    title: document.getElementById(`title-${id}`)?.value.trim() || '',
    description: document.getElementById(`desc-${id}`)?.value.trim() || '',
    category: document.getElementById(`category-${id}`)?.value.trim() || '',
    location,
    tags: (document.getElementById(`tags-${id}`)?.value.trim() || '').split(',').map(t => t.trim()).filter(Boolean),
    price: document.getElementById(`price-${id}`)?.value.trim() || '0',
    condition: document.getElementById(`condition-${id}`)?.value.trim() || '',
    availability: document.getElementById(`availability-${id}`)?.value.trim() || '',
    video: document.getElementById(`video-input-${id}`)?.value.trim() || '',
    public_meetup: document.getElementById(`meetup-${id}`)?.checked ? 1 : 0,
    door_pickup: document.getElementById(`pickup-${id}`)?.checked ? 1 : 0,
    door_dropoff: document.getElementById(`dropoff-${id}`)?.checked ? 1 : 0,
  };
}

function validate() {
  if (entries.length === 0) { alert('Please add at least one product listing.'); return false; }
  const poolHasLocations = (document.getElementById('location-pool')?.value || '').split('|').map(s => s.trim()).filter(Boolean).length > 0;

  for (let i = 0; i < entries.length; i++) {
    const d = collectEntryData(entries[i]);
    const n = i + 1;
    if (d.images.length === 0) { alert(`Product #${n}: At least one image is required.`); return false; }
    if (!d.title) { alert(`Product #${n}: Title is required.`); return false; }
    if (!d.description) { alert(`Product #${n}: Description is required.`); return false; }
    if (!d.category) { alert(`Product #${n}: Category is required.`); return false; }
    if (!d.location && !poolHasLocations) { alert(`Product #${n}: Location is required (or add locations to the Location Pool).`); return false; }
    if (d.tags.length === 0) { alert(`Product #${n}: At least one tag is required.`); return false; }
    if (!d.price) { alert(`Product #${n}: Price is required.`); return false; }
    if (!d.condition) { alert(`Product #${n}: Condition is required.`); return false; }
    if (!d.availability) { alert(`Product #${n}: Availability is required.`); return false; }
  }
  return true;
}
async function getFailedFields() {
  try {
    const values=await getFailedFieldsValue()
    console.log('Failed fields values:', values);
    generateFailedUI(values.failed_fields);
  }catch(err){
    alert(`Failed to get failed fields: ${err.message}`);
  }
}
function onBotComplete(failedVideos) {
  enableControls();
  const hasFailures = Object.values(failedVideos).some(arr => arr && arr.length > 0);
  if (!hasFailures) {
    setStatus('Finished Successfully', 'success');
    return;
  }
  showFailedModal(failedVideos);
}

function showFailedModal(failedVideos) {
  const container = document.getElementById('failed-list-content');
  container.innerHTML = '';
  for (const [key, items] of Object.entries(failedVideos)) {
    if (!items || items.length === 0) continue;
    const g = document.createElement('div');
    g.style.fontWeight = 'bold';
    g.textContent = key + ':';
    container.appendChild(g);
    items.forEach(item => {
      const d = document.createElement('div');
      d.style.color = 'var(--text-muted)';
      d.style.paddingLeft = '12px';
      d.textContent = item;
      container.appendChild(d);
    });
  }
  openModal('modal-failed');
}

function saveAllFields() {
  openModal('modal-save');
}

// ── Account Manager UI ───────────────────────────────────────────────────────
async function loadAccountsModal() {
  try {
    const res = await fetchAccounts();
    const accounts = res.accounts || [];
    const container = document.getElementById('accounts-list-container');
    if (!container) return;
    container.innerHTML = '';

    if (accounts.length === 0) {
      container.innerHTML = '<div style="color:var(--text-muted);padding:8px;">No accounts saved yet.</div>';
    } else {
      accounts.forEach(acc => {
        const item = document.createElement('div');
        item.className = 'saved-item';
        item.style.display = 'flex';
        item.style.justifyContent = 'space-between';
        item.style.alignItems = 'center';
        item.style.padding = '10px 14px';
        item.style.marginBottom = '8px';
        item.style.borderRadius = '6px';
        item.style.background = 'var(--bg-card, #252526)';

        const statusBadge = acc.authenticated
          ? '<span style="color:#4caf50;font-weight:bold;margin-left:6px;">🟢 Authenticated</span>'
          : '<span style="color:#f44336;font-weight:bold;margin-left:6px;">🔴 Not Initialized</span>';

        const info = document.createElement('div');
        info.innerHTML = `<div><strong>${acc.email}</strong> ${statusBadge}</div>
                          <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">
                            ${acc.phone ? '📞 ' + acc.phone + ' ' : ''} ${acc.proxy ? '🌐 Proxy: ' + acc.proxy : ''}
                          </div>`;

        const btnGroup = document.createElement('div');
        btnGroup.style.display = 'flex';
        btnGroup.style.gap = '6px';

        const autoLoginBtn = document.createElement('button');
        autoLoginBtn.className = 'btn btn-primary';
        autoLoginBtn.style.padding = '4px 10px';
        autoLoginBtn.style.fontSize = '12px';
        autoLoginBtn.textContent = '🚀 Auto-Login & Setup';
        autoLoginBtn.onclick = () => autoLoginFromUI(acc.email, acc.password, acc.proxy);

        const delBtn = document.createElement('button');
        delBtn.className = 'btn btn-danger';
        delBtn.style.padding = '4px 10px';
        delBtn.style.fontSize = '12px';
        delBtn.textContent = '🗑️ Delete';
        delBtn.onclick = () => deleteAccountFromUI(acc.email);

        btnGroup.appendChild(autoLoginBtn);
        btnGroup.appendChild(delBtn);

        item.appendChild(info);
        item.appendChild(btnGroup);
        container.appendChild(item);
      });
    }
    openModal('modal-accounts');
  } catch (err) {
    alert(`Failed loading accounts: ${err.message}`);
  }
}

async function saveAccountFromUI() {
  const email = (document.getElementById('acc-email-input')?.value || '').trim();
  const password = (document.getElementById('acc-pass-input')?.value || '').trim();
  const phone = (document.getElementById('acc-phone-input')?.value || '').trim();
  const proxy = (document.getElementById('acc-proxy-input')?.value || '').trim();

  if (!email) { alert('Email is required.'); return; }
  try {
    await saveAccountAPI(email, phone, password, proxy);
    document.getElementById('acc-email-input').value = '';
    if (document.getElementById('acc-pass-input')) document.getElementById('acc-pass-input').value = '';
    document.getElementById('acc-phone-input').value = '';
    document.getElementById('acc-proxy-input').value = '';
    loadAccountsModal();
  } catch (err) {
    alert(`Save account failed: ${err.message}`);
  }
}

async function autoLoginFromUI(email, password, proxy) {
  try {
    setStatus(`Auto-logging in for ${email}...`, 'active');
    await triggerAutoLoginAPI(email, password, proxy);
    alert(`Auto-login session started for ${email}.\nChrome will open and detect your Facebook login automatically.`);
    
    // Poll accounts list every 3s to update badge when logged in
    const interval = setInterval(async () => {
      try {
        const res = await fetchAccounts();
        const target = (res.accounts || []).find(a => a.email === email);
        if (target && target.authenticated) {
          clearInterval(interval);
          setStatus(`Account ${email} Authenticated!`, 'success');
          loadAccountsModal();
        }
      } catch (e) {}
    }, 3000);
    setTimeout(() => clearInterval(interval), 120000);
  } catch (err) {
    alert(`Auto login failed: ${err.message}`);
  }
}

async function deleteAccountFromUI(email) {
  if (!confirm(`Delete account profile '${email}'?`)) return;
  try {
    await deleteAccountAPI(email);
    loadAccountsModal();
  } catch (err) {
    alert(`Delete account failed: ${err.message}`);
  }
}

// ── Session State Persistence (Auto-Save & Restore) ──────────────────────────

let autoSaveTimer = null;

function getFullSessionData() {
  return {
    settings: {
      marketplace: document.getElementById('marketplace')?.value || 'UK',
      waitTime: document.getElementById('wait-value')?.value || '2',
      waitUnit: document.getElementById('wait-unit')?.value || 'seconds',
      waitTimeAccount: document.getElementById('wait-value-account')?.value || '2',
      waitUnitAccount: document.getElementById('wait-unit-account')?.value || 'seconds',
    },
    defaults: {
      category: document.getElementById('default-category')?.value || 'Furniture',
      condition: document.getElementById('default-condition')?.value || 'New',
      availability: document.getElementById('default-availability')?.value || 'List as In Stock',
      priceMin: document.getElementById('default-price-min')?.value || '80',
      priceMax: document.getElementById('default-price-max')?.value || '100',
      meetup: !!document.getElementById('default-meetup')?.checked,
      pickup: !!document.getElementById('default-pickup')?.checked,
      dropoff: !!document.getElementById('default-dropoff')?.checked,
    },
    locationPool: document.getElementById('location-pool')?.value || '',
    entries: entries.map(collectEntryData),
    savedAt: new Date().toISOString()
  };
}

async function saveFullSession(isManual = false) {
  const sessionData = getFullSessionData();
  const jsonStr = JSON.stringify(sessionData);

  // 1. Save to browser localStorage
  try {
    localStorage.setItem('fb_bot_session_state', jsonStr);
  } catch (e) {
    console.warn('LocalStorage save failed:', e);
  }

  // 2. Save to backend disk backup
  try {
    if (typeof apiPost === 'function') {
      await apiPost('/save-session', { state: sessionData });
    }
  } catch (e) {
    console.warn('Server session backup failed:', e);
  }

  // 3. UI feedback
  const indicator = document.getElementById('save-indicator');
  if (indicator) {
    indicator.textContent = `Saved (${sessionData.entries.length} listings)`;
    indicator.style.color = '#4caf50';
    indicator.style.opacity = '1';
    setTimeout(() => {
      if (indicator) indicator.style.color = 'var(--text-muted)';
    }, 2500);
  }

  if (isManual) {
    setStatus(`Session Saved (${sessionData.entries.length} listings + Settings)`, 'success');
  }
}

function triggerAutoSave() {
  const indicator = document.getElementById('save-indicator');
  if (indicator) {
    indicator.textContent = 'Saving...';
    indicator.style.color = '#ff9800';
    indicator.style.opacity = '1';
  }
  clearTimeout(autoSaveTimer);
  autoSaveTimer = setTimeout(() => {
    saveFullSession(false);
  }, 1000);
}

function restoreFullSession(data) {
  if (!data) return false;

  try {
    // 1. Settings
    if (data.settings) {
      const set = (id, val) => { const el = document.getElementById(id); if (el && val !== undefined) el.value = val; };
      set('marketplace', data.settings.marketplace);
      set('wait-value', data.settings.waitTime);
      set('wait-unit', data.settings.waitUnit);
      set('wait-value-account', data.settings.waitTimeAccount);
      set('wait-unit-account', data.settings.waitUnitAccount);
    }

    // 2. Defaults
    if (data.defaults) {
      const set = (id, val) => { const el = document.getElementById(id); if (el && val !== undefined) el.value = val; };
      set('default-category', data.defaults.category);
      set('default-condition', data.defaults.condition);
      set('default-availability', data.defaults.availability);
      set('default-price-min', data.defaults.priceMin);
      set('default-price-max', data.defaults.priceMax);
      if (document.getElementById('default-meetup')) document.getElementById('default-meetup').checked = !!data.defaults.meetup;
      if (document.getElementById('default-pickup')) document.getElementById('default-pickup').checked = !!data.defaults.pickup;
      if (document.getElementById('default-dropoff')) document.getElementById('default-dropoff').checked = !!data.defaults.dropoff;
    }

    // 3. Location Pool
    if (data.locationPool !== undefined && document.getElementById('location-pool')) {
      document.getElementById('location-pool').value = data.locationPool;
    }

    // 4. Product Listings Cards
    if (Array.isArray(data.entries) && data.entries.length > 0) {
      entries = [];
      const listContainer = document.getElementById('entries-list');
      if (listContainer) listContainer.innerHTML = '';
      updateEmptyState();

      data.entries.forEach(f => {
        addField();
        const entry = entries[entries.length - 1];
        const id = entry.id;

        // Images
        if (f.images && f.images.length > 0) {
          const firstInput = document.getElementById(`img-input-${id}-0`);
          if (firstInput) {
            firstInput.value = f.images[0] || '';
            updateImagePreview(id, 0, f.images[0]);
          }
          for (let i = 1; i < f.images.length && i < MAX_IMAGES; i++) {
            addImageRow(id);
            const input = document.getElementById(`img-input-${id}-${i}`);
            if (input) {
              input.value = f.images[i];
              updateImagePreview(id, i, f.images[i]);
            }
          }
        }

        const set = (fieldId, val) => {
          const el = document.getElementById(fieldId);
          if (el) el.value = val ?? '';
        };

        set(`title-${id}`,        f.title);
        set(`desc-${id}`,         f.description || f.desc);
        set(`category-${id}`,     f.category);
        set(`location-${id}`,     f.location);
        set(`tags-${id}`,         Array.isArray(f.tags) ? f.tags.join(', ') : (f.tags || ''));
        set(`price-${id}`,        f.price);
        set(`condition-${id}`,    f.condition);
        set(`availability-${id}`, f.availability);
        set(`video-input-${id}`,  f.video);
        if (document.getElementById(`meetup-${id}`))  document.getElementById(`meetup-${id}`).checked  = !!f.public_meetup;
        if (document.getElementById(`pickup-${id}`))  document.getElementById(`pickup-${id}`).checked  = !!f.door_pickup;
        if (document.getElementById(`dropoff-${id}`)) document.getElementById(`dropoff-${id}`).checked = !!f.door_dropoff;
      });
    }

    const indicator = document.getElementById('save-indicator');
    if (indicator) {
      indicator.textContent = `Restored (${data.entries ? data.entries.length : 0} listings)`;
      indicator.style.color = '#4caf50';
    }
    return true;
  } catch (e) {
    console.error('Failed to restore session:', e);
    return false;
  }
}

async function loadSessionOnStartup() {
  let restored = false;

  // 1. Try local storage first
  try {
    const raw = localStorage.getItem('fb_bot_session_state');
    if (raw) {
      const data = JSON.parse(raw);
      restored = restoreFullSession(data);
    }
  } catch (e) {
    console.warn('LocalStorage load failed:', e);
  }

  // 2. If localStorage had nothing, try server backup disk state
  if (!restored) {
    try {
      if (typeof apiGet === 'function') {
        const res = await apiGet('/load-session');
        if (res && res.state) {
          restoreFullSession(res.state);
        }
      }
    } catch (e) {
      console.warn('Server session load failed:', e);
    }
  }

  // 3. Attach auto-save listeners across inputs
  document.addEventListener('input', (e) => {
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT')) {
      triggerAutoSave();
    }
  });

  document.addEventListener('change', (e) => {
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT')) {
      triggerAutoSave();
    }
  });
}

// ── CSV & Excel Import Handlers ─────────────────────────────────────────────
function triggerCSVImportDialog() {
  const input = document.getElementById('csv-file-input');
  if (input) { input.value = ''; input.click(); }
}

async function handleCSVFileSelected(event) {
  const files = event.target.files;
  if (!files || files.length === 0) return;
  const file = files[0];
  try {
    setStatus(`Importing ${file.name}...`, 'active');
    const res = await importCSVAPI(file);
    if (!res.fields || res.fields.length === 0) {
      alert('No valid product listings found in CSV.');
      setStatus('Ready');
      return;
    }

    res.fields.forEach(f => {
      addField();
      const entry = entries[entries.length - 1];
      const id = entry.id;

      if (f.images && f.images.length > 0) {
        const firstInput = document.getElementById(`img-input-${id}-0`);
        if (firstInput) {
          firstInput.value = f.images[0] || '';
          updateImagePreview(id, 0, f.images[0]);
        }
        for (let i = 1; i < f.images.length && i < MAX_IMAGES; i++) {
          addImageRow(id);
          const input = document.getElementById(`img-input-${id}-${i}`);
          if (input) {
            input.value = f.images[i];
            updateImagePreview(id, i, f.images[i]);
          }
        }
      }

      const set = (fieldId, val) => { const el = document.getElementById(fieldId); if (el) el.value = val ?? ''; };
      set(`title-${id}`,        f.title);
      set(`desc-${id}`,         f.description);
      set(`category-${id}`,     f.category);
      set(`location-${id}`,     f.location);
      set(`tags-${id}`,         Array.isArray(f.tags) ? f.tags.join(', ') : (f.tags || ''));
      set(`price-${id}`,        f.price);
      set(`condition-${id}`,    f.condition);
      set(`availability-${id}`, f.availability);
      set(`video-input-${id}`,  f.video);
      if (document.getElementById(`meetup-${id}`))  document.getElementById(`meetup-${id}`).checked  = !!f.public_meetup;
      if (document.getElementById(`pickup-${id}`))  document.getElementById(`pickup-${id}`).checked  = !!f.door_pickup;
      if (document.getElementById(`dropoff-${id}`)) document.getElementById(`dropoff-${id}`).checked = !!f.door_dropoff;
    });

    triggerAutoSave();
    setStatus(`Imported ${res.fields.length} listings from ${file.name}`, 'success');
  } catch (err) {
    alert(`CSV Import Failed: ${err.message}`);
    setStatus('Ready');
  }
}

// ── Folder Auto-Generator Handlers ──────────────────────────────────────────
function openFolderGeneratorModal() {
  openModal('modal-folder-gen');
}

async function browseFolderGenPath() {
  try {
    const paths = await browseNativeFiles();
    if (paths && paths.length > 0) {
      const p = paths[0];
      const dir = p.substring(0, Math.max(p.lastIndexOf('/'), p.lastIndexOf('\\')));
      if (dir) document.getElementById('folder-gen-path').value = dir;
    }
  } catch (e) {}
}

async function runFolderGenerator() {
  const path = (document.getElementById('folder-gen-path')?.value || '').trim();
  if (!path) { alert('Please enter a folder path.'); return; }
  try {
    setStatus(`Scanning folder ${path}...`, 'active');
    const res = await scanFolderAPI(path);
    closeModal('modal-folder-gen');

    if (!res.fields || res.fields.length === 0) {
      alert('No photo folders found in directory.');
      setStatus('Ready');
      return;
    }

    res.fields.forEach(f => {
      addField();
      const entry = entries[entries.length - 1];
      const id = entry.id;

      if (f.images && f.images.length > 0) {
        const firstInput = document.getElementById(`img-input-${id}-0`);
        if (firstInput) {
          firstInput.value = f.images[0] || '';
          updateImagePreview(id, 0, f.images[0]);
        }
        for (let i = 1; i < f.images.length && i < MAX_IMAGES; i++) {
          addImageRow(id);
          const input = document.getElementById(`img-input-${id}-${i}`);
          if (input) {
            input.value = f.images[i];
            updateImagePreview(id, i, f.images[i]);
          }
        }
      }

      const set = (fieldId, val) => { const el = document.getElementById(fieldId); if (el) el.value = val ?? ''; };
      set(`title-${id}`,        f.title);
      set(`desc-${id}`,         f.description);
      set(`category-${id}`,     f.category);
      set(`location-${id}`,     f.location);
      set(`tags-${id}`,         Array.isArray(f.tags) ? f.tags.join(', ') : (f.tags || ''));
      set(`price-${id}`,        f.price);
      set(`condition-${id}`,    f.condition);
      set(`availability-${id}`, f.availability);
    });

    triggerAutoSave();
    setStatus(`Generated ${res.fields.length} product listings from folder`, 'success');
  } catch (err) {
    alert(`Folder Generation Failed: ${err.message}`);
    setStatus('Ready');
  }
}

// ── Global Batch Editor Handlers ────────────────────────────────────────────
function openBatchEditModal() {
  if (entries.length === 0) { alert('No active product cards to edit.'); return; }
  openModal('modal-batch-edit');
}

function applyBatchEditsToCards() {
  const cat = (document.getElementById('batch-category')?.value || '').trim();
  const cond = document.getElementById('batch-condition')?.value || '';
  const priceType = document.getElementById('batch-price-type')?.value || 'set';
  const priceVal = parseFloat(document.getElementById('batch-price-val')?.value);
  const footer = (document.getElementById('batch-desc-footer')?.value || '').trim();

  let modifiedCount = 0;
  entries.forEach(entry => {
    const id = entry.id;
    if (cat) {
      const el = document.getElementById(`category-${id}`);
      if (el) el.value = cat;
    }
    if (cond) {
      const el = document.getElementById(`condition-${id}`);
      if (el) el.value = cond;
    }
    if (!isNaN(priceVal)) {
      const pEl = document.getElementById(`price-${id}`);
      if (pEl) {
        let cur = parseFloat(pEl.value) || 0;
        if (priceType === 'set') cur = priceVal;
        else if (priceType === 'add') cur += priceVal;
        else if (priceType === 'sub') cur = Math.max(0, cur - priceVal);
        pEl.value = Math.round(cur);
      }
    }
    if (footer) {
      const dEl = document.getElementById(`desc-${id}`);
      if (dEl) {
        const cur = dEl.value.trim();
        dEl.value = cur ? `${cur}\n\n${footer}` : footer;
      }
    }
    modifiedCount++;
  });

  closeModal('modal-batch-edit');
  triggerAutoSave();
  setStatus(`Updated ${modifiedCount} cards with batch edits`, 'success');
}

// ── Policy Compliance Guard Check ───────────────────────────────────────────
const PROHIBITED_KEYWORDS = [
  "replica", "fake", "first copy", "counterfeit", "master copy",
  "weapon", "gun", "tobacco", "vape", "cbd", "prescription", "stolen"
];

function runPolicyGuardCheck() {
  if (entries.length === 0) { alert('Add at least one product card to run Policy Guard.'); return; }
  let warnings = [];
  entries.forEach((e, idx) => {
    const data = collectEntryData(e);
    const num = idx + 1;
    const fullText = `${data.title} ${data.description}`.toLowerCase();
    const foundKeywords = PROHIBITED_KEYWORDS.filter(k => fullText.includes(k));
    if (foundKeywords.length > 0) {
      warnings.push(`Listing #${num} ("${data.title}") contains prohibited keywords: ${foundKeywords.join(', ')}`);
    }
    const priceVal = parseFloat(data.price);
    if (priceVal === 0 || priceVal === 1) {
      warnings.push(`Listing #${num} ("${data.title}") uses suspicious $${priceVal} bait pricing.`);
    }
  });

  if (warnings.length === 0) {
    alert('🛡️ Policy Guard Scan Passed!\n\nAll listings follow Facebook Marketplace content guidelines.');
    setStatus('Policy Guard: 100% Passed', 'success');
  } else {
    alert(`⚠️ Policy Guard Warnings Found (${warnings.length}):\n\n` + warnings.join('\n\n') + '\n\nPlease resolve these issues before running the bot to prevent account flags.');
    setStatus(`Policy Warning: ${warnings.length} issues`, 'warning');
  }
}

// Initial setup
updateEmptyState();
