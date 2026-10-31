/**
 * Controller Frontend untuk Portal Data Cipta Group
 * Fitur: Change Detection, Manajemen Data Baru, Tambah Proyek/Dokumen Manual, Riwayat Perubahan
 */

// State Global
let rawData = null;
let currentProjects = [];
let currentCategory = 'ALL'; // 'ALL' | 'NEW' | 'RESIDENTIAL' | 'COMMERCIAL'
let currentDocType = 'ALL';
let currentSort = 'DEFAULT';
let searchQuery = '';
let currentView = 'grid'; // 'grid' | 'list'
let selectedProjectIdForDoc = null;

// Pemetaan Kategori Proyek
const COMMERCIAL_KEYWORDS = ['pertokoan', 'square', 'marina central', 'namarina', 'ruko', 'pasar'];

function getProjectCategory(title) {
  const t = (title || '').toLowerCase();
  for (const kw of COMMERCIAL_KEYWORDS) {
    if (t.includes(kw)) {
      return { id: 'COMMERCIAL', label: 'Pertokoan & Komersial', color: 'amber' };
    }
  }
  return { id: 'RESIDENTIAL', label: 'Hunian / Residensial', color: 'brand' };
}

// Deteksi Jenis Dokumen
function getDocTypeInfo(title, url) {
  const t = (title || '').toLowerCase();
  const u = (url || '').toLowerCase();

  if (t.includes('brosur') || t.includes('brochure') || t.includes('flyer')) {
    return { id: 'BROCHURE', label: 'E-Brosur', icon: 'book-open', color: 'emerald', bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' };
  }
  if (t.includes('pricelist') || t.includes('harga') || t.includes('price')) {
    return { id: 'PRICELIST', label: 'Pricelist', icon: 'badge-dollar-sign', color: 'amber', bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20' };
  }
  if (t.includes('siteplan') || t.includes('site plan') || t.includes('denah') || t.includes('floor plan')) {
    return { id: 'SITEPLAN', label: 'Siteplan', icon: 'map', color: 'cyan', bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' };
  }
  if (t.includes('lokasi') || t.includes('maps') || t.includes('map') || u.includes('maps.app.goo.gl') || u.includes('google.com/maps')) {
    return { id: 'MAPS', label: 'Lokasi Maps', icon: 'navigation', color: 'rose', bg: 'bg-rose-500/10 text-rose-400 border-rose-500/20' };
  }
  if (t.includes('video') || t.includes('promo') || t.includes('promosi') || t.includes('pk')) {
    return { id: 'VIDEO', label: 'Video / Promo', icon: 'play-circle', color: 'purple', bg: 'bg-purple-500/10 text-purple-400 border-purple-500/20' };
  }
  if (t.includes('render') || t.includes('desain') || t.includes('fasad') || t.includes('tampak') || t.includes('tipe') || t.includes('type') || t.includes('gambar') || t.includes('foto')) {
    return { id: 'DESIGN', label: 'Render / Desain', icon: 'palette', color: 'indigo', bg: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' };
  }
  return { id: 'OTHER', label: 'Dokumen', icon: 'file-text', color: 'slate', bg: 'bg-slate-500/10 text-slate-300 border-slate-500/20' };
}

// Inisialisasi Data
async function initApp() {
  try {
    const res = await fetch('/api/data', { cache: 'no-store' });
    if (res.ok) {
      rawData = await res.json();
    }
  } catch (err) {
    console.log('[*] Berjalan dalam mode mandiri/offline');
  }

  if (!rawData && window.CIPTAGROUP_DATA) {
    rawData = window.CIPTAGROUP_DATA;
  }

  if (!rawData) {
    showToast('Gagal memuat database properti.', 'error');
    return;
  }

  setupHeaderInfo();
  processData();
  calculateStats();
  checkNewDataStatus();
  applyFilters();
}

// Setup Info Header
function setupHeaderInfo() {
  if (rawData.avatar_url) {
    document.getElementById('headerAvatar').src = rawData.avatar_url;
  }
  if (rawData.page_title) {
    document.getElementById('headerTitle').textContent = 'Cipta Group Official';
  }
  if (rawData.username) {
    document.getElementById('headerSubtitle').innerHTML = `
      <span>@${rawData.username}</span>
      <span>•</span>
      <span class="flex items-center gap-1 text-slate-300">
        <i data-lucide="map-pin" class="w-3.5 h-3.5 text-rose-400"></i> Batam, Kepulauan Riau
      </span>
    `;
  }
  if (rawData.url) {
    document.getElementById('linktreeBtn').href = rawData.url;
  }
}

// Olah dan Bersihkan Data
function processData() {
  const rawList = rawData.links || [];
  currentProjects = rawList.map((proj, idx) => {
    const category = getProjectCategory(proj.title);
    const subLinks = (proj.sub_links || []).map(sub => {
      const typeInfo = getDocTypeInfo(sub.title, sub.url);
      return {
        ...sub,
        is_new: !!sub.is_new,
        typeInfo
      };
    });

    const hasNewItems = !!proj.is_new || !!proj.has_new_items || subLinks.some(s => s.is_new);

    return {
      id: proj.id || idx + 1,
      title: proj.title,
      url: proj.url,
      category,
      is_new: !!proj.is_new,
      has_new_items: hasNewItems,
      created_at: proj.created_at || null,
      sub_links: subLinks,
      docCount: subLinks.length
    };
  });
}

// Hitung Statistik & Cek Data Baru
function calculateStats() {
  const totalProjects = currentProjects.length;
  let totalDocs = 0;
  let brochures = 0;
  let pricelists = 0;
  let siteplans = 0;
  let newItemsCount = 0;

  let residentialCount = 0;
  let commercialCount = 0;
  let newProjectsCount = 0;
  let newDocsCount = 0;

  currentProjects.forEach(p => {
    if (p.category.id === 'COMMERCIAL') commercialCount++;
    else residentialCount++;

    if (p.is_new) {
      newProjectsCount++;
      newItemsCount++;
    }

    p.sub_links.forEach(sub => {
      totalDocs++;
      const typeId = sub.typeInfo.id;
      if (typeId === 'BROCHURE') brochures++;
      else if (typeId === 'PRICELIST') pricelists++;
      else if (typeId === 'SITEPLAN') siteplans++;

      if (sub.is_new && !p.is_new) {
        newDocsCount++;
        newItemsCount++;
      }
    });
  });

  document.getElementById('statTotalProjects').textContent = totalProjects;
  document.getElementById('statTotalDocuments').textContent = totalDocs;
  document.getElementById('statBrochures').textContent = brochures;
  document.getElementById('statPricelists').textContent = pricelists;
  document.getElementById('statSiteplans').textContent = siteplans;
  document.getElementById('statNewItems').textContent = newItemsCount;

  document.getElementById('catCountAll').textContent = totalProjects;
  document.getElementById('catCountRes').textContent = residentialCount;
  document.getElementById('catCountCom').textContent = commercialCount;
  document.getElementById('catCountNew').textContent = newProjectsCount + newDocsCount;
}

// Cek Banner Data Baru
function checkNewDataStatus() {
  const banner = document.getElementById('newDataBanner');
  const bannerBadge = document.getElementById('bannerNewCountBadge');
  const bannerDesc = document.getElementById('bannerNewDesc');

  let newProjects = currentProjects.filter(p => p.is_new);
  let newDocs = [];
  currentProjects.forEach(p => {
    p.sub_links.forEach(s => {
      if (s.is_new) newDocs.push({ proj: p.title, doc: s.title });
    });
  });

  const totalNew = newProjects.length + newDocs.length;
  if (totalNew > 0) {
    banner.classList.remove('hidden');
    bannerBadge.textContent = `${totalNew} BARU`;
    
    let descParts = [];
    if (newProjects.length > 0) descParts.push(`${newProjects.length} Proyek Baru`);
    if (newDocs.length > 0) descParts.push(`${newDocs.length} Berkas/Dokumen Baru`);
    bannerDesc.textContent = `Berhasil mendeteksi: ${descParts.join(' & ')}. Data siap ditinjau dan digunakan!`;
  } else {
    banner.classList.add('hidden');
  }
}

// Terapkan Filter & Pencarian
function applyFilters() {
  searchQuery = document.getElementById('searchInput').value.trim().toLowerCase();
  currentDocType = document.getElementById('docTypeFilter').value;
  currentSort = document.getElementById('sortSelect').value;

  const clearBtn = document.getElementById('clearSearchBtn');
  if (searchQuery) {
    clearBtn.classList.remove('hidden');
  } else {
    clearBtn.classList.add('hidden');
  }

  let filtered = currentProjects.filter(proj => {
    // Filter Kategori Khusus DATA BARU
    if (currentCategory === 'NEW') {
      if (!proj.has_new_items) return false;
    } else if (currentCategory !== 'ALL' && proj.category.id !== currentCategory) {
      return false;
    }

    // Filter Tipe Dokumen
    if (currentDocType !== 'ALL') {
      const hasType = proj.sub_links.some(sub => sub.typeInfo.id === currentDocType);
      if (!hasType) return false;
    }

    // Filter Pencarian Teks
    if (searchQuery) {
      const titleMatch = proj.title.toLowerCase().includes(searchQuery);
      const subMatch = proj.sub_links.some(sub => sub.title.toLowerCase().includes(searchQuery));
      if (!titleMatch && !subMatch) return false;
    }

    return true;
  });

  // Pengurutan
  if (currentSort === 'NEWEST') {
    filtered.sort((a, b) => (b.has_new_items ? 1 : 0) - (a.has_new_items ? 1 : 0));
  } else if (currentSort === 'NAME_ASC') {
    filtered.sort((a, b) => a.title.localeCompare(b.title));
  } else if (currentSort === 'NAME_DESC') {
    filtered.sort((a, b) => b.title.localeCompare(a.title));
  } else if (currentSort === 'ITEMS_DESC') {
    filtered.sort((a, b) => b.docCount - a.docCount);
  }

  renderData(filtered);
}

// Render Data ke Tampilan
function renderData(projects) {
  const gridView = document.getElementById('gridView');
  const listView = document.getElementById('listView');
  const emptyState = document.getElementById('emptyState');
  const tableBody = document.getElementById('tableBody');

  if (projects.length === 0) {
    gridView.classList.add('hidden');
    listView.classList.add('hidden');
    emptyState.classList.remove('hidden');
    return;
  }

  emptyState.classList.add('hidden');

  if (currentView === 'grid') {
    gridView.classList.remove('hidden');
    listView.classList.add('hidden');
    renderGrid(projects, gridView);
  } else {
    gridView.classList.add('hidden');
    listView.classList.remove('hidden');
    renderList(projects, tableBody);
  }

  lucide.createIcons();
}

// Render Card Grid View
function renderGrid(projects, container) {
  container.innerHTML = projects.map(proj => {
    const isCommercial = proj.category.id === 'COMMERCIAL';
    const badgeColor = isCommercial 
      ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' 
      : 'bg-brand-500/10 text-brand-400 border-brand-500/30';

    const newHighlightClass = proj.has_new_items ? 'border-new-highlight' : '';

    const newBadge = proj.is_new 
      ? `<span class="px-2 py-0.5 text-[10px] font-bold rounded-md bg-amber-500 text-dark-950 uppercase badge-new-pulse">✨ PROYEK BARU</span>`
      : proj.has_new_items 
      ? `<span class="px-2 py-0.5 text-[10px] font-bold rounded-md bg-amber-500/20 text-amber-400 border border-amber-500/40 uppercase">✨ BERKAS BARU</span>`
      : '';

    const previewLinks = proj.sub_links.slice(0, 4).map(sub => `
      <a href="${sub.url}" target="_blank" rel="noopener noreferrer" 
         class="group/item flex items-center justify-between p-2 rounded-xl bg-slate-900/80 hover:bg-slate-800 border ${sub.is_new ? 'border-amber-500/50 bg-amber-500/5' : 'border-slate-800/80'} hover:border-slate-700 transition">
        <div class="flex items-center gap-2 min-w-0 pr-2">
          <span class="w-6 h-6 rounded-lg ${sub.typeInfo.bg} flex items-center justify-center shrink-0">
            <i data-lucide="${sub.typeInfo.icon}" class="w-3 h-3"></i>
          </span>
          <span class="text-xs font-medium text-slate-300 group-hover/item:text-brand-400 truncate">${sub.title}</span>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          ${sub.is_new ? `<span class="px-1.5 py-0.2 text-[9px] font-bold rounded bg-amber-500 text-dark-950">BARU</span>` : ''}
          <i data-lucide="arrow-up-right" class="w-3.5 h-3.5 text-slate-500 group-hover/item:text-brand-400"></i>
        </div>
      </a>
    `).join('');

    const moreCount = proj.sub_links.length - 4;

    return `
      <div class="glass-card glass-card-hover rounded-2xl p-5 border border-slate-800/90 ${newHighlightClass} flex flex-col justify-between relative overflow-hidden">
        
        <div>
          <div class="flex items-start justify-between gap-2 mb-2">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="px-2.5 py-0.5 text-xs font-semibold rounded-md border ${badgeColor}">
                ${proj.category.label}
              </span>
              ${newBadge}
            </div>
            <span class="px-2 py-0.5 text-xs rounded-full bg-slate-800 text-slate-400 border border-slate-700 font-mono shrink-0">
              ${proj.docCount} Berkas
            </span>
          </div>

          <h3 class="text-lg font-bold text-white tracking-tight hover:text-brand-400 transition cursor-pointer mt-1" 
              onclick="openProjectModal(${proj.id})">
            ${proj.title}
          </h3>

          <!-- Links preview list -->
          <div class="space-y-1.5 mt-3.5">
            ${previewLinks}
          </div>

          ${moreCount > 0 ? `
            <button onclick="openProjectModal(${proj.id})" class="w-full text-center py-1.5 mt-2 text-xs font-semibold text-brand-400 hover:text-brand-300 hover:underline">
              + ${moreCount} Dokumen Tambahan Lainnya
            </button>
          ` : ''}
        </div>

        <!-- Card Footer Actions -->
        <div class="pt-4 mt-4 border-t border-slate-800/80 flex items-center justify-between gap-2">
          <button onclick="openProjectModal(${proj.id})" 
                  class="flex-1 py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center justify-center gap-1.5 shadow-sm">
            <i data-lucide="folder-open" class="w-3.5 h-3.5 text-brand-400"></i>
            <span>Detail</span>
          </button>

          <button onclick="openAddDocModal(${proj.id}, '${proj.title}')" 
                  title="Tambah Dokumen ke Proyek Ini"
                  class="p-2 rounded-xl bg-brand-500/10 hover:bg-brand-500/20 text-brand-400 border border-brand-500/30 transition">
            <i data-lucide="file-plus" class="w-3.5 h-3.5"></i>
          </button>

          <button onclick="copyToClipboard('${proj.url}', 'Tautan Linktree ${proj.title}')" 
                  title="Salin Tautan"
                  class="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition">
            <i data-lucide="copy" class="w-3.5 h-3.5"></i>
          </button>

          <a href="${proj.url}" target="_blank" rel="noopener noreferrer"
             title="Buka Linktree Asli"
             class="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-brand-400 border border-slate-800 transition">
            <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
          </a>
        </div>
      </div>
    `;
  }).join('');
}

// Render Table / List View
function renderList(projects, tbody) {
  let rows = '';
  let counter = 1;

  projects.forEach(proj => {
    proj.sub_links.forEach(sub => {
      if (currentDocType !== 'ALL' && sub.typeInfo.id !== currentDocType) return;
      if (searchQuery && !proj.title.toLowerCase().includes(searchQuery) && !sub.title.toLowerCase().includes(searchQuery)) return;

      const newBadge = sub.is_new 
        ? `<span class="ml-2 px-1.5 py-0.5 text-[9px] font-bold rounded bg-amber-500 text-dark-950 uppercase">✨ BARU</span>`
        : '';

      rows += `
        <tr class="hover:bg-slate-800/40 transition ${sub.is_new ? 'bg-amber-500/5' : ''}">
          <td class="px-6 py-3.5 text-xs text-slate-500 font-mono">${counter++}</td>
          <td class="px-6 py-3.5">
            <div class="flex items-center gap-1.5">
              <span class="font-semibold text-white hover:text-brand-400 cursor-pointer" onclick="openProjectModal(${proj.id})">
                ${proj.title}
              </span>
              ${proj.is_new ? `<span class="px-1.5 py-0.2 text-[9px] font-bold rounded bg-amber-500 text-dark-950">BARU</span>` : ''}
            </div>
          </td>
          <td class="px-6 py-3.5">
            <span class="px-2 py-0.5 text-xs rounded-md bg-slate-800 text-slate-300 border border-slate-700">
              ${proj.category.label}
            </span>
          </td>
          <td class="px-6 py-3.5 font-medium text-slate-200">
            <span>${sub.title}</span>
            ${newBadge}
          </td>
          <td class="px-6 py-3.5">
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-lg ${sub.typeInfo.bg}">
              <i data-lucide="${sub.typeInfo.icon}" class="w-3 h-3"></i>
              ${sub.typeInfo.label}
            </span>
          </td>
          <td class="px-6 py-3.5 text-right space-x-1">
            <button onclick="copyToClipboard('${sub.url}', '${sub.title}')" title="Salin Link"
                    class="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition">
              <i data-lucide="copy" class="w-3.5 h-3.5"></i>
            </button>
            <a href="${sub.url}" target="_blank" rel="noopener noreferrer" title="Buka Link"
               class="p-1.5 inline-block rounded-lg text-brand-400 hover:text-brand-300 hover:bg-slate-800 transition">
              <i data-lucide="arrow-up-right" class="w-3.5 h-3.5"></i>
            </a>
          </td>
        </tr>
      `;
    });
  });

  tbody.innerHTML = rows;
}

// Buka Modal Detail Proyek
function openProjectModal(projectId) {
  const proj = currentProjects.find(p => p.id === projectId);
  if (!proj) return;

  selectedProjectIdForDoc = projectId;

  document.getElementById('modalTitle').textContent = proj.title;
  document.getElementById('modalCategory').textContent = proj.category.label;
  document.getElementById('modalLinktree').href = proj.url;
  document.getElementById('modalLinktreeText').textContent = proj.url;

  const newBadge = document.getElementById('modalNewBadge');
  if (proj.has_new_items) {
    newBadge.classList.remove('hidden');
  } else {
    newBadge.classList.add('hidden');
  }

  const listContainer = document.getElementById('modalLinkList');
  listContainer.innerHTML = proj.sub_links.map(sub => `
    <div class="flex items-center justify-between p-3 rounded-2xl bg-slate-900 border ${sub.is_new ? 'border-amber-500/50 bg-amber-500/5' : 'border-slate-800'} hover:border-slate-700 transition">
      <div class="flex items-center gap-3 min-w-0 pr-3">
        <div class="w-9 h-9 rounded-xl ${sub.typeInfo.bg} flex items-center justify-center shrink-0">
          <i data-lucide="${sub.typeInfo.icon}" class="w-4 h-4"></i>
        </div>
        <div class="truncate">
          <div class="text-sm font-semibold text-white flex items-center gap-1.5 truncate">
            <span>${sub.title}</span>
            ${sub.is_new ? `<span class="px-1.5 py-0.2 text-[9px] font-bold rounded bg-amber-500 text-dark-950 uppercase">BARU</span>` : ''}
          </div>
          <div class="text-xs text-slate-400 truncate font-mono">${sub.url}</div>
        </div>
      </div>
      <div class="flex items-center gap-1.5 shrink-0">
        <button onclick="copyToClipboard('${sub.url}', '${sub.title}')" title="Salin Tautan"
                class="p-2 rounded-xl bg-slate-800 text-slate-300 hover:text-white transition">
          <i data-lucide="copy" class="w-4 h-4"></i>
        </button>
        <a href="${sub.url}" target="_blank" rel="noopener noreferrer"
           class="px-3 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold transition flex items-center gap-1 shadow-sm">
          <span>Buka</span>
          <i data-lucide="arrow-up-right" class="w-3.5 h-3.5"></i>
        </a>
      </div>
    </div>
  `).join('');

  document.getElementById('projectModal').classList.remove('hidden');
  lucide.createIcons();
}

function openAddDocModalFromDetail() {
  const proj = currentProjects.find(p => p.id === selectedProjectIdForDoc);
  if (proj) {
    closeModal('projectModal');
    openAddDocModal(proj.id, proj.title);
  }
}

// Buka Modal Tambah Proyek Baru
function openAddProjectModal() {
  document.getElementById('addProjectForm').reset();
  const docContainer = document.getElementById('dynamicDocContainer');
  docContainer.innerHTML = '';
  // Tambah default 1 row
  addDynamicDocRow('E-Brosur', 'https://drive.google.com/...');
  document.getElementById('addProjectModal').classList.remove('hidden');
  lucide.createIcons();
}

// Baris Dokumen Dinamis
function addDynamicDocRow(title = '', url = '') {
  const container = document.getElementById('dynamicDocContainer');
  const div = document.createElement('div');
  div.className = 'flex items-center gap-2 dynamic-doc-row';
  div.innerHTML = `
    <input type="text" placeholder="Judul (cth: E-Brosur, Pricelist)" value="${title}" required
           class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 doc-title-input" />
    <input type="url" placeholder="URL Berkas (Google Drive / Maps)" value="${url}" required
           class="flex-[1.5] bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 doc-url-input" />
    <button type="button" onclick="this.parentElement.remove()" class="p-2 text-slate-500 hover:text-rose-400 transition" title="Hapus baris">
      <i data-lucide="trash-2" class="w-4 h-4"></i>
    </button>
  `;
  container.appendChild(div);
  lucide.createIcons();
}

// Submit Tambah Proyek Baru
async function submitNewProject(e) {
  e.preventDefault();
  const title = document.getElementById('newProjTitle').value.trim();
  const category = document.getElementById('newProjCategory').value;
  const url = document.getElementById('newProjUrl').value.trim() || `https://linktr.ee/${title.toLowerCase().replace(/\s+/g, '')}`;

  const docRows = document.querySelectorAll('.dynamic-doc-row');
  const subLinks = [];
  docRows.forEach(row => {
    const dTitle = row.querySelector('.doc-title-input').value.trim();
    const dUrl = row.querySelector('.doc-url-input').value.trim();
    if (dTitle && dUrl) {
      subLinks.push({ title: dTitle, url: dUrl, type: 'CLASSIC' });
    }
  });

  const payload = { title, url, category, sub_links: subLinks };

  try {
    const res = await fetch('/api/project/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const result = await res.json();
      showToast(result.message || 'Proyek baru berhasil ditambahkan!', 'success');
      closeModal('addProjectModal');
      // Reload data
      const dataRes = await fetch('/api/data');
      if (dataRes.ok) {
        rawData = await dataRes.json();
        processData();
        calculateStats();
        checkNewDataStatus();
        filterCategory('NEW');
      }
    } else {
      throw new Error('Gagal menyimpan ke server');
    }
  } catch (err) {
    // Mode Offline / Fallback
    const newProjObj = {
      id: Date.now(),
      title,
      url,
      category: { id: category, label: category === 'COMMERCIAL' ? 'Pertokoan & Komersial' : 'Hunian / Residensial' },
      is_new: true,
      has_new_items: true,
      sub_links: subLinks.map(s => ({ ...s, is_new: true, typeInfo: getDocTypeInfo(s.title, s.url) })),
      docCount: subLinks.length
    };
    currentProjects.unshift(newProjObj);
    calculateStats();
    checkNewDataStatus();
    filterCategory('NEW');
    closeModal('addProjectModal');
    showToast(`Proyek '${title}' berhasil ditambahkan (Mode Lokal)!`, 'success');
  }
}

// Buka Modal Tambah Dokumen ke Proyek
function openAddDocModal(projectId, projectTitle) {
  document.getElementById('addDocForm').reset();
  document.getElementById('targetProjectId').value = projectId;
  document.getElementById('targetProjectName').value = projectTitle;
  document.getElementById('addDocModal').classList.remove('hidden');
}

// Submit Tambah Dokumen Baru
async function submitNewDocument(e) {
  e.preventDefault();
  const projectId = document.getElementById('targetProjectId').value;
  const title = document.getElementById('newDocTitle').value.trim();
  const url = document.getElementById('newDocUrl').value.trim();

  const payload = { project_id: projectId, title, url, type: 'CLASSIC' };

  try {
    const res = await fetch('/api/project/add-document', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const result = await res.json();
      showToast(result.message || 'Dokumen berhasil ditambahkan!', 'success');
      closeModal('addDocModal');
      const dataRes = await fetch('/api/data');
      if (dataRes.ok) {
        rawData = await dataRes.json();
        processData();
        calculateStats();
        checkNewDataStatus();
        applyFilters();
      }
    } else {
      throw new Error('Gagal menambahkan berkas ke server');
    }
  } catch (err) {
    // Fallback Lokal
    const target = currentProjects.find(p => String(p.id) === String(projectId));
    if (target) {
      target.sub_links.unshift({
        title,
        url,
        type: 'CLASSIC',
        is_new: true,
        typeInfo: getDocTypeInfo(title, url)
      });
      target.docCount = target.sub_links.length;
      target.has_new_items = true;
      calculateStats();
      checkNewDataStatus();
      applyFilters();
      closeModal('addDocModal');
      showToast(`Dokumen '${title}' berhasil ditambahkan ke ${target.title}!`, 'success');
    }
  }
}

// Buka Modal Riwayat Perubahan (Changelog)
async function openHistoryModal() {
  const container = document.getElementById('historyListContainer');
  container.innerHTML = '<div class="py-8 text-center text-slate-400">Memuat riwayat perubahan...</div>';
  document.getElementById('historyModal').classList.remove('hidden');

  let historyData = [];
  try {
    const res = await fetch('/api/history');
    if (res.ok) {
      historyData = await res.json();
    }
  } catch (err) {
    console.log('[*] History API offline');
  }

  if (historyData.length === 0) {
    container.innerHTML = `
      <div class="py-8 text-center text-slate-500">
        <i data-lucide="info" class="w-8 h-8 mx-auto mb-2 text-slate-600"></i>
        <p>Belum ada catatan riwayat pembaruan.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = historyData.map(h => `
    <div class="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
      <div class="flex items-center justify-between">
        <span class="font-bold text-white">${h.title}</span>
        <span class="text-[11px] text-slate-500 font-mono">${h.timestamp}</span>
      </div>
      <div class="flex items-center gap-2">
        ${h.new_projects_count > 0 ? `<span class="px-2 py-0.5 rounded bg-brand-500/20 text-brand-400 text-[10px] font-bold">+${h.new_projects_count} PROYEK</span>` : ''}
        ${h.new_documents_count > 0 ? `<span class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 text-[10px] font-bold">+${h.new_documents_count} BERKAS</span>` : ''}
      </div>
      <ul class="text-slate-400 list-disc list-inside space-y-0.5 pt-1 text-[11px]">
        ${(h.items || []).map(it => `<li>${it}</li>`).join('')}
      </ul>
    </div>
  `).join('');

  lucide.createIcons();
}

// Tandai Semua Data Baru Sudah Dibaca
async function markAllAsRead() {
  try {
    await fetch('/api/mark-read', { method: 'POST' });
  } catch (err) {}

  currentProjects.forEach(p => {
    p.is_new = false;
    p.has_new_items = false;
    p.sub_links.forEach(s => s.is_new = false);
  });

  calculateStats();
  checkNewDataStatus();
  filterCategory('ALL');
  showToast('Semua data baru telah ditandai sudah dilihat!', 'success');
}

// Filter Kategori
function filterCategory(catId) {
  currentCategory = catId;
  document.querySelectorAll('.category-pill').forEach(btn => {
    btn.classList.remove('bg-brand-500/20', 'text-brand-400', 'border-brand-500/40', 'bg-amber-500/20', 'text-amber-400', 'border-amber-500/40');
    btn.classList.add('bg-slate-900', 'text-slate-400', 'border-slate-800');
  });

  const activeBtn = document.getElementById(`catBtn-${catId}`);
  if (activeBtn) {
    if (catId === 'NEW') {
      activeBtn.classList.add('bg-amber-500/20', 'text-amber-400', 'border-amber-500/40');
    } else {
      activeBtn.classList.add('bg-brand-500/20', 'text-brand-400', 'border-brand-500/40');
    }
    activeBtn.classList.remove('bg-slate-900', 'text-slate-400', 'border-slate-800');
  }

  applyFilters();
}

// Reset Filters
function resetFilters() {
  document.getElementById('searchInput').value = '';
  document.getElementById('docTypeFilter').value = 'ALL';
  document.getElementById('sortSelect').value = 'DEFAULT';
  filterCategory('ALL');
}

function clearSearch() {
  document.getElementById('searchInput').value = '';
  applyFilters();
}

// Switch View
function switchView(view) {
  currentView = view;
  const btnGrid = document.getElementById('btnGridView');
  const btnList = document.getElementById('btnListView');

  if (view === 'grid') {
    btnGrid.classList.add('text-brand-400', 'bg-slate-800');
    btnGrid.classList.remove('text-slate-400');
    btnList.classList.remove('text-brand-400', 'bg-slate-800');
    btnList.classList.add('text-slate-400');
  } else {
    btnList.classList.add('text-brand-400', 'bg-slate-800');
    btnList.classList.remove('text-slate-400');
    btnGrid.classList.remove('text-brand-400', 'bg-slate-800');
    btnGrid.classList.add('text-slate-400');
  }

  applyFilters();
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.add('hidden');
}

// Salin Tautan ke Clipboard
function copyToClipboard(text, label = 'Tautan') {
  navigator.clipboard.writeText(text).then(() => {
    showToast(`${label} berhasil disalin ke clipboard!`, 'success');
  }).catch(() => {
    showToast('Gagal menyalin tautan.', 'error');
  });
}

// Toast Notifikasi
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  
  const bgClass = type === 'success' 
    ? 'bg-slate-900 border-brand-500/50 text-white' 
    : type === 'error' 
    ? 'bg-slate-900 border-rose-500/50 text-white' 
    : 'bg-slate-900 border-indigo-500/50 text-white';

  const iconName = type === 'success' ? 'check-circle' : type === 'error' ? 'alert-triangle' : 'info';
  const iconColor = type === 'success' ? 'text-brand-400' : type === 'error' ? 'text-rose-400' : 'text-indigo-400';

  toast.className = `p-4 rounded-2xl border shadow-2xl flex items-center gap-3 text-xs font-semibold transition-all duration-300 transform translate-y-4 opacity-0 pointer-events-auto ${bgClass}`;
  toast.innerHTML = `
    <i data-lucide="${iconName}" class="w-4 h-4 ${iconColor} shrink-0"></i>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  lucide.createIcons();

  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-4', 'opacity-0');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-4');
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

// Ekspor Data
function exportData(format) {
  if (!currentProjects || currentProjects.length === 0) return;

  if (format === 'json') {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(rawData, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute('href', dataStr);
    dlAnchor.setAttribute('download', 'ciptagroup_data.json');
    dlAnchor.click();
    showToast('File JSON berhasil diunduh.', 'success');
  } else if (format === 'csv') {
    let csvContent = 'Project_Title,Project_URL,Item_Title,Item_URL,Item_Type,Is_New\n';
    currentProjects.forEach(p => {
      p.sub_links.forEach(sub => {
        const cleanTitle = (sub.title || '').replace(/"/g, '""');
        const projTitle = (p.title || '').replace(/"/g, '""');
        csvContent += `"${projTitle}","${p.url}","${cleanTitle}","${sub.url}","${sub.typeInfo.label}","${sub.is_new ? 'YES' : 'NO'}"\n`;
      });
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute('href', url);
    dlAnchor.setAttribute('download', 'ciptagroup_data.csv');
    dlAnchor.click();
    showToast('File CSV berhasil diunduh.', 'success');
  }
}

// Sinkronisasi Ulang via Backend
async function handleSyncData() {
  const icon = document.getElementById('syncIcon');
  icon.classList.add('animate-spin');

  try {
    const triggerRes = await fetch('/api/scrape', { method: 'POST' });
    if (!triggerRes.ok && triggerRes.status !== 409) {
      throw new Error('Gagal memulai scraping');
    }

    showToast('Memulai sinkronisasi ulang & pendeteksian data baru...', 'info');

    const pollInterval = setInterval(async () => {
      try {
        const statusRes = await fetch('/api/status');
        const status = await statusRes.json();

        if (!status.is_scraping) {
          clearInterval(pollInterval);
          icon.classList.remove('animate-spin');

          if (status.error) {
            showToast(`Scraping gagal: ${status.error}`, 'error');
          } else {
            const newProj = status.new_projects_count || 0;
            const newDocs = status.new_documents_count || 0;
            if (newProj > 0 || newDocs > 0) {
              showToast(`🎉 Ditemukan ${newProj} proyek baru & ${newDocs} dokumen baru!`, 'success');
            } else {
              showToast('Sinkronisasi selesai! Data sudah mutakhir.', 'success');
            }

            const newDataRes = await fetch('/api/data');
            if (newDataRes.ok) {
              rawData = await newDataRes.json();
              processData();
              calculateStats();
              checkNewDataStatus();
              applyFilters();
            }
          }
        }
      } catch (e) {
        clearInterval(pollInterval);
        icon.classList.remove('animate-spin');
      }
    }, 2000);

  } catch (err) {
    icon.classList.remove('animate-spin');
    showToast('Mode Standalone: Jalankan "python app.py" untuk sinkronisasi live.', 'info');
  }
}

// Inisialisasi Event
document.addEventListener('DOMContentLoaded', () => {
  initApp();

  document.getElementById('searchInput').addEventListener('input', applyFilters);

  // Close modals on click outside
  ['projectModal', 'addProjectModal', 'addDocModal', 'historyModal'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('click', (e) => {
        if (e.target.id === id) closeModal(id);
      });
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      ['projectModal', 'addProjectModal', 'addDocModal', 'historyModal'].forEach(closeModal);
    }
  });
});
