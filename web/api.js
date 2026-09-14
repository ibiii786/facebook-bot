/**
 * api.js — Dedicated API Client module for FB Marketplace Bot
 * Handles all network requests to the FastAPI backend endpoints.
 */

const BASE_URL = (typeof window !== 'undefined' && window.location && window.location.origin && window.location.origin !== 'null')
  ? window.location.origin
  : 'http://127.0.0.1:8000';

// Low-level HTTP fetch wrappers
async function apiPost(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  return res.json();
}

async function apiGet(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  return res.json();
}

// Native OS File Browser Calls
async function browseNativeFiles() {
  try {
    const res = await apiGet('/browse-files');
    return res.paths || [];
  } catch (err) {
    console.error('browseNativeFiles error:', err);
    return [];
  }
}

async function browseNativeVideo() {
  try {
    const res = await apiGet('/browse-video');
    return res.path || '';
  } catch (err) {
    console.error('browseNativeVideo error:', err);
    return '';
  }
}

async function browseNativeFolder() {
  try {
    const res = await apiGet('/browse-folder');
    return res.path || '';
  } catch (err) {
    console.error('browseNativeFolder error:', err);
    return '';
  }
}

async function uploadDroppedFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE_URL}/upload-file`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload error: ${res.status}`);
  const data = await res.json();
  return data.path || '';
}
// ── Live Bot Status Polling ────────────────────────────────────────────────
async function getBotLiveStatus() {
  try {
    return await apiGet('/bot-status');
  } catch (err) {
    console.error('Failed to get live bot status:', err);
    return null;
  }
}

async function endTasks() {
  try {
    const res = await apiPost('/end-tasks', {});
    document.querySelectorAll('#btn-stop, .btn-danger').forEach(btn => {
      if (btn.textContent.includes('Stop')) {
        btn.disabled = true;
        btn.textContent = '⏹ Stopped';
      }
    });
    if (typeof onBotStopped === 'function') {
      onBotStopped();
    }
  } catch (err) {
    console.error('Error ending tasks:', err);
  }
}

async function getFailedFieldsValue() {
  try {
    const failed = await apiPost('/getfailedfields', {});
    return failed;
  } catch (err) {
    alert(`Execution Error: ${err.message}`);
    enableControls();
  }
}

async function runFailedBot() {
  const res = await apiPost('/run-failed', {});
  return res;
}

// ── Bot Operations ──────────────────────────────────────────────────────────
async function runBot() {
  if (!await validate()) return;
  disableControls();
  setStatus('Running Bot...', 'active');

  try {
    // ── Step 1: Fetch which listings are already completed ──
    let postedSet = new Set(); // Set of "title||||email" keys already done
    try {
      const statusResp = await fetch('/listing-status');
      if (statusResp.ok) {
        const statusData = await statusResp.json();
        (statusData.listings || []).forEach(item => {
          if (item.posted) {
            postedSet.add((item.title || '').trim().toLowerCase() + '||||' + (item.email || ''));
          }
        });
      }
    } catch (e) {
      console.warn('Could not pre-check listing status, sending all:', e);
    }

    // ── Step 2: Collect all entries and filter out already-posted ones ──
    const allListings = entries.map(collectEntryData);
    const pendingListings = allListings.filter(listing => {
      // A listing is "done" if it's posted on ALL accounts that have it in saved_states
      // Since we can't know the account mapping here, we check if ANY account has it pending
      const titleKey = (listing.title || '').trim().toLowerCase();
      // Check if this title appears in the postedSet for any account
      // We filter it out only if ALL its occurrences are posted (i.e. none pending)
      const matchedPosted = [...postedSet].filter(k => k.startsWith(titleKey + '||||'));
      const matchedAll = [...postedSet].filter(k => k.startsWith(titleKey + '||||'));
      // If this title has ZERO completed records, it's pending — include it
      if (matchedPosted.length === 0) return true;
      // Otherwise it has some completed records — still include it (backend will skip per-account)
      return true;
    });

    // Simple approach: the backend (Open_fb.py) handles per-account skipping via completed_log.json.
    // Here we just warn the user how many were already done.
    const skippedCount = postedSet.size > 0 ? [...new Set([...postedSet].map(k => k.split('||||')[0]))].length : 0;
    if (skippedCount > 0) {
      setStatus(`Running Bot... (${skippedCount} already-posted listing(s) will be skipped)`, 'active');
    }

    const payload = {
      listings:           allListings,
      wait_time:          getWaitTimeSeconds(''),
      wait_time_accounts: getWaitTimeSeconds('-account'),
      marketplace:        getMarketplace()
    };
    await apiPost('/run-bot', payload);
    if (typeof onBotStarted === 'function') {
      onBotStarted();
    }
  } catch (err) {
    alert(`Execution Error: ${err.message}`);
    enableControls();
    if (typeof stopLiveStatusPolling === 'function') {
      stopLiveStatusPolling();
    }
  }
}

async function markDoneAPI(title, email) {
  return await apiPost('/mark-done', { title, email });
}


// Legacy alias - both actions now use unified interleaved distribution
async function runDistributeBot() {
  return runBot();
}




async function renewListings() {
  disableControls();
  setStatus('Renewing Listings...', 'active');
  try {
    const count = parseInt(document.getElementById('renew-count').value) || 2;
    await apiPost('/renew', { count });
    enableControls();
    setStatus('Renew Complete', 'success');
  } catch (err) {
    alert(`Execution Error: ${err.message}`);
    enableControls();
  }
}

async function deleteAndRelist() {
  disableControls();
  setStatus('Relisting Items...', 'active');
  try {
    const count = parseInt(document.getElementById('delete-relist-count').value) || 2;
    await apiPost('/delete-relist', { count });
    enableControls();
    setStatus('Relist Complete', 'success');
  } catch (err) {
    alert(`Execution Error: ${err.message}`);
    enableControls();
  }
}

async function runFailedBot() {
  disableControls();
  setStatus('Regenerating Failed...', 'active');
  try {
    await apiPost('/run-failed', {});
    enableControls();
    setStatus('Regen Complete', 'success');
  } catch (err) {
    alert(`Execution Error: ${err.message}`);
    enableControls();
  }
}

// ── Preset Operations ──────────────────────────────────────────────────────
async function confirmSave() {
  const name = document.getElementById('save-name-input').value.trim();
  if (!name) { alert('Please enter a preset name.'); return; }
  const data = entries.map(collectEntryData);
  try {
    await apiPost('/save-fields', { name, fields: data });
    closeModal('modal-save');
    setStatus(`Saved: "${name}"`, 'success');
  } catch (err) {
    alert(`Save failed: ${err.message}`);
  }
}

async function loadSavedFields() {
  try {
    const { states } = await apiGet('/saved-states');
    const listEl = document.getElementById('saved-states-list');
    listEl.innerHTML = '';
    if (!states || states.length === 0) {
      listEl.innerHTML = '<div style="color:var(--text-muted);">No saved presets found.</div>';
    } else {
      states.forEach(s => {
        const row = document.createElement('div');
        row.className = 'saved-item';
        const nameSpan = document.createElement('span');
        nameSpan.textContent = s.name || s;
        const loadBtn = document.createElement('button');
        loadBtn.className = 'btn btn-primary';
        loadBtn.style.fontSize = '12px';
        loadBtn.textContent = 'Load';
        loadBtn.onclick = () => loadState(s.name || s);
        row.appendChild(nameSpan);
        row.appendChild(loadBtn);
        listEl.appendChild(row);
      });
    }
    openModal('modal-load');
  } catch (err) {
    alert(`Failed loading presets: ${err.message}`);
  }
}

async function loadState(name) {
  try {
    const { fields } = await apiGet(`/load-fields?name=${encodeURIComponent(name)}`);
    closeModal('modal-load');
    entries = [];
    document.getElementById('entries-list').innerHTML = '';
    updateEmptyState();
    fields.forEach(f => {
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
      const set = (fieldId, val) => {
        const el = document.getElementById(fieldId);
        if (el) el.value = val ?? '';
      };
      set(`title-${id}`,        f.title);
      set(`desc-${id}`,         f.description);
      set(`category-${id}`,     f.category);
      set(`location-${id}`,     f.location);
      set(`tags-${id}`,         (f.tags || []).join(', '));
      set(`price-${id}`,        f.price);
      set(`condition-${id}`,    f.condition);
      set(`availability-${id}`, f.availability);
      set(`video-input-${id}`,  f.video);
      if (document.getElementById(`meetup-${id}`))  document.getElementById(`meetup-${id}`).checked  = !!f.public_meetup;
      if (document.getElementById(`pickup-${id}`))  document.getElementById(`pickup-${id}`).checked  = !!f.door_pickup;
      if (document.getElementById(`dropoff-${id}`)) document.getElementById(`dropoff-${id}`).checked = !!f.door_dropoff;
    });
    setStatus(`Loaded: "${name}"`, 'success');
  } catch (err) {
    alert(`Load failed: ${err.message}`);
  }
}

async function saveQuickFieldsToPreset() {
  const fields = parseQuickFields();
  if (!fields) return;

  const name = prompt('Enter Preset Name:');
  if (!name || !name.trim()) return;

  try {
    await apiPost('/save-fields', { name: name.trim(), fields });
    closeModal('modal-quick-save');
    setStatus(`Saved Bulk Preset: "${name.trim()}"`, 'success');
  } catch (err) {
    alert(`Save preset failed: ${err.message}`);
  }
}

// ── Account Profiles Management ─────────────────────────────────────────────
async function fetchAccounts() {
  return await apiGet('/accounts');
}

async function saveAccountAPI(email, phone, password, proxy) {
  return await apiPost('/accounts', { email, phone, password, proxy });
}

async function triggerAutoLoginAPI(email, password, proxy) {
  return await apiPost('/login-session', { email, password, proxy });
}

async function deleteAccountAPI(email) {
  const res = await fetch(`${BASE_URL}/accounts?email=${encodeURIComponent(email)}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
  return res.json();
}

// ── Bulk & Folder API Helpers ──────────────────────────────────────────────
async function importCSVAPI(file) {
  const formData = new FormData();
  formData.append('file', file);

  const folder = (document.getElementById('bulk-image-folder')?.value || localStorage.getItem('fb_bot_image_pool_folder') || '').trim();
  const imagesPerListing = document.getElementById('bulk-images-per-listing')?.value || '1';
  const minGap = document.getElementById('bulk-image-gap')?.value || '25';
  const autoAssign = document.getElementById('bulk-auto-assign-csv') ? document.getElementById('bulk-auto-assign-csv').checked : true;

  if (folder && autoAssign) {
    formData.append('image_folder', folder);
    formData.append('images_per_listing', imagesPerListing);
    formData.append('min_gap', minGap);
  }

  const res = await fetch(`${BASE_URL}/import-csv`, { method: 'POST', body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'CSV Import failed');
  }
  return res.json();
}

async function scanImagePoolAPI(folderPath) {
  const res = await fetch(`${BASE_URL}/scan-image-pool?folder_path=${encodeURIComponent(folderPath)}`);
  if (!res.ok) return { status: 'error', count: 0 };
  return res.json();
}

async function autoAssignImagesAPI(payload) {
  return await apiPost('/auto-assign-images', payload);
}

async function scanFolderAPI(folderPath) {
  return await apiPost('/scan-folder', { folder_path: folderPath });
}

async function fetchFlaggedAccountsAPI() {
  return await apiGet('/flagged-accounts');
}

async function unflagAccountAPI(email) {
  return await apiPost('/unflag-account', { email });
}

function downloadCSVTemplate() {
  window.open(`${BASE_URL}/download-template`, '_blank');
}