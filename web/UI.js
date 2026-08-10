function generateFailedUI(values) {
  console.log('Generating failed UI with values:', values);
  const container = document.getElementById('failed-list-content');
  if (!container) return;

  container.innerHTML = '';

  const items = Array.isArray(values) ? values : [];
  if (items.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'failed-empty';
    empty.textContent = 'No failed items to show.';
    container.appendChild(empty);
    if (typeof window.openModal === 'function') {
      window.openModal('modal-failed');
    }
    return;
  }

  items.forEach((item) => {
    const card = document.createElement('div');
    card.className = 'failed-item-card';

    const title = document.createElement('div');
    title.className = 'failed-item-title';
    title.textContent = item?.Title || item?.title || item?.name || 'Untitled listing';

    const description = document.createElement('div');
    description.className = 'failed-item-description';
    const rawDescription = item?.Description || item?.description || '';
    description.textContent = rawDescription ? String(rawDescription).replace(/\n/g, ' ').trim() : 'No description provided.';

    card.appendChild(title);
    card.appendChild(description);
    container.appendChild(card);
  });

  const footer = document.querySelector('#modal-failed .modal-actions');
  if (footer) {
    footer.querySelector('.failed-modal-action')?.remove();

    const actionBtn = document.createElement('button');
    actionBtn.type = 'button';
    actionBtn.className = 'btn btn-warning failed-item-btn failed-modal-action';
    actionBtn.textContent = 'Regenerate Failed Listings';
    actionBtn.onclick = () => {
      runFailedBot()
    };

    footer.insertBefore(actionBtn, footer.firstChild);
  }

  if (typeof window.openModal === 'function') {
    window.openModal('modal-failed');
  }
}

window.handleGenerateFailedVideos = window.handleGenerateFailedVideos || function (item) {
  console.log('Generate failed videos for:', item);
};