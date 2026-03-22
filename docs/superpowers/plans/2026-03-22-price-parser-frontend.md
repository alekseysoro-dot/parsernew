# Price Parser Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `reverens/price-parser.html` to add a product detail drawer, settings modal with localStorage, SVG price chart, clickable table rows with active state, and empty state — all in a single HTML file without frameworks.

**Architecture:** Additive changes to existing prototype. New elements (drawer, settings modal) are appended to `<body>`. JS state tracked via two variables: `activeProductIndex` (null or integer) and `drawerOpen` (boolean). All new JS functions added to the existing `<script>` block.

**Tech Stack:** HTML5, CSS3 (custom properties already defined), Vanilla JS ES6+, Inline SVG (no libraries)

---

## File Structure

```
reverens/price-parser.html   ← single file, all changes here
  CSS additions (~150 lines):
    - .drawer, .drawer.open, .drawer-overlay
    - .settings-modal, .settings-modal.active
    - tr.active-row (left border accent)
    - .empty-state
  HTML additions:
    - #productDrawer  (after </div> closing .layout)
    - #settingsModal  (after #productDrawer)
    - Add ⚙ button to .header-actions
    - Add "Название" field to #modalOverlay form
  JS additions (~120 lines):
    - openDrawer(index), closeDrawer()
    - renderChart(priceHistory)
    - openSettings(), closeSettings()
    - saveSettings(), loadSettings()
    - Update renderTable() — active row, empty state, clickable rows
    - Update addProduct() — use name field, push to products array
```

---

## Inline Test Helper

Add this to the `<script>` block once at the start of implementation. Used in each task's verify step via browser DevTools console.

```js
function assert(condition, msg) {
  if (!condition) console.error('FAIL:', msg);
  else console.log('PASS:', msg);
}
```

---

## Task 1: Active table row + empty state + target price column

**Files:**
- Modify: `reverens/price-parser.html` — CSS section, `renderTable()` function, table `<thead>`

- [ ] **Step 1: Add `assert` helper + CSS for active row and empty state**

  In the `<style>` block, append:
  ```css
  /* Active row */
  tbody tr.active-row {
    border-left: 2px solid var(--accent);
    background: rgba(108, 92, 231, 0.06);
  }

  /* Empty state */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    color: var(--text2);
    gap: 12px;
  }
  .empty-state svg { opacity: 0.3; }
  .empty-state p { font-size: 14px; }
  ```

  In `<script>`, add at the top:
  ```js
  function assert(condition, msg) {
    if (!condition) console.error('FAIL:', msg);
    else console.log('PASS:', msg);
  }

  let activeProductIndex = null;
  let drawerOpen = false;
  ```

- [ ] **Step 2: Add "Целевая цена" to mock data and thead**

  Each product in the `products` array already has `minPrice`. Add `targetPrice` field:
  ```js
  // For each product object, add:
  targetPrice: Math.round(p.minPrice * 0.95),  // 5% below min as default target
  ```
  Do this by adding `targetPrice` to each object in the array (set it to `minPrice - Math.round(minPrice * 0.05)`).

  Update `<thead>`:
  ```html
  <tr>
    <th>Товар</th>
    <th>Магазин</th>
    <th>Текущая цена</th>
    <th>Целевая цена</th>
    <th>Изменение</th>
    <th>Проверка</th>
    <th></th>
  </tr>
  ```

- [ ] **Step 3: Update `renderTable()` — clickable rows, active state, empty state, target price column**

  Replace the `tbody.innerHTML = filtered.map(...)` template literal's `<tr>` opening tag and add `targetPrice` column:

  ```js
  function renderTable(filter = '') {
    const tbody = document.getElementById('tableBody');
    const filtered = products.filter(p => {
      const matchStore = currentStore === 'all' || p.storeKey === currentStore;
      const matchSearch = !filter || p.name.toLowerCase().includes(filter) || p.sku.toLowerCase().includes(filter);
      return matchStore && matchSearch;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `
        <tr><td colspan="7">
          <div class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <p>Нет товаров. <button class="btn btn-primary btn-sm" onclick="openModal()" style="margin-left:8px">Добавить первый</button></p>
          </div>
        </td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map((p, i) => {
      const idx = products.indexOf(p);
      const changeClass = p.change < 0 ? 'down' : p.change > 0 ? 'up' : 'same';
      const changeText = p.change < 0 ? `${p.change}%` : p.change > 0 ? `+${p.change}%` : '0%';
      const arrow = p.change < 0 ? '&#9660; ' : p.change > 0 ? '&#9650; ' : '';
      const isActive = idx === activeProductIndex;

      return `<tr class="${isActive ? 'active-row' : ''}" onclick="openDrawer(${idx})" style="cursor:pointer">
        <td>
          <div class="product-cell">
            <div class="product-img">${p.emoji}</div>
            <div class="product-info">
              <span class="product-title">${p.name}</span>
              <span class="product-sku">${p.sku}</span>
            </div>
          </div>
        </td>
        <td><span class="store-tag" style="color:${p.color};border:1px solid ${p.color}33;background:${p.color}15">${p.store}</span></td>
        <td><span class="price">${formatPrice(p.price)}</span>${p.oldPrice !== p.price ? `<span class="price-old">${formatPrice(p.oldPrice)}</span>` : ''}</td>
        <td style="color:var(--text2);font-family:monospace">${formatPrice(p.targetPrice)}</td>
        <td><span class="change-badge ${changeClass}">${arrow}${changeText}</span></td>
        <td><span class="last-check">${p.time} назад</span></td>
        <td>
          <div class="row-actions" onclick="event.stopPropagation()">
            <button class="icon-btn" title="Удалить" onclick="deleteProduct(${idx})">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </td>
      </tr>`;
    }).join('');
  }

  function deleteProduct(idx) {
    products.splice(idx, 1);
    if (activeProductIndex === idx) closeDrawer();
    renderTable(document.getElementById('searchInput').value.toLowerCase());
    showToast('Товар удалён');
  }
  ```

- [ ] **Step 4: Verify in browser**

  Open `reverens/price-parser.html` in browser. In DevTools console run:
  ```js
  assert(document.querySelector('thead th:nth-child(4)').textContent === 'Целевая цена', 'Column "Целевая цена" exists');
  assert(document.querySelector('tbody tr') !== null, 'Table has rows');
  assert(document.querySelector('tbody tr').style.cursor === 'pointer' || getComputedStyle(document.querySelector('tbody tr')).cursor === 'pointer', 'Rows are clickable');
  ```
  Expected: 3× PASS

  Also manually: delete search input value, type something that matches nothing → empty state should appear.

- [ ] **Step 5: Commit**
  ```bash
  git add reverens/price-parser.html
  git commit -m "feat: clickable table rows, active state, empty state, target price column"
  ```

---

## Task 2: Drawer HTML + CSS

**Files:**
- Modify: `reverens/price-parser.html` — `<style>` block, HTML after `.layout`

- [ ] **Step 1: Add drawer CSS**

  In `<style>` block, append:
  ```css
  /* Drawer */
  .drawer-overlay {
    position: fixed;
    inset: 0;
    z-index: 50;
    pointer-events: none;
  }
  .drawer-overlay.open { pointer-events: auto; }

  .drawer {
    position: fixed;
    top: 61px; /* header height */
    right: 0;
    width: 380px;
    height: calc(100vh - 61px);
    background: var(--surface);
    border-left: 1px solid var(--accent);
    display: flex;
    flex-direction: column;
    transform: translateX(100%);
    transition: transform 0.2s ease-out;
    z-index: 51;
    overflow-y: auto;
  }

  .drawer.open { transform: translateX(0); }

  .drawer-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-shrink: 0;
  }

  .drawer-title { font-size: 15px; font-weight: 700; margin-bottom: 3px; }
  .drawer-subtitle { font-size: 11px; color: var(--text2); font-family: monospace; }

  .drawer-close {
    width: 26px; height: 26px;
    border: 1px solid var(--border);
    border-radius: 5px;
    background: none;
    color: var(--text2);
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
    transition: all 0.15s;
  }
  .drawer-close:hover { background: var(--surface2); color: var(--text); }

  .drawer-price-block {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }

  .drawer-price { font-size: 26px; font-weight: 700; font-family: monospace; }
  .drawer-delta { text-align: right; }
  .drawer-delta-value { font-size: 15px; font-weight: 700; font-family: monospace; }
  .drawer-delta-pct { font-size: 11px; margin-top: 2px; }

  .drawer-section {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .drawer-section-label {
    font-size: 9px;
    color: var(--text2);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-family: monospace;
    margin-bottom: 10px;
  }

  .chart-svg { width: 100%; height: 120px; display: block; }

  .chart-x-labels {
    display: flex;
    justify-content: space-between;
    font-size: 9px;
    color: var(--text2);
    font-family: monospace;
    margin-top: 4px;
  }

  .store-price-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 10px;
    border-radius: 6px;
    margin-bottom: 4px;
    border: 1px solid var(--border);
    background: var(--surface2);
    font-size: 12px;
  }

  .store-price-row.best {
    background: rgba(108,92,231,0.08);
    border-color: rgba(108,92,231,0.4);
  }

  .store-price-row.best .store-price-val { color: var(--green); font-weight: 700; }
  .store-price-name { color: var(--text2); }
  .store-price-row.best .store-price-name { color: var(--text); font-weight: 600; }
  .store-price-val { font-family: monospace; font-weight: 600; }

  .drawer-actions {
    padding: 12px 20px;
    display: flex;
    gap: 8px;
    border-top: 1px solid var(--border);
    margin-top: auto;
    flex-shrink: 0;
  }
  ```

- [ ] **Step 2: Add drawer HTML after closing `</div>` of `.layout`**

  Locate `</div>` that closes `.layout` (after `</main>`), then add:
  ```html
  <!-- Product Drawer -->
  <div class="drawer" id="productDrawer">
    <div class="drawer-header">
      <div>
        <div class="drawer-title" id="drawerTitle">—</div>
        <div class="drawer-subtitle" id="drawerSubtitle">—</div>
      </div>
      <button class="drawer-close" onclick="closeDrawer()">✕</button>
    </div>

    <div class="drawer-price-block">
      <div>
        <div style="font-size:11px;color:var(--text2);margin-bottom:4px;">Текущая цена</div>
        <div class="drawer-price" id="drawerPrice">—</div>
      </div>
      <div class="drawer-delta" id="drawerDelta">
        <div class="drawer-delta-value" id="drawerDeltaValue">—</div>
        <div class="drawer-delta-pct" id="drawerDeltaPct">—</div>
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-label">История цен</div>
      <svg class="chart-svg" id="drawerChart" viewBox="0 0 340 120" preserveAspectRatio="none">
        <defs>
          <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#6c5ce7" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="#6c5ce7" stop-opacity="0"/>
          </linearGradient>
        </defs>
      </svg>
      <div class="chart-x-labels">
        <span>−30 дн</span><span>−14 дн</span><span>−7 дн</span><span>Сейчас</span>
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-label">Цены по магазинам</div>
      <div id="drawerStorePrices"></div>
    </div>

    <div class="drawer-actions">
      <button class="btn btn-secondary btn-sm" style="flex:1" onclick="showToast('Открытие страницы товара')">↗ Открыть</button>
      <button class="btn btn-secondary btn-sm" style="flex:1" onclick="showToast('Редактирование товара')">✎ Изменить</button>
      <button class="btn btn-secondary btn-sm" style="color:var(--red)" onclick="activeProductIndex !== null && deleteProduct(activeProductIndex)">✕</button>
    </div>
  </div>
  ```

- [ ] **Step 3: Verify structure in browser**

  Open file in browser. In console:
  ```js
  assert(document.getElementById('productDrawer') !== null, 'Drawer element exists');
  assert(!document.getElementById('productDrawer').classList.contains('open'), 'Drawer starts closed');
  assert(getComputedStyle(document.getElementById('productDrawer')).transform.includes('matrix'), 'Drawer has transform');
  ```
  Expected: 3× PASS

- [ ] **Step 4: Commit**
  ```bash
  git add reverens/price-parser.html
  git commit -m "feat: add product drawer HTML and CSS"
  ```

---

## Task 3: Drawer JS — open/close + data population

**Files:**
- Modify: `reverens/price-parser.html` — `<script>` block

- [ ] **Step 1: Add mock price history data**

  In the `<script>` block, after the `products` array, add:
  ```js
  // Mock price history: 30 data points per product (last 30 days)
  function generateMockHistory(currentPrice) {
    const points = [];
    let price = Math.round(currentPrice * 1.08); // start 8% higher
    for (let i = 0; i < 30; i++) {
      const delta = (Math.random() - 0.55) * 0.03; // slight downward trend
      price = Math.round(price * (1 + delta));
      points.push(price);
    }
    points[29] = currentPrice; // end at current
    return points;
  }
  ```

- [ ] **Step 2: Add `renderChart(svgEl, priceHistory)` function**

  ```js
  function renderChart(svgEl, priceHistory) {
    const W = 340, H = 120, PAD = 8;
    const min = Math.min(...priceHistory) - PAD;
    const max = Math.max(...priceHistory) + PAD;
    const xs = priceHistory.map((_, i) => (i / (priceHistory.length - 1)) * W);
    const ys = priceHistory.map(v => H - ((v - min) / (max - min)) * H);

    const linePoints = xs.map((x, i) => `${x},${ys[i]}`).join(' ');
    const areaPoints = `${xs[0]},${H} ` + linePoints + ` ${xs[xs.length-1]},${H}`;

    svgEl.innerHTML = `
      <defs>
        <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#6c5ce7" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="#6c5ce7" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <polyline points="${areaPoints}" fill="url(#chartGrad)" stroke="none"/>
      <polyline points="${linePoints}" fill="none" stroke="#6c5ce7" stroke-width="1.5" stroke-linejoin="round"/>
      <circle cx="${xs[xs.length-1]}" cy="${ys[ys.length-1]}" r="3" fill="#6c5ce7"/>
    `;
  }
  ```

- [ ] **Step 3: Add `openDrawer(idx)` and `closeDrawer()`**

  ```js
  const STORE_PRICES = {
    wb:     { name: 'Wildberries', mult: 1.00 },
    ozon:   { name: 'Ozon',        mult: 1.05 },
    ym:     { name: 'Яндекс Маркет', mult: 1.07 },
    dns:    { name: 'DNS',         mult: 1.03 },
    mvideo: { name: 'МВидео',      mult: 1.09 },
  };

  function openDrawer(idx) {
    const p = products[idx];
    activeProductIndex = idx;
    drawerOpen = true;

    // Header
    document.getElementById('drawerTitle').textContent = p.name;
    document.getElementById('drawerSubtitle').textContent = `${p.sku} · ${p.store}`;

    // Price block
    document.getElementById('drawerPrice').textContent = formatPrice(p.price);
    const deltaRub = p.price - p.oldPrice;
    const sign = deltaRub <= 0 ? '▼' : '▲';
    const color = deltaRub <= 0 ? 'var(--green)' : 'var(--red)';
    const deltaVal = document.getElementById('drawerDeltaValue');
    const deltaPct = document.getElementById('drawerDeltaPct');
    deltaVal.textContent = `${sign} ${Math.abs(deltaRub).toLocaleString('ru')} ₽`;
    deltaVal.style.color = color;
    deltaPct.textContent = `${p.change}% за 7 дней`;
    deltaPct.style.color = color;

    // Chart
    const history = generateMockHistory(p.price);
    renderChart(document.getElementById('drawerChart'), history);

    // Store prices
    const storesHtml = Object.entries(STORE_PRICES).map(([key, s]) => {
      const storePrice = Math.round(p.price * s.mult);
      const isBest = key === p.storeKey;
      return `<div class="store-price-row ${isBest ? 'best' : ''}">
        <span class="store-price-name">${s.name}</span>
        <span class="store-price-val">${formatPrice(storePrice)}</span>
      </div>`;
    }).join('');
    document.getElementById('drawerStorePrices').innerHTML = storesHtml;

    // Open
    document.getElementById('productDrawer').classList.add('open');
    renderTable(document.getElementById('searchInput').value.toLowerCase());
  }

  function closeDrawer() {
    activeProductIndex = null;
    drawerOpen = false;
    document.getElementById('productDrawer').classList.remove('open');
    renderTable(document.getElementById('searchInput').value.toLowerCase());
  }
  ```

- [ ] **Step 4: Verify in browser**

  Open file. In console:
  ```js
  // Open drawer for first product
  openDrawer(0);
  assert(document.getElementById('productDrawer').classList.contains('open'), 'Drawer opens');
  assert(document.getElementById('drawerTitle').textContent === products[0].name, 'Drawer shows correct product name');
  assert(document.getElementById('drawerChart').querySelector('polyline') !== null, 'Chart rendered');

  // Close
  closeDrawer();
  assert(!document.getElementById('productDrawer').classList.contains('open'), 'Drawer closes');
  assert(activeProductIndex === null, 'Active index cleared');
  ```
  Expected: 5× PASS

  Manual: click table row → drawer slides in from right, shows product data and chart.

- [ ] **Step 5: Commit**
  ```bash
  git add reverens/price-parser.html
  git commit -m "feat: drawer open/close, SVG chart, store price comparison"
  ```

---

## Task 4: Settings modal HTML + CSS + JS

**Files:**
- Modify: `reverens/price-parser.html` — `<style>`, HTML after drawer, `<script>`

- [ ] **Step 1: Add settings modal CSS**

  In `<style>`, append:
  ```css
  /* Settings modal */
  .settings-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    backdrop-filter: blur(4px);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 200;
  }
  .settings-overlay.active { display: flex; }

  .settings-modal {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    width: 480px;
    max-width: 90vw;
    overflow: hidden;
  }

  .settings-modal-header {
    padding: 18px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .settings-modal-title { font-size: 15px; font-weight: 700; }
  .settings-modal-subtitle { font-size: 11px; color: var(--text2); font-family: monospace; margin-top: 2px; }

  .settings-section {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
  }

  .settings-section-label {
    font-size: 9px;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-family: monospace;
    margin-bottom: 14px;
  }

  .settings-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .settings-row:last-child { margin-bottom: 0; }

  .settings-row-label { font-size: 13px; font-weight: 500; }
  .settings-row-hint { font-size: 11px; color: var(--text2); margin-top: 2px; }

  .pill-group { display: flex; gap: 4px; }
  .pill {
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-family: monospace;
    border: 1px solid var(--border);
    background: var(--surface2);
    color: var(--text2);
    cursor: pointer;
    transition: all 0.15s;
  }
  .pill.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }

  .toggle {
    width: 40px; height: 22px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 11px;
    position: relative;
    cursor: pointer;
    transition: background 0.2s;
    flex-shrink: 0;
  }
  .toggle.on { background: var(--accent); border-color: var(--accent); }
  .toggle::after {
    content: '';
    position: absolute;
    width: 16px; height: 16px;
    background: #fff;
    border-radius: 50%;
    top: 2px; left: 2px;
    transition: transform 0.2s;
  }
  .toggle.on::after { transform: translateX(18px); }

  .settings-footer {
    padding: 14px 24px;
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
  ```

- [ ] **Step 2: Add settings modal HTML after drawer HTML**

  ```html
  <!-- Settings Modal -->
  <div class="settings-overlay" id="settingsOverlay" onclick="closeSettingsOnOverlay(event)">
    <div class="settings-modal" onclick="event.stopPropagation()">

      <div class="settings-modal-header">
        <div>
          <div class="settings-modal-title">Настройки</div>
          <div class="settings-modal-subtitle">Конфигурация парсера</div>
        </div>
        <button class="drawer-close" onclick="closeSettings()">✕</button>
      </div>

      <!-- Section: Парсинг -->
      <div class="settings-section">
        <div class="settings-section-label">Парсинг</div>

        <div class="settings-row">
          <div>
            <div class="settings-row-label">Интервал обновления</div>
            <div class="settings-row-hint">Как часто проверять цены</div>
          </div>
          <div class="pill-group" id="intervalPills">
            <button class="pill active" data-value="30" onclick="selectPill(this, 'intervalPills')">30 мин</button>
            <button class="pill" data-value="60" onclick="selectPill(this, 'intervalPills')">1 ч</button>
            <button class="pill" data-value="360" onclick="selectPill(this, 'intervalPills')">6 ч</button>
            <button class="pill" data-value="1440" onclick="selectPill(this, 'intervalPills')">24 ч</button>
          </div>
        </div>

        <div class="settings-row">
          <div>
            <div class="settings-row-label">Автозапуск парсера</div>
            <div class="settings-row-hint">Запускать по расписанию</div>
          </div>
          <div class="toggle on" id="toggleAutostart" onclick="toggleSetting(this)"></div>
        </div>
      </div>

      <!-- Section: Уведомления -->
      <div class="settings-section">
        <div class="settings-section-label">Уведомления</div>

        <div class="settings-row">
          <div>
            <div class="settings-row-label">Порог снижения цены</div>
            <div class="settings-row-hint">Уведомлять при падении на</div>
          </div>
          <div style="display:flex;align-items:center;gap:6px;">
            <input type="number" id="thresholdInput" min="1" max="99" value="5"
              style="width:52px;padding:5px 8px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:monospace;font-size:13px;text-align:center;outline:none;">
            <span style="font-size:12px;color:var(--text2)">%</span>
          </div>
        </div>

        <div class="settings-row">
          <div>
            <div class="settings-row-label">Push-уведомления</div>
            <div class="settings-row-hint">Подключается на шаге 3</div>
          </div>
          <div class="toggle" id="togglePush" onclick="toggleSetting(this)" style="opacity:0.4;pointer-events:none"></div>
        </div>
      </div>

      <!-- Section: Данные -->
      <div class="settings-section">
        <div class="settings-section-label">Данные</div>

        <div class="settings-row">
          <div>
            <div class="settings-row-label">Хранить историю</div>
            <div class="settings-row-hint">Глубина истории цен</div>
          </div>
          <div class="pill-group" id="historyPills">
            <button class="pill" data-value="7" onclick="selectPill(this, 'historyPills')">7 дн</button>
            <button class="pill active" data-value="30" onclick="selectPill(this, 'historyPills')">30 дн</button>
            <button class="pill" data-value="90" onclick="selectPill(this, 'historyPills')">90 дн</button>
          </div>
        </div>

        <div class="settings-row">
          <div>
            <div class="settings-row-label">Экспорт данных</div>
            <div class="settings-row-hint">Выгрузить все цены в файл</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="showToast('Экспорт CSV — подключается на шаге 4')">CSV ↓</button>
        </div>
      </div>

      <div class="settings-footer">
        <button class="btn btn-secondary" onclick="closeSettings()">Отмена</button>
        <button class="btn btn-primary" onclick="saveSettings()">Сохранить</button>
      </div>
    </div>
  </div>
  ```

- [ ] **Step 3: Add ⚙ button to header**

  In `.header-actions` div, add before the existing status badge:
  ```html
  <button class="icon-btn" onclick="openSettings()" title="Настройки" style="width:36px;height:36px;border:1px solid var(--border);border-radius:8px;">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  </button>
  ```

- [ ] **Step 4: Add settings JS functions**

  ```js
  function openSettings() {
    loadSettings();
    document.getElementById('settingsOverlay').classList.add('active');
  }

  function closeSettings() {
    document.getElementById('settingsOverlay').classList.remove('active');
  }

  function closeSettingsOnOverlay(e) {
    if (e.target === document.getElementById('settingsOverlay')) closeSettings();
  }

  function selectPill(el, groupId) {
    document.querySelectorAll(`#${groupId} .pill`).forEach(p => p.classList.remove('active'));
    el.classList.add('active');
  }

  function toggleSetting(el) {
    el.classList.toggle('on');
  }

  function saveSettings() {
    const interval = document.querySelector('#intervalPills .pill.active')?.dataset.value || '30';
    const autostart = document.getElementById('toggleAutostart').classList.contains('on');
    const threshold = document.getElementById('thresholdInput').value;
    const history = document.querySelector('#historyPills .pill.active')?.dataset.value || '30';

    localStorage.setItem('pp_settings', JSON.stringify({ interval, autostart, threshold, history }));
    closeSettings();
    showToast('Настройки сохранены');
  }

  function loadSettings() {
    const raw = localStorage.getItem('pp_settings');
    if (!raw) return;
    const s = JSON.parse(raw);

    // Interval pills
    document.querySelectorAll('#intervalPills .pill').forEach(p => {
      p.classList.toggle('active', p.dataset.value === s.interval);
    });
    // Autostart toggle
    document.getElementById('toggleAutostart').classList.toggle('on', s.autostart);
    // Threshold
    if (s.threshold) document.getElementById('thresholdInput').value = s.threshold;
    // History pills
    document.querySelectorAll('#historyPills .pill').forEach(p => {
      p.classList.toggle('active', p.dataset.value === s.history);
    });
  }
  ```

- [ ] **Step 5: Verify in browser**

  ```js
  // Open settings
  openSettings();
  assert(document.getElementById('settingsOverlay').classList.contains('active'), 'Settings modal opens');

  // Save and reload
  saveSettings();
  assert(!document.getElementById('settingsOverlay').classList.contains('active'), 'Settings modal closes on save');
  assert(localStorage.getItem('pp_settings') !== null, 'Settings saved to localStorage');

  // Verify load
  const saved = JSON.parse(localStorage.getItem('pp_settings'));
  assert(saved.interval !== undefined, 'Settings have interval');
  assert(saved.threshold !== undefined, 'Settings have threshold');
  ```
  Expected: 5× PASS

  Manual: open settings → change interval to "6 ч" → save → reopen → "6 ч" should still be selected.

- [ ] **Step 6: Commit**
  ```bash
  git add reverens/price-parser.html
  git commit -m "feat: settings modal with localStorage persistence"
  ```

---

## Task 5: Update add product modal + wire up name field

**Files:**
- Modify: `reverens/price-parser.html` — `#modalOverlay` HTML, `addProduct()` function

- [ ] **Step 1: Add "Название" field to modal form**

  In `#modalOverlay`, add before the URL field:
  ```html
  <div class="form-group">
    <label>Название товара <span style="color:var(--red)">*</span></label>
    <input type="text" class="form-input" placeholder="Например: iPhone 15 Pro 256GB" id="nameInput">
  </div>
  ```

- [ ] **Step 2: Update `addProduct()` to use name field and push to array**

  Replace the existing `addProduct()`:
  ```js
  function addProduct() {
    const name = document.getElementById('nameInput').value.trim();
    const url = document.getElementById('urlInput').value.trim();
    const store = document.getElementById('storeSelect').value || 'Wildberries';

    if (!name) {
      showToast('Введите название товара');
      return;
    }

    const storeMap = {
      'Wildberries': { key: 'wb', icon: 'W', color: '#6c5ce7' },
      'Ozon': { key: 'ozon', icon: 'O', color: '#0984e3' },
      'Яндекс Маркет': { key: 'ym', icon: 'Я', color: '#fdcb6e' },
      'DNS': { key: 'dns', icon: 'D', color: '#e17055' },
      'МВидео': { key: 'mvideo', icon: 'M', color: '#00b894' },
    };
    const s = storeMap[store] || storeMap['Wildberries'];
    const mockPrice = Math.round(Math.random() * 50000 + 5000);

    products.push({
      name,
      sku: 'NEW-' + Date.now().toString().slice(-4),
      store,
      storeKey: s.key,
      icon: s.icon,
      color: s.color,
      emoji: '📦',
      price: mockPrice,
      oldPrice: mockPrice,
      minPrice: mockPrice,
      targetPrice: Math.round(mockPrice * 0.9),
      change: 0,
      time: 'только что',
    });

    closeModal();
    renderTable(document.getElementById('searchInput').value.toLowerCase());
    showToast(`"${name}" добавлен в отслеживание`);
    document.getElementById('nameInput').value = '';
    document.getElementById('urlInput').value = '';
  }
  ```

- [ ] **Step 3: Verify**

  ```js
  // Simulate adding product
  document.getElementById('nameInput').value = 'Test Product';
  document.getElementById('storeSelect').value = 'Ozon';
  const countBefore = products.length;
  addProduct();
  assert(products.length === countBefore + 1, 'Product added to array');
  assert(products[products.length - 1].name === 'Test Product', 'Correct name saved');
  assert(products[products.length - 1].storeKey === 'ozon', 'Correct store saved');
  ```
  Expected: 3× PASS

  Manual: click "+ Добавить товар" → fill in name → submit → product appears in table.

- [ ] **Step 4: Commit**
  ```bash
  git add reverens/price-parser.html
  git commit -m "feat: add product modal - name field, pushes to products array"
  ```

---

## Task 6: Final integration + smoke test

**Files:**
- Modify: `reverens/price-parser.html` — `<script>` block init section

- [ ] **Step 1: Load settings on init**

  In the `// Init` section at the bottom of `<script>`, add `loadSettings()`:
  ```js
  // Init
  renderTable();
  loadSettings();
  ```

- [ ] **Step 2: Run full smoke test in browser DevTools**

  Open file. In console:
  ```js
  // 1. Table renders
  assert(document.querySelectorAll('tbody tr').length > 0, '✓ Table has rows');

  // 2. Drawer opens on row click
  document.querySelector('tbody tr').click();
  assert(document.getElementById('productDrawer').classList.contains('open'), '✓ Drawer opens on click');
  assert(document.getElementById('drawerTitle').textContent.length > 0, '✓ Drawer has product name');

  // 3. Chart rendered
  assert(document.getElementById('drawerChart').querySelector('polyline') !== null, '✓ SVG chart rendered');

  // 4. Store prices rendered
  assert(document.getElementById('drawerStorePrices').children.length > 0, '✓ Store prices rendered');

  // 5. Close drawer
  closeDrawer();
  assert(!document.getElementById('productDrawer').classList.contains('open'), '✓ Drawer closes');

  // 6. Settings open/save
  openSettings();
  assert(document.getElementById('settingsOverlay').classList.contains('active'), '✓ Settings modal opens');
  saveSettings();
  assert(localStorage.getItem('pp_settings') !== null, '✓ Settings persisted');

  // 7. Search filter
  document.getElementById('searchInput').value = 'xxxxxxxxxx';
  filterTable();
  assert(document.querySelector('.empty-state') !== null, '✓ Empty state shows on no results');
  document.getElementById('searchInput').value = '';
  filterTable();

  // 8. Add product
  document.getElementById('nameInput').value = 'Smoke Test Product';
  document.getElementById('storeSelect').value = 'DNS';
  const n = products.length;
  addProduct();
  assert(products.length === n + 1, '✓ Product added');

  console.log('--- Smoke test complete ---');
  ```
  Expected: all 9 assertions PASS.

- [ ] **Step 3: Final commit**
  ```bash
  git add reverens/price-parser.html
  git commit -m "feat: init loadSettings, complete price parser frontend MVP

  All spec requirements implemented:
  - Clickable table rows with active state (left accent border)
  - Product detail drawer with SVG price chart and store comparison
  - Settings modal with localStorage persistence
  - Empty state for table
  - Add product modal with name field

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  ```

---

## Done ✓

After Task 6, the frontend is complete per spec. All three states work:
1. List view with clickable rows
2. Drawer detail with chart
3. Settings modal with persistence

Ready for Step 2: backend integration.
