(function(){
  function getCsrf(){ const m=document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
  async function postForm(url, data){
    const body = new URLSearchParams();
    Object.entries(data).forEach(([k,v]) => body.append(k, String(v)));
    body.append('csrf_token', getCsrf());
    const res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8','X-CSRF-Token':getCsrf()}, body});
    let payload = {};
    try { payload = await res.json(); } catch(_e) {}
    if(!res.ok){ throw new Error(payload.message || 'Request failed'); }
    return payload;
  }
  function showToast(msg, isError){
    let root = document.getElementById('toast-root');
    if(!root){ root = document.createElement('div'); root.id='toast-root'; root.style.cssText='position:fixed;top:18px;left:0;right:0;display:flex;flex-direction:column;align-items:center;gap:10px;z-index:120;pointer-events:none;padding:0 16px'; document.body.appendChild(root); }
    const el = document.createElement('div');
    el.className='flash' + (isError ? ' error' : '');
    el.style.maxWidth='520px';
    el.style.width='100%';
    el.textContent=msg;
    root.appendChild(el);
    setTimeout(()=>el.remove(), 3000);
  }

  let activeDishPayload = null;

  function renderCartLists(state){
    const items = state.cart_items || [];
    const html = items.length ? items.map(item => `
      <div class="cart-item">
        <div class="emoji-bubble" style="width:46px;height:46px;flex-basis:46px;font-size:1.35rem">${item.emoji || '🍽️'}</div>
        <div style="flex:1">
          <div class="badge badge-ice">${item.day}</div>
          <div style="color:#fff;margin-top:6px"><strong>${item.dish_name}</strong></div>
          <div class="muted small">${item.price_text}</div>
        </div>
      </div>
    `).join('') : '<div class="muted">Košík je zatím prázdný.</div>';
    document.querySelectorAll('[data-cart-list-mobile],[data-cart-list-desktop]').forEach(el => { el.innerHTML = html; });
  }

  function updateDayTabStates(state){
    const statusByDay = (state && state.day_status_by_day) || {};
    document.querySelectorAll('[data-day-link]').forEach(link => {
      const day = link.dataset.dayLink;
      const stateName = statusByDay[day] || 'none';
      link.dataset.orderState = stateName;
      link.classList.remove('day-tab-state-none', 'day-tab-state-selected', 'day-tab-state-paid');
      link.classList.add(`day-tab-state-${stateName}`);
    });
  }

  function syncDayRail(){
    const sections = Array.from(document.querySelectorAll('[data-day-section]'));
    if(!sections.length) return;
    let activeDay = sections[0].dataset.daySection;
    const topOffset = window.innerWidth <= 900 ? 170 : 120;
    sections.forEach(section => {
      const rect = section.getBoundingClientRect();
      if(rect.top - topOffset <= 0 && rect.bottom > topOffset){ activeDay = section.dataset.daySection; }
    });
    document.querySelectorAll('[data-day-link]').forEach(link => {
      link.classList.toggle('active', link.dataset.dayLink === activeDay);
    });
  }

  function setAccordionState(day, shouldOpen){
    const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
    if(!section) return;
    section.classList.toggle('is-open', shouldOpen);
    const button = section.querySelector('[data-day-toggle]');
    if(button) button.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
    const content = section.querySelector('[data-day-content]');
    if(content) content.hidden = !shouldOpen;
  }

  function openDaySection(day){
    const mobile = window.innerWidth <= 900;
    document.querySelectorAll('[data-day-section]').forEach(section => {
      const isTarget = section.dataset.daySection === day;
      if(mobile){
        setAccordionState(section.dataset.daySection, isTarget);
      } else if(isTarget) {
        setAccordionState(section.dataset.daySection, true);
      }
    });
  }

  function setupDayAccordion(){
    document.querySelectorAll('[data-day-section]').forEach(section => {
      const isOpen = section.classList.contains('is-open');
      const content = section.querySelector('[data-day-content]');
      if(content) content.hidden = !isOpen;
    });
    document.querySelectorAll('[data-day-toggle]').forEach(btn => {
      btn.addEventListener('click', () => {
        const day = btn.dataset.dayToggle;
        const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
        const nextState = !(section && section.classList.contains('is-open'));
        if(window.innerWidth <= 900){
          document.querySelectorAll('[data-day-section]').forEach(s => setAccordionState(s.dataset.daySection, false));
        }
        setAccordionState(day, nextState);
        syncDayRail();
      });
    });
    document.querySelectorAll('[data-day-link]').forEach(link => {
      link.addEventListener('click', (e) => {
        const day = link.dataset.dayLink;
        openDaySection(day);
        const section = document.getElementById(`day-${day}`);
        if(section){
          e.preventDefault();
          section.scrollIntoView({behavior:'smooth', block:'start'});
          history.replaceState(null, '', `#day-${encodeURIComponent(day)}`);
        }
      });
    });
  }

  function setSmartCartExpanded(expanded){
    const cart = document.querySelector('[data-smart-cart]');
    const toggle = document.querySelector('[data-smart-cart-toggle]');
    if(!cart || !toggle) return;
    cart.classList.toggle('is-expanded', expanded);
    toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }

  function setupMobileNavCollapse(){
    if(document.body.dataset.activePage !== 'menu') return;
    let lastY = window.scrollY;
    window.addEventListener('scroll', () => {
      if(window.innerWidth > 900) {
        document.body.classList.remove('mobile-nav-collapsed');
        return;
      }
      const currentY = window.scrollY;
      if(currentY > 140 && currentY > lastY + 12) {
        document.body.classList.add('mobile-nav-collapsed');
      } else if(currentY < lastY - 10 || currentY < 80) {
        document.body.classList.remove('mobile-nav-collapsed');
      }
      lastY = currentY;
    }, {passive:true});
  }

  function setupSmartCart(){
    const toggle = document.querySelector('[data-smart-cart-toggle]');
    if(!toggle) return;
    toggle.addEventListener('click', () => {
      const cart = document.querySelector('[data-smart-cart]');
      setSmartCartExpanded(!(cart && cart.classList.contains('is-expanded')));
    });
    let lastY = window.scrollY;
    window.addEventListener('scroll', () => {
      const cart = document.querySelector('[data-smart-cart]');
      if(!cart || window.innerWidth > 900) return;
      const currentY = window.scrollY;
      if(currentY > lastY + 24 && cart.classList.contains('is-expanded')) {
        setSmartCartExpanded(false);
      }
      lastY = currentY;
    }, {passive:true});
  }

  function parseDishPayload(el){
    const card = el.closest('.dish-card');
    if(!card) return null;
    try { return JSON.parse(card.dataset.dishPayload || '{}'); } catch(_e) { return null; }
  }

  function renderDishModal(payload){
    if(!payload) return;
    activeDishPayload = payload;
    const modal = document.querySelector('[data-dish-modal]');
    if(!modal) return;
    modal.hidden = false;
    document.body.classList.add('modal-open');
    const setText = (sel, value) => { const el = document.querySelector(sel); if(el) el.textContent = value || ''; };
    setText('[data-modal-emoji]', payload.emoji || '🍽️');
    setText('[data-modal-name]', payload.dish_name || 'Detail jídla');
    setText('[data-modal-day]', `${payload.day || ''} · ${payload.price_text || ''}`);
    setText('[data-modal-price]', payload.price_text || '0 Kč');

    const badges = document.querySelector('[data-modal-badges]');
    if(badges){
      const parts = [];
      if(payload.selected) parts.push('<span class="badge badge-gold">Vybráno</span>');
      if(payload.recommended) parts.push('<span class="badge badge-gold">⭐ Doporučeno</span>');
      if(!payload.safe) parts.push('<span class="badge badge-red">⚠️ Obsahuje alergen</span>');
      if(payload.popularity) parts.push(`<span class="badge badge-blue">🔥 ${payload.popularity}× objednáno</span>`);
      if(payload.thumbs) parts.push(`<span class="badge badge-gold">👍 ${payload.thumbs} hodnocení</span>`);
      if(payload.manual) parts.push('<span class="badge badge-ice">Manuální položka</span>');
      badges.innerHTML = parts.join('');
    }

    const allergensWrap = document.querySelector('[data-modal-allergens]');
    if(allergensWrap){
      const allergens = payload.allergen_numbers || [];
      if(allergens.length){
        allergensWrap.innerHTML = allergens.map(a => `<span class="badge badge-red">Alergen ${a}</span>`).join('');
      } else {
        allergensWrap.innerHTML = '<span class="badge badge-green">Bez uvedených alergenů</span>';
      }
    }

    const desc = [];
    desc.push(payload.selected ? 'Tohle jídlo máš aktuálně vybrané pro daný den.' : 'Kliknutím můžeš jídlo vybrat pro daný den.');
    if(payload.continued_lines && payload.continued_lines.length){ desc.push(`Název byl složen z ${payload.continued_lines.length + 1} řádků PDF.`); }
    setText('[data-modal-description]', desc.join(' '));

    const srcWrap = document.querySelector('[data-modal-source-wrap]');
    if(srcWrap){
      const visible = payload.source_line !== undefined && payload.source_line !== null && payload.source_line !== '';
      srcWrap.classList.toggle('hidden', !visible);
      setText('[data-modal-source-line]', visible ? String(payload.source_line) : '');
    }
    setText('[data-modal-recommendation]', payload.recommended ? 'Doporučení: odpovídá tvé historii objednávek.' : 'Doporučení: neutrální položka bez zvláštní preference.');
    setText('[data-modal-popularity]', payload.popularity ? `Popularita: ${payload.popularity} aktivních objednávek.` : 'Popularita: zatím bez aktivních objednávek.');
    setText('[data-modal-safe]', payload.safe ? 'Alergie: položka neobsahuje žádný z tvých nastavených alergenů.' : 'Alergie: zkontroluj si uvedené alergeny před potvrzením.');

    const selectBtn = document.querySelector('[data-modal-select]');
    const cancelBtn = document.querySelector('[data-modal-cancel]');
    const rateBtn = document.querySelector('[data-modal-rate]');
    if(selectBtn){
      selectBtn.disabled = !!payload.selected;
      selectBtn.textContent = payload.selected ? 'Vybráno ✅' : 'Vybrat jídlo';
    }
    if(cancelBtn){ cancelBtn.disabled = !payload.selected; }
    if(rateBtn){
      rateBtn.disabled = !!payload.rated;
      rateBtn.textContent = payload.rated ? '👍 Hodnoceno' : '👍 Ohodnotit';
      rateBtn.classList.toggle('btn-gold', !!payload.rated);
      rateBtn.classList.toggle('btn-ghost', !payload.rated);
    }
  }

  function closeDishModal(){
    const modal = document.querySelector('[data-dish-modal]');
    if(!modal) return;
    modal.hidden = true;
    document.body.classList.remove('modal-open');
    activeDishPayload = null;
  }

  function updateSelectionVisuals(state){
    if(!state) return;
    document.querySelectorAll('.dish-card').forEach(card => {
      const day = card.dataset.day;
      const dishId = Number(card.dataset.dishId);
      const selected = Number((state.selected_by_day || {})[day] || 0) === dishId;
      card.classList.toggle('selected', selected);
      const status = card.querySelector('[data-card-status]');
      if(status){ status.textContent = selected ? 'Vybráno' : 'K dispozici'; status.className = 'badge ' + (selected ? 'badge-gold' : 'badge-blue'); }
      const slot = card.querySelector('[data-action-slot]');
      if(slot){
        if(selected){
          slot.innerHTML = `<button class="btn-gold label" type="button">Vybráno ✅</button><button class="btn-ghost label" type="button" data-cancel-day="${day}">Zrušit ✕</button><button class="btn-ghost label" type="button" data-open-dish-modal="1">Detail</button>`;
        } else {
          slot.innerHTML = `<button class="btn-blue label" type="button" data-select-day="${day}" data-select-dish-id="${dishId}">Vybrat jídlo</button><button class="btn-ghost label" type="button" data-open-dish-modal="1">Detail</button>`;
        }
      }
      try {
        const payload = JSON.parse(card.dataset.dishPayload || '{}');
        payload.selected = selected;
        card.dataset.dishPayload = JSON.stringify(payload);
      } catch(_e) {}
    });
    document.querySelectorAll('[data-cart-count]').forEach(el => el.textContent = state.cart_count || 0);
    document.querySelectorAll('[data-cart-total]').forEach(el => el.textContent = state.cart_total_text || '0 Kč');
    const bar = document.querySelector('[data-week-progress-fill]');
    if(bar){
      const days = (state.menu_days || []).length || 1;
      const pct = Math.round(((state.cart_count || 0) / days) * 100);
      bar.style.width = pct + '%';
    }
    renderCartLists(state);
    updateDayTabStates(state);
    const cart = document.querySelector('[data-smart-cart]');
    if(cart){
      cart.classList.toggle('has-items', (state.cart_count || 0) > 0);
      if((state.cart_count || 0) > 0 && window.innerWidth <= 900){
        setSmartCartExpanded(true);
        setTimeout(() => setSmartCartExpanded(false), 2200);
      }
    }
    if(activeDishPayload){
      const liveCard = document.querySelector(`.dish-card[data-day="${CSS.escape(activeDishPayload.day)}"][data-dish-id="${activeDishPayload.id}"]`);
      if(liveCard){
        renderDishModal(parseDishPayload(liveCard));
      }
    }
  }

  async function selectDish(day, dishId){
    try {
      const payload = await postForm('/order-api', {day, dish_id:dishId});
      updateSelectionVisuals(payload.state);
      openDaySection(day);
      showToast(payload.message || 'Dish selected.');
    } catch(err){ showToast(err.message, true); }
  }
  async function cancelDish(day){
    try {
      const payload = await postForm('/order-api/cancel', {day});
      updateSelectionVisuals(payload.state);
      showToast(payload.message || 'Order cancelled.');
    } catch(err){ showToast(err.message, true); }
  }
  async function rateDish(dishName, btn){
    try {
      const payload = await postForm('/order-api/rate', {dish_name:dishName});
      if(btn){
        btn.disabled = true;
        btn.textContent = '👍 Hodnoceno';
        btn.classList.remove('btn-ghost');
        btn.classList.add('btn-gold');
      }
      document.querySelectorAll(`[data-rate-dish="${CSS.escape(dishName)}"]`).forEach(node => {
        node.disabled = true;
        node.textContent = '👍 Hodnoceno';
        node.classList.remove('btn-ghost');
        node.classList.add('btn-gold');
      });
      if(activeDishPayload && activeDishPayload.dish_name === dishName){
        activeDishPayload.rated = true;
        renderDishModal(activeDishPayload);
      }
      showToast(payload.message || 'Děkujeme za hodnocení.');
    } catch(err){ showToast(err.message, true); }
  }

  function applyFilters(){
    const term = (document.getElementById('menu-search')?.value || '').trim().toLowerCase();
    const selectedOnly = document.getElementById('filter-selected')?.classList.contains('active');
    const recommendedOnly = document.getElementById('filter-recommended')?.classList.contains('active');
    const safeOnly = document.getElementById('filter-safe')?.classList.contains('active');
    const popularOnly = document.getElementById('filter-popular')?.classList.contains('active');
    let visibleCount = 0;
    document.querySelectorAll('.dish-card').forEach(card => {
      const matchesTerm = !term || (card.dataset.search || '').includes(term);
      const matchesSelected = !selectedOnly || card.classList.contains('selected');
      const matchesRecommended = !recommendedOnly || card.dataset.recommended === '1';
      const matchesSafe = !safeOnly || card.dataset.safe === '1';
      const matchesPopular = !popularOnly || Number(card.dataset.popularity || '0') > 0;
      const visible = matchesTerm && matchesSelected && matchesRecommended && matchesSafe && matchesPopular;
      card.classList.toggle('hidden', !visible);
      if(visible) visibleCount++;
    });
    const empty = document.getElementById('menu-empty-state');
    if(empty) empty.classList.toggle('hidden', visibleCount !== 0);
  }

  function setMenuToolsOpen(open){
    const panel = document.querySelector('[data-menu-tools-panel]');
    const toggle = document.querySelector('[data-menu-tools-toggle]');
    if(!panel || !toggle) return;
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    document.body.classList.toggle('menu-tools-open', open);
    if(open){
      const input = document.getElementById('menu-search');
      if(input && window.innerWidth > 900) setTimeout(() => input.focus(), 40);
    }
  }

  function setupMenuTools(){
    const root = document.querySelector('[data-menu-tools]');
    const toggle = document.querySelector('[data-menu-tools-toggle]');
    if(!root || !toggle) return;
    toggle.addEventListener('click', () => {
      const panel = document.querySelector('[data-menu-tools-panel]');
      setMenuToolsOpen(!!panel && panel.hidden);
    });
    document.querySelectorAll('[data-menu-tools-close]').forEach(btn => btn.addEventListener('click', () => setMenuToolsOpen(false)));
    document.addEventListener('click', (event) => {
      if(!document.body.classList.contains('menu-tools-open')) return;
      if(root.contains(event.target)) return;
      setMenuToolsOpen(false);
    });
    document.addEventListener('keydown', (event) => {
      if(event.key === 'Escape') setMenuToolsOpen(false);
    });
  }

  function setupAdminTabs(){
    document.querySelectorAll('[data-tab-button]').forEach(btn => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.tabButton;
        document.querySelectorAll('[data-tab-button]').forEach(item => item.classList.toggle('active', item === btn));
        document.querySelectorAll('[data-tab-panel]').forEach(panel => panel.classList.toggle('active', panel.dataset.tabPanel === target));
      });
    });
  }

  function setupDishModal(){
    document.addEventListener('click', (event) => {
      const closeBtn = event.target.closest('[data-close-dish-modal]');
      if(closeBtn){ closeDishModal(); return; }
      const openTrigger = event.target.closest('[data-open-dish-modal]');
      if(openTrigger){
        const payload = parseDishPayload(openTrigger);
        if(payload){ renderDishModal(payload); }
        return;
      }
      const selectBtn = event.target.closest('[data-modal-select]');
      if(selectBtn && activeDishPayload){ selectDish(activeDishPayload.day, activeDishPayload.id); return; }
      const cancelBtn = event.target.closest('[data-modal-cancel]');
      if(cancelBtn && activeDishPayload){ cancelDish(activeDishPayload.day); return; }
      const rateBtn = event.target.closest('[data-modal-rate]');
      if(rateBtn && activeDishPayload){ rateDish(activeDishPayload.dish_name, rateBtn); return; }
    });
    document.addEventListener('keydown', (event) => {
      if(event.key === 'Escape'){ closeDishModal(); }
      if((event.key === 'Enter' || event.key === ' ') && event.target.matches('[data-open-dish-modal]')){
        event.preventDefault();
        const payload = parseDishPayload(event.target);
        if(payload){ renderDishModal(payload); }
      }
    });
  }

  document.addEventListener('click', (event) => {
    const selectBtn = event.target.closest('[data-select-day]');
    if(selectBtn){ selectDish(selectBtn.dataset.selectDay, selectBtn.dataset.selectDishId); return; }
    const cancelBtn = event.target.closest('[data-cancel-day]');
    if(cancelBtn){ cancelDish(cancelBtn.dataset.cancelDay); return; }
    const rateBtn = event.target.closest('[data-rate-dish]');
    if(rateBtn){ rateDish(rateBtn.dataset.rateDish, rateBtn); return; }
    const chip = event.target.closest('[data-filter-chip]');
    if(chip){ chip.classList.toggle('active'); applyFilters(); }
  });

  document.addEventListener('input', (event) => {
    if(event.target.id === 'menu-search'){ applyFilters(); }
  });

  window.addEventListener('resize', () => {
    document.querySelectorAll('[data-day-section]').forEach(section => {
      if(window.innerWidth > 900){ setAccordionState(section.dataset.daySection, true); }
    });
  });
  window.addEventListener('scroll', syncDayRail, {passive:true});
  document.addEventListener('DOMContentLoaded', () => {
    setupDayAccordion();
    setupSmartCart();
    setupMobileNavCollapse();
    setupMenuTools();
    setupAdminTabs();
    setupDishModal();
    applyFilters();
    syncDayRail();
    updateDayTabStates({day_status_by_day: Object.fromEntries(Array.from(document.querySelectorAll('[data-day-link]')).map(link => [link.dataset.dayLink, link.dataset.orderState || 'none']))});
  });
})();


const notifToggle = document.querySelector("[data-notification-toggle]");
const notifPanel = document.querySelector("[data-notification-panel]");
if (notifToggle && notifPanel) {
  notifToggle.addEventListener("click", () => {
    const isOpen = notifPanel.classList.toggle("is-open");
    notifToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  });
  document.addEventListener("click", (event) => {
    if (!notifPanel.contains(event.target) && !notifToggle.contains(event.target)) notifPanel.classList.remove("is-open");
  });
}



/* === UX V3 Mobile Command Center === */
(function(){
  const DAYS = ['Neděle','Pondělí','Úterý','Středa','Čtvrtek','Pátek','Sobota'];
  const WORK_DAYS = ['Pondělí','Úterý','Středa','Čtvrtek','Pátek'];

  function isMobile(){
    return window.innerWidth <= 900;
  }

  function currentWorkDay(){
    const today = DAYS[new Date().getDay()];
    return WORK_DAYS.includes(today) ? today : 'Pondělí';
  }

  function selectedFromCards(){
    const items = [];
    document.querySelectorAll('.dish-card.selected[data-day]').forEach((card) => {
      let payload = {};
      try { payload = JSON.parse(card.dataset.dishPayload || '{}'); } catch(e) {}
      items.push({
        day: card.dataset.day,
        dish_name: payload.dish_name || (card.querySelector('.dish-name strong') || {}).textContent || 'Vybrané jídlo',
        emoji: payload.emoji || (card.querySelector('.emoji-bubble') || {}).textContent || '🍽️'
      });
    });
    return items;
  }

  function nearestItem(items){
    if (!items.length) return null;
    const today = currentWorkDay();
    const todayItem = items.find(x => x.day === today);
    if (todayItem) return {item: todayItem, label: 'Dnes máš vybráno'};

    const start = WORK_DAYS.indexOf(today);
    const ordered = WORK_DAYS.slice(start).concat(WORK_DAYS.slice(0, start));
    for (const day of ordered) {
      const item = items.find(x => x.day === day);
      if (item) return {item, label: 'Nejbližší objednávka'};
    }
    return {item: items[0], label: 'Vybrané jídlo'};
  }

  function updateWelcome(){
    const title = document.querySelector('[data-v3-today-title]');
    const sub = document.querySelector('[data-v3-today-sub]');
    const emoji = document.querySelector('[data-v3-today-emoji]');
    if (!title || !sub || !emoji) return;

    const nearest = nearestItem(selectedFromCards());
    if (!nearest) {
      emoji.textContent = '👋';
      title.textContent = 'Zatím nemáš vybraný oběd';
      sub.textContent = 'Vyber si jídlo pro dnešní nebo nejbližší pracovní den.';
      return;
    }

    emoji.textContent = nearest.item.emoji || '🍽️';
    title.textContent = nearest.item.dish_name || 'Vybrané jídlo';
    sub.textContent = nearest.label + ' · ' + nearest.item.day;
  }

  function updateWeekStrip(){
    const selected = selectedFromCards();

    document.querySelectorAll('[data-v3-day-chip]').forEach((chip) => {
      const day = chip.dataset.v3DayChip;
      const item = selected.find(x => x.day === day);
      const state = chip.querySelector('.v3-day-state');

      chip.classList.toggle('active', !!item);
      chip.classList.toggle('current', day === currentWorkDay());
      if (state) state.textContent = item ? '✓' : '—';
    });
  }

  function updateReview(){
    const selected = selectedFromCards();

    document.querySelectorAll('[data-v3-review-day]').forEach((row) => {
      const day = row.dataset.v3ReviewDay;
      const item = selected.find(x => x.day === day);
      const food = row.querySelector('.v3-review-food');

      row.classList.toggle('active', !!item);
      if (food) food.textContent = item ? `${item.emoji || '🍽️'} ${item.dish_name}` : 'Vybrat jídlo';
    });
  }

  function openDay(day){
    const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);

    if (section) {
      document.querySelectorAll('[data-day-section]').forEach((s) => {
        const isTarget = s === section;
        s.classList.toggle('is-open', isTarget);
        const content = s.querySelector('[data-day-content]');
        const toggle = s.querySelector('[data-day-toggle]');
        if (content) content.hidden = !isTarget;
        if (toggle) toggle.setAttribute('aria-expanded', isTarget ? 'true' : 'false');
      });

      section.scrollIntoView({behavior:'smooth', block:'start'});
    }
  }

  function collapseDays(){
    if (!isMobile()) return;
    document.querySelectorAll('[data-day-section]').forEach((section) => {
      section.classList.remove('is-open');
      const content = section.querySelector('[data-day-content]');
      const toggle = section.querySelector('[data-day-toggle]');
      if (content) content.hidden = true;
      if (toggle) toggle.setAttribute('aria-expanded', 'false');
    });
  }

  function bind(){
    document.querySelectorAll('[data-v3-day-chip]').forEach((chip) => {
      if (chip.dataset.v3Bound === '1') return;
      chip.dataset.v3Bound = '1';
      chip.addEventListener('click', () => openDay(chip.dataset.v3DayChip));
    });

    document.querySelectorAll('[data-v3-review-day]').forEach((row) => {
      if (row.dataset.v3Bound === '1') return;
      row.dataset.v3Bound = '1';
      row.addEventListener('click', () => {
        const panel = document.querySelector('[data-v3-review]');
        if (panel) panel.hidden = true;
        openDay(row.dataset.v3ReviewDay);
      });
    });

    const reviewOpen = document.querySelector('[data-v3-review-open]');
    if (reviewOpen && reviewOpen.dataset.v3Bound !== '1') {
      reviewOpen.dataset.v3Bound = '1';
      reviewOpen.addEventListener('click', () => {
        updateReview();
        const panel = document.querySelector('[data-v3-review]');
        if (panel) panel.hidden = false;
      });
    }

    const reviewClose = document.querySelector('[data-v3-review-close]');
    if (reviewClose && reviewClose.dataset.v3Bound !== '1') {
      reviewClose.dataset.v3Bound = '1';
      reviewClose.addEventListener('click', () => {
        const panel = document.querySelector('[data-v3-review]');
        if (panel) panel.hidden = true;
      });
    }

    const jump = document.querySelector('[data-v3-jump-current]');
    if (jump && jump.dataset.v3Bound !== '1') {
      jump.dataset.v3Bound = '1';
      jump.addEventListener('click', () => openDay(currentWorkDay()));
    }
  }

  function sync(){
    updateWelcome();
    updateWeekStrip();
    updateReview();
  }

  function init(){
    bind();
    collapseDays();
    sync();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-select-day], [data-cancel-day]')) {
      setTimeout(sync, 250);
      setTimeout(sync, 850);
    }
  }, true);
})();




/* === MOBILE FOOD-FIRST UX === */
(function(){
  const DAYS = ['Pondělí','Úterý','Středa','Čtvrtek','Pátek'];

  function isMobile(){
    return window.innerWidth <= 900;
  }

  function openOnlyDay(day){
    if (!isMobile()) return;

    document.querySelectorAll('[data-day-section]').forEach((section) => {
      const active = section.dataset.daySection === day;
      section.classList.toggle('is-open', active);

      const content = section.querySelector('[data-day-content]');
      const toggle = section.querySelector('[data-day-toggle]');

      if (content) content.hidden = !active;
      if (toggle) toggle.setAttribute('aria-expanded', active ? 'true' : 'false');
    });

    document.querySelectorAll('[data-v3-day-chip]').forEach((chip) => {
      chip.classList.toggle('mobile-active-day', chip.dataset.v3DayChip === day);
    });

    const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
    if (section) {
      section.scrollIntoView({behavior:'smooth', block:'start'});
    }
  }

  function initFoodFirst(){
    if (!isMobile()) return;

    // defaultně všechno sbalit
    document.querySelectorAll('[data-day-section]').forEach((section) => {
      section.classList.remove('is-open');
      const content = section.querySelector('[data-day-content]');
      const toggle = section.querySelector('[data-day-toggle]');
      if (content) content.hidden = true;
      if (toggle) toggle.setAttribute('aria-expanded', 'false');
    });

    // klik na horní ouško otevře den přes displej
    document.querySelectorAll('[data-v3-day-chip]').forEach((chip) => {
      if (chip.dataset.foodFirstBound === '1') return;
      chip.dataset.foodFirstBound = '1';
      chip.addEventListener('click', function(e){
        e.preventDefault();
        openOnlyDay(chip.dataset.v3DayChip);
      });
    });

    // klik na accordion taky otevře jen jeden den
    document.querySelectorAll('[data-day-toggle]').forEach((toggle) => {
      if (toggle.dataset.foodFirstBound === '1') return;
      toggle.dataset.foodFirstBound = '1';
      toggle.addEventListener('click', function(e){
        const day = toggle.dataset.dayToggle;
        setTimeout(() => openOnlyDay(day), 0);
      }, true);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFoodFirst);
  } else {
    initFoodFirst();
  }

  window.addEventListener('resize', initFoodFirst);
})();

/* === Current day highlight polish === */
(function(){
  const DAYS = ['Neděle','Pondělí','Úterý','Středa','Čtvrtek','Pátek','Sobota'];
  const WORK_DAYS = ['Pondělí','Úterý','Středa','Čtvrtek','Pátek'];

  function currentWorkDay(){
    const today = DAYS[new Date().getDay()];
    return WORK_DAYS.includes(today) ? today : 'Pondělí';
  }

  function applyCurrentDayHighlight(){
    const day = currentWorkDay();

    document.querySelectorAll('[data-v3-day-chip]').forEach((chip) => {
      chip.classList.toggle('current', chip.dataset.v3DayChip === day);
    });

    document.querySelectorAll('[data-v3-review-day]').forEach((row) => {
      row.classList.toggle('current-day', row.dataset.v3ReviewDay === day);
    });

    document.querySelectorAll('[data-day-section]').forEach((section) => {
      section.classList.toggle('current-day', section.dataset.daySection === day);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyCurrentDayHighlight);
  } else {
    applyCurrentDayHighlight();
  }

  document.addEventListener('click', () => {
    setTimeout(applyCurrentDayHighlight, 80);
  }, true);
})();

/* === Collapsible day tabs panel === */
(function(){
  function currentActiveLabel(){
    const active = document.querySelector('[data-v3-day-chip].mobile-active-day, [data-v3-day-chip].current');
    if (!active) return 'Vyber den';
    const abbr = (active.querySelector('.v3-day-abbr') || {}).textContent || '';
    const date = (active.querySelector('.v3-day-state') || {}).textContent || '';
    return `${abbr.trim()} ${date.trim()}`.trim() || 'Vyber den';
  }

  function setPanel(open){
    document.body.classList.toggle('v3-day-panel-open', !!open);
    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  function syncLabel(){
    const el = document.querySelector('[data-v3-day-panel-current]');
    if (el) el.textContent = currentActiveLabel();
  }

  function bind(){
    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle && toggle.dataset.bound !== '1') {
      toggle.dataset.bound = '1';
      toggle.addEventListener('click', () => {
        setPanel(!document.body.classList.contains('v3-day-panel-open'));
      });
    }

    document.querySelectorAll('[data-v3-day-chip]').forEach((chip) => {
      if (chip.dataset.panelCloseBound === '1') return;
      chip.dataset.panelCloseBound = '1';
      chip.addEventListener('click', () => {
        setTimeout(() => {
          setPanel(false);
          syncLabel();
        }, 80);
      }, true);
    });

    document.addEventListener('click', (event) => {
      if (!document.body.classList.contains('v3-day-panel-open')) return;
      if (event.target.closest('[data-v3-day-panel-toggle], .v3-week-strip')) return;
      setPanel(false);
    }, true);

    syncLabel();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }

  document.addEventListener('click', () => setTimeout(syncLabel, 120), true);
})();

/* === HARD FINAL DAY PANEL STATE === */
(function(){
  function closePanel(){
    document.body.classList.remove('v3-day-panel-open');
    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
  }

  function bindHardPanel(){
    closePanel();

    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle && toggle.dataset.hardPanelBound !== '1') {
      toggle.dataset.hardPanelBound = '1';
      toggle.addEventListener('click', function(e){
        e.preventDefault();
        e.stopPropagation();
        document.body.classList.toggle('v3-day-panel-open');
        toggle.setAttribute('aria-expanded', document.body.classList.contains('v3-day-panel-open') ? 'true' : 'false');
      }, true);
    }

    document.querySelectorAll('[data-v3-day-chip]').forEach(function(chip){
      if (chip.dataset.hardPanelCloseBound === '1') return;
      chip.dataset.hardPanelCloseBound = '1';
      chip.addEventListener('click', function(){
        setTimeout(closePanel, 120);
      }, true);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindHardPanel);
  } else {
    bindHardPanel();
  }
})();

/* === MERGED DAY PANEL + REVIEW BUTTON FINAL === */
(function(){
  function reviewPanel(){
    return document.querySelector('[data-v3-review]');
  }

  function togglePanel(open){
    document.body.classList.toggle('v3-day-panel-open', !!open);

    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');

    const panel = reviewPanel();
    if (panel) panel.hidden = !open;
  }

  function bindMergedPanel(){
    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle && toggle.dataset.mergedPanelBound !== '1') {
      toggle.dataset.mergedPanelBound = '1';
      toggle.addEventListener('click', function(e){
        e.preventDefault();
        e.stopPropagation();
        togglePanel(!document.body.classList.contains('v3-day-panel-open'));
      }, true);
    }

    document.querySelectorAll('[data-v3-day-chip], [data-v3-review-day]').forEach(function(el){
      if (el.dataset.mergedPanelCloseBound === '1') return;
      el.dataset.mergedPanelCloseBound = '1';
      el.addEventListener('click', function(){
        setTimeout(function(){
          togglePanel(false);
        }, 160);
      }, true);
    });

    const close = document.querySelector('[data-v3-review-close]');
    if (close && close.dataset.mergedPanelCloseButton !== '1') {
      close.dataset.mergedPanelCloseButton = '1';
      close.addEventListener('click', function(e){
        e.preventDefault();
        togglePanel(false);
      }, true);
    }

    const panel = reviewPanel();
    if (panel) panel.hidden = true;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindMergedPanel);
  } else {
    bindMergedPanel();
  }
})();

/* === TARGETED MOBILE V4 PATCH: real class names === */
(function(){
  const DAYS = ['Neděle','Pondělí','Úterý','Středa','Čtvrtek','Pátek','Sobota'];
  const WORK_DAYS = ['Pondělí','Úterý','Středa','Čtvrtek','Pátek'];

  function currentWorkDay(){
    const today = DAYS[new Date().getDay()];
    return WORK_DAYS.includes(today) ? today : 'Pondělí';
  }

  function setPanel(open){
    document.body.classList.toggle('v3-day-panel-open', !!open);

    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');

    const review = document.querySelector('[data-v3-review]');
    if (review) review.hidden = !open;
  }

  function openOnlyDay(day){
    document.querySelectorAll('[data-day-section]').forEach((section) => {
      const active = section.dataset.daySection === day;
      section.classList.toggle('is-open', active);
      const content = section.querySelector('[data-day-content]');
      const toggle = section.querySelector('[data-day-toggle]');
      if (content) content.hidden = !active;
      if (toggle) toggle.setAttribute('aria-expanded', active ? 'true' : 'false');
    });

    document.querySelectorAll('[data-v3-day-chip]').forEach((chip) => {
      chip.classList.toggle('mobile-active-day', chip.dataset.v3DayChip === day);
      chip.classList.toggle('current', chip.dataset.v3DayChip === currentWorkDay());
    });

    document.querySelectorAll('[data-v3-review-day]').forEach((row) => {
      row.classList.toggle('current-day', row.dataset.v3ReviewDay === currentWorkDay());
    });

    const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
    if (section) section.scrollIntoView({behavior:'smooth', block:'start'});
  }

  function init(){
    const today = currentWorkDay();

    document.querySelectorAll('[data-v3-day-chip]').forEach((chip) => {
      chip.classList.toggle('current', chip.dataset.v3DayChip === today);
      if (chip.dataset.targetedV4Bound === '1') return;
      chip.dataset.targetedV4Bound = '1';
      chip.addEventListener('click', (event) => {
        event.preventDefault();
        openOnlyDay(chip.dataset.v3DayChip);
        setPanel(false);
      }, true);
    });

    document.querySelectorAll('[data-v3-review-day]').forEach((row) => {
      row.classList.toggle('current-day', row.dataset.v3ReviewDay === today);
      if (row.dataset.targetedV4Bound === '1') return;
      row.dataset.targetedV4Bound = '1';
      row.addEventListener('click', (event) => {
        event.preventDefault();
        openOnlyDay(row.dataset.v3ReviewDay);
        setPanel(false);
      }, true);
    });

    const panelToggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (panelToggle && panelToggle.dataset.targetedV4Bound !== '1') {
      panelToggle.dataset.targetedV4Bound = '1';
      panelToggle.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        setPanel(!document.body.classList.contains('v3-day-panel-open'));
      }, true);
    }

    const close = document.querySelector('[data-v3-review-close]');
    if (close && close.dataset.targetedV4Bound !== '1') {
      close.dataset.targetedV4Bound = '1';
      close.addEventListener('click', (event) => {
        event.preventDefault();
        setPanel(false);
      }, true);
    }

    setPanel(false);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

/* === FIX V3 DAY TOGGLE: opened day can collapse === */
(function(){
  function isMobile(){
    return window.innerWidth <= 900;
  }

  function setDayOpen(day, open){
    const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
    if (!section) return;

    section.classList.toggle('is-open', !!open);

    const content = section.querySelector('[data-day-content]');
    const toggle = section.querySelector('[data-day-toggle]');

    if (content) {
      content.hidden = !open;
      content.style.display = open ? '' : 'none';
    }

    if (toggle) {
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
  }

  function closeAllDays(){
    document.querySelectorAll('[data-day-section]').forEach((section) => {
      const day = section.dataset.daySection;
      if (day) setDayOpen(day, false);
    });
  }

  function openOnlyDay(day){
    document.querySelectorAll('[data-day-section]').forEach((section) => {
      const sectionDay = section.dataset.daySection;
      if (!sectionDay) return;
      setDayOpen(sectionDay, sectionDay === day);
    });

    document.querySelectorAll('[data-v3-day-chip]').forEach((chip) => {
      chip.classList.toggle('mobile-active-day', chip.dataset.v3DayChip === day);
    });

    const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
    if (section) {
      section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function toggleDay(day){
    const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
    if (!section) return;

    const alreadyOpen = section.classList.contains('is-open');

    if (alreadyOpen) {
      setDayOpen(day, false);
      document.querySelectorAll('[data-v3-day-chip]').forEach((chip) => {
        if (chip.dataset.v3DayChip === day) chip.classList.remove('mobile-active-day');
      });
    } else {
      openOnlyDay(day);
    }
  }

  function closePanel(){
    document.body.classList.remove('v3-day-panel-open');
    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');

    const review = document.querySelector('[data-v3-review]');
    if (review) review.hidden = true;
  }

  function bindFinalDayToggle(){
    if (!isMobile()) return;

    // Výchozí stav: dny sbalené.
    closeAllDays();

    document.addEventListener('click', function(event){
      const dayToggle = event.target.closest('[data-day-toggle]');
      if (dayToggle && isMobile()) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        const day = dayToggle.dataset.dayToggle;
        if (day) toggleDay(day);
        return;
      }

      const dayChip = event.target.closest('[data-v3-day-chip]');
      if (dayChip && isMobile()) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        const day = dayChip.dataset.v3DayChip;
        if (day) openOnlyDay(day);
        closePanel();
        return;
      }

      const reviewRow = event.target.closest('[data-v3-review-day]');
      if (reviewRow && isMobile()) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        const day = reviewRow.dataset.v3ReviewDay;
        if (day) openOnlyDay(day);
        closePanel();
        return;
      }
    }, true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindFinalDayToggle);
  } else {
    bindFinalDayToggle();
  }
})();

/* === V3 compact dish cards toggle === */
(function(){
  function isMobile(){
    return window.innerWidth <= 900;
  }

  function bindCompactDishCards(){
    document.querySelectorAll('.dish-card[data-day][data-dish-id]').forEach((card) => {
      if (card.dataset.compactDishBound === '1') return;
      card.dataset.compactDishBound = '1';

      const top = card.querySelector('.dish-top');
      if (!top) return;

      top.addEventListener('click', function(event){
        if (!isMobile()) return;

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        const wasExpanded = card.classList.contains('mobile-dish-expanded');

        const parentDay = card.closest('[data-day-section]');
        if (parentDay) {
          parentDay.querySelectorAll('.dish-card.mobile-dish-expanded').forEach((other) => {
            if (other !== card) other.classList.remove('mobile-dish-expanded');
          });
        }

        card.classList.toggle('mobile-dish-expanded', !wasExpanded);
      }, true);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindCompactDishCards);
  } else {
    bindCompactDishCards();
  }

  document.addEventListener('click', function(event){
    if (event.target.closest('[data-select-day], [data-cancel-day]')) {
      setTimeout(bindCompactDishCards, 100);
    }
  }, true);
})();

/* === EXACT TARGET MOBILE UI === */
(function(){
  function setPanel(open){
    document.body.classList.toggle('v3-day-panel-open', !!open);
    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');

    const review = document.querySelector('[data-v3-review]');
    if (review) review.hidden = !open;
  }

  function bindExactTarget(){
    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle && toggle.dataset.exactTargetBound !== '1') {
      toggle.dataset.exactTargetBound = '1';
      toggle.addEventListener('click', function(e){
        e.preventDefault();
        e.stopPropagation();
        setPanel(!document.body.classList.contains('v3-day-panel-open'));
      }, true);
    }

    setPanel(false);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindExactTarget);
  } else {
    bindExactTarget();
  }
})();

/* === FINAL FIX: weekly panel opens review only, tabs stay visible === */
(function(){
  const DAYS = ['Neděle','Pondělí','Úterý','Středa','Čtvrtek','Pátek','Sobota'];
  const WORK_DAYS = ['Pondělí','Úterý','Středa','Čtvrtek','Pátek'];

  function todayWorkDay(){
    const d = DAYS[new Date().getDay()];
    return WORK_DAYS.includes(d) ? d : 'Pondělí';
  }

  function setReviewOpen(open){
    document.body.classList.toggle('v3-day-panel-open', !!open);

    const toggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');

    const review = document.querySelector('[data-v3-review]');
    if (review) review.hidden = !open;
  }

  function openDay(day){
    document.querySelectorAll('[data-day-section]').forEach(section => {
      const active = section.dataset.daySection === day;
      section.classList.toggle('is-open', active);

      const content = section.querySelector('[data-day-content]');
      const toggle = section.querySelector('[data-day-toggle]');
      if (content) {
        content.hidden = !active;
        content.style.display = active ? '' : 'none';
      }
      if (toggle) toggle.setAttribute('aria-expanded', active ? 'true' : 'false');
    });

    document.querySelectorAll('[data-v3-day-chip]').forEach(chip => {
      chip.classList.toggle('current', chip.dataset.v3DayChip === todayWorkDay());
      chip.classList.toggle('mobile-active-day', chip.dataset.v3DayChip === day);
    });

    const target = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function bindFinalWeeklyPanel(){
    document.querySelectorAll('[data-v3-day-chip]').forEach(chip => {
      chip.classList.toggle('current', chip.dataset.v3DayChip === todayWorkDay());

      if (chip.dataset.finalWeeklyBound === '1') return;
      chip.dataset.finalWeeklyBound = '1';

      chip.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        openDay(chip.dataset.v3DayChip);
        setReviewOpen(false);
      }, true);
    });

    const panelToggle = document.querySelector('[data-v3-day-panel-toggle]');
    if (panelToggle && panelToggle.dataset.finalWeeklyBound !== '1') {
      panelToggle.dataset.finalWeeklyBound = '1';
      panelToggle.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        setReviewOpen(!document.body.classList.contains('v3-day-panel-open'));
      }, true);
    }

    const close = document.querySelector('[data-v3-review-close]');
    if (close && close.dataset.finalWeeklyBound !== '1') {
      close.dataset.finalWeeklyBound = '1';
      close.addEventListener('click', e => {
        e.preventDefault();
        setReviewOpen(false);
      }, true);
    }

    setReviewOpen(false);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindFinalWeeklyPanel);
  } else {
    bindFinalWeeklyPanel();
  }
})();

/* === FIX: keep MENU first in mobile nav === */
(function(){
  function normalizeMobileNav(){
    const nav = document.querySelector('.nav-links');
    if (!nav) return;

    const links = Array.from(nav.querySelectorAll('a.nav-pill'));
    const menu = links.find(a => {
      const txt = (a.textContent || '').trim().toLowerCase();
      const href = a.getAttribute('href') || '';
      return txt.includes('menu') || href === '/' || href === '/orders';
    });

    if (menu && nav.firstElementChild !== menu) {
      nav.insertBefore(menu, nav.firstElementChild);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', normalizeMobileNav);
  } else {
    normalizeMobileNav();
  }
})();

/* === UX V4 behavior === */
(function(){
  function isMobile(){
    return window.innerWidth <= 900;
  }

  function setDay(day, shouldScroll){
    document.querySelectorAll('[data-day-section]').forEach(section => {
      const open = section.dataset.daySection === day;
      section.classList.toggle('is-open', open);
      const content = section.querySelector('[data-day-content]');
      const toggle = section.querySelector('[data-day-toggle]');
      if (content) content.hidden = !open;
      if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    document.querySelectorAll('[data-uxv4-day-pill]').forEach(pill => {
      pill.classList.toggle('active', pill.dataset.uxv4DayPill === day);
    });

    if (shouldScroll) {
      const target = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
      if (target) target.scrollIntoView({behavior:'smooth', block:'start'});
    }
  }

  function bindV4(){
    if (!isMobile()) return;

    document.querySelectorAll('[data-uxv4-day-pill]').forEach(pill => {
      if (pill.dataset.uxv4Bound === '1') return;
      pill.dataset.uxv4Bound = '1';
      pill.addEventListener('click', e => {
        e.preventDefault();
        setDay(pill.dataset.uxv4DayPill, true);
      });
    });

    document.querySelectorAll('[data-day-toggle]').forEach(btn => {
      if (btn.dataset.uxv4Bound === '1') return;
      btn.dataset.uxv4Bound = '1';
      btn.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        const section = btn.closest('[data-day-section]');
        const day = btn.dataset.dayToggle;
        const isOpen = section && section.classList.contains('is-open');

        if (isOpen) {
          section.classList.remove('is-open');
          const content = section.querySelector('[data-day-content]');
          if (content) content.hidden = true;
          btn.setAttribute('aria-expanded', 'false');
        } else {
          setDay(day, false);
        }
      }, true);
    });

    document.querySelectorAll('[data-uxv4-dish-toggle]').forEach(btn => {
      if (btn.dataset.uxv4Bound === '1') return;
      btn.dataset.uxv4Bound = '1';
      btn.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        const card = btn.closest('.uxv4-dish-card');
        if (!card) return;
        const parent = card.closest('[data-day-section]');
        if (parent) {
          parent.querySelectorAll('.uxv4-dish-card.is-expanded').forEach(other => {
            if (other !== card) other.classList.remove('is-expanded');
          });
        }
        card.classList.toggle('is-expanded');
      }, true);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindV4);
  } else {
    bindV4();
  }
})();

/* === UX V4 behavior === */
(function(){
  function isMobile(){
    return window.innerWidth <= 900;
  }

  function setDay(day, shouldScroll){
    document.querySelectorAll('[data-day-section]').forEach(section => {
      const open = section.dataset.daySection === day;
      section.classList.toggle('is-open', open);
      const content = section.querySelector('[data-day-content]');
      const toggle = section.querySelector('[data-day-toggle]');
      if (content) content.hidden = !open;
      if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    document.querySelectorAll('[data-uxv4-day-pill]').forEach(pill => {
      pill.classList.toggle('active', pill.dataset.uxv4DayPill === day);
    });

    if (shouldScroll) {
      const target = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
      if (target) target.scrollIntoView({behavior:'smooth', block:'start'});
    }
  }

  function bindV4(){
    if (!isMobile()) return;

    document.querySelectorAll('[data-uxv4-day-pill]').forEach(pill => {
      if (pill.dataset.uxv4Bound === '1') return;
      pill.dataset.uxv4Bound = '1';
      pill.addEventListener('click', e => {
        e.preventDefault();
        setDay(pill.dataset.uxv4DayPill, true);
      });
    });

    document.querySelectorAll('[data-day-toggle]').forEach(btn => {
      if (btn.dataset.uxv4Bound === '1') return;
      btn.dataset.uxv4Bound = '1';
      btn.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        const section = btn.closest('[data-day-section]');
        const day = btn.dataset.dayToggle;
        const isOpen = section && section.classList.contains('is-open');

        if (isOpen) {
          section.classList.remove('is-open');
          const content = section.querySelector('[data-day-content]');
          if (content) content.hidden = true;
          btn.setAttribute('aria-expanded', 'false');
        } else {
          setDay(day, false);
        }
      }, true);
    });

    document.querySelectorAll('[data-uxv4-dish-toggle]').forEach(btn => {
      if (btn.dataset.uxv4Bound === '1') return;
      btn.dataset.uxv4Bound = '1';
      btn.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        const card = btn.closest('.uxv4-dish-card');
        if (!card) return;
        const parent = card.closest('[data-day-section]');
        if (parent) {
          parent.querySelectorAll('.uxv4-dish-card.is-expanded').forEach(other => {
            if (other !== card) other.classList.remove('is-expanded');
          });
        }
        card.classList.toggle('is-expanded');
      }, true);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindV4);
  } else {
    bindV4();
  }
})();

/* === FORCE NAVBAR CONSISTENCY === */
(function(){

  function normalizeNavbar(){
    const nav = document.querySelector('.glass-nav');
    if (!nav) return;

    // sjednotí active stav podle URL
    const path = location.pathname;

    document.querySelectorAll('.nav-pill').forEach(pill=>{
      pill.classList.remove('active');

      if (path.includes('/orders') && pill.textContent.includes('REPORT')) {
        pill.classList.add('active');
      }
      if (path.includes('/profile') && pill.textContent.includes('PROFIL')) {
        pill.classList.add('active');
      }
      if (path.includes('/admin') && pill.textContent.includes('ADMIN')) {
        pill.classList.add('active');
      }
    });
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', normalizeNavbar);
  } else {
    normalizeNavbar();
  }

})();

/* === UX V4 food actions hard binding === */
(function(){
  function csrf(){
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
  }

  async function postJson(url, payload){
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrf()
      },
      body: JSON.stringify(payload || {})
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.success === false) {
      throw new Error(data.message || 'Akce se nepodařila.');
    }
    return data;
  }

  function dishPayload(card){
    try {
      return JSON.parse(card.dataset.dishPayload || '{}');
    } catch (_) {
      return {};
    }
  }

  function openV4Modal(card){
    const payload = dishPayload(card);
    const modal = document.getElementById('dish-modal');
    const content = document.getElementById('dish-modal-content');
    if (!modal || !content) return;

    content.innerHTML = `
      <div class="dish-modal-hero">
        <div class="emoji-bubble">${payload.emoji || '🍽️'}</div>
        <div>
          <h2 class="display" style="color:#fff;margin:0 0 8px">${payload.dish_name || 'Detail jídla'}</h2>
          <p class="muted">${payload.price_text || ''}</p>
        </div>
      </div>
      <div class="stack">
        <p>${payload.safe === false ? '⚠️ Obsahuje alergen podle profilu.' : 'Bez upozornění podle profilu.'}</p>
        <p>Popularita: ${payload.popularity || 0}× · Hodnocení: ${payload.thumbs || 0}×</p>
      </div>
    `;

    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
  }

  function closeV4Modal(){
    const modal = document.getElementById('dish-modal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
  }

  function bindV4FoodActions(){
    document.addEventListener('click', async function(e){
      const detailBtn = e.target.closest('[data-open-dish-modal]');
      if (detailBtn) {
        e.preventDefault();
        e.stopPropagation();
        const card = detailBtn.closest('.uxv4-dish-card, .dish-card');
        if (card) openV4Modal(card);
        return;
      }

      const selectBtn = e.target.closest('[data-select-day][data-select-dish-id]');
      if (selectBtn) {
        e.preventDefault();
        e.stopPropagation();
        selectBtn.disabled = true;
        try {
          await postJson('/order-api', {
            day: selectBtn.dataset.selectDay,
            dish_id: selectBtn.dataset.selectDishId
          });
          window.location.reload();
        } catch (err) {
          alert(err.message);
          selectBtn.disabled = false;
        }
        return;
      }

      const cancelBtn = e.target.closest('[data-cancel-day]');
      if (cancelBtn) {
        e.preventDefault();
        e.stopPropagation();
        cancelBtn.disabled = true;
        try {
          await postJson('/order-api/cancel', {
            day: cancelBtn.dataset.cancelDay
          });
          window.location.reload();
        } catch (err) {
          alert(err.message);
          cancelBtn.disabled = false;
        }
        return;
      }

      const rateBtn = e.target.closest('[data-rate-dish]');
      if (rateBtn) {
        e.preventDefault();
        e.stopPropagation();
        rateBtn.disabled = true;
        try {
          await postJson('/order-api/rate', {
            dish_name: rateBtn.dataset.rateDish
          });
          window.location.reload();
        } catch (err) {
          alert(err.message);
          rateBtn.disabled = false;
        }
        return;
      }

      if (e.target.closest('[data-close-modal], .modal-backdrop')) {
        e.preventDefault();
        closeV4Modal();
      }
    }, true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindV4FoodActions);
  } else {
    bindV4FoodActions();
  }
})();

/* === FINAL FIX: UX V4 order buttons use FormData === */
(function(){
  function getCsrf(){
    return (
      document.querySelector('meta[name="csrf-token"]')?.content ||
      document.querySelector('input[name="csrf_token"]')?.value ||
      ''
    );
  }

  async function postForm(url, data){
    const fd = new FormData();
    Object.entries(data || {}).forEach(([key, value]) => fd.append(key, value));
    fd.append('csrf_token', getCsrf());

    const res = await fetch(url, {
      method: 'POST',
      body: fd,
      headers: {
        'X-CSRF-Token': getCsrf()
      }
    });

    const text = await res.text();
    let payload = {};
    try { payload = JSON.parse(text); } catch (_) {}

    if (!res.ok || payload.success === false) {
      throw new Error(payload.message || text || 'Objednávku se nepodařilo uložit.');
    }

    return payload;
  }

  document.addEventListener('click', async function(event){
    const selectBtn = event.target.closest('button[data-select-day][data-select-dish-id]');
    if (selectBtn) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      if (selectBtn.dataset.busy === '1') return;
      selectBtn.dataset.busy = '1';
      selectBtn.disabled = true;

      try {
        await postForm('/order-api', {
          day: selectBtn.dataset.selectDay,
          dish_id: selectBtn.dataset.selectDishId
        });
        window.location.reload();
      } catch (err) {
        alert(err.message || 'Objednávku se nepodařilo uložit.');
        selectBtn.disabled = false;
        selectBtn.dataset.busy = '0';
      }
      return;
    }

    const cancelBtn = event.target.closest('button[data-cancel-day]');
    if (cancelBtn) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      if (cancelBtn.dataset.busy === '1') return;
      cancelBtn.dataset.busy = '1';
      cancelBtn.disabled = true;

      try {
        await postForm('/order-api/cancel', {
          day: cancelBtn.dataset.cancelDay
        });
        window.location.reload();
      } catch (err) {
        alert(err.message || 'Zrušení objednávky se nepodařilo.');
        cancelBtn.disabled = false;
        cancelBtn.dataset.busy = '0';
      }
    }
  }, true);
})();

/* === FINAL MULTI RESTAURANT + ORDER BUTTON BINDING === */
(function(){
  function csrf(){
    return document.querySelector('meta[name="csrf-token"]')?.content ||
           document.querySelector('input[name="csrf_token"]')?.value || '';
  }

  async function postForm(url, payload){
    const fd = new FormData();
    Object.entries(payload || {}).forEach(([k, v]) => fd.append(k, v));
    fd.append('csrf_token', csrf());

    const res = await fetch(url, {
      method: 'POST',
      body: fd,
      headers: {'X-CSRF-Token': csrf()}
    });

    const text = await res.text();
    let data = {};
    try { data = JSON.parse(text); } catch (_) {}

    if (!res.ok || data.success === false) {
      throw new Error(data.message || text || 'Akce se nepodařila.');
    }
    return data;
  }

  document.addEventListener('click', async function(event){
    const restaurantBtn = event.target.closest('[data-restaurant-id]');
    if (restaurantBtn) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      try {
        await postForm('/restaurant/select', {
          restaurant_id: restaurantBtn.dataset.restaurantId
        });
        window.location.href = window.location.pathname + '?v=restaurant-' + Date.now();
      } catch (err) {
        alert(err.message || 'Restauraci se nepodařilo přepnout.');
      }
      return;
    }

    const quick = event.target.closest('.uxv4-quick-order[data-select-day][data-select-dish-id]');
    if (quick) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      if (quick.dataset.locked === '1') return;
      quick.dataset.locked = '1';
      quick.classList.add('is-loading');
      quick.textContent = '…';

      try {
        await postForm('/order-api', {
          day: quick.dataset.selectDay,
          dish_id: quick.dataset.selectDishId
        });
        window.location.href = window.location.pathname + '?v=ordered-' + Date.now();
      } catch (err) {
        alert(err.message || 'Objednávku se nepodařilo uložit.');
        quick.dataset.locked = '0';
        quick.classList.remove('is-loading');
        quick.textContent = '+';
      }
    }
  }, true);
})();

/* === V4 DISH DETAIL CLEAN LOGIC === */
(function(){
  function cardOf(node){
    return node ? node.closest('.uxv4-dish-card, .dish-card') : null;
  }

  document.addEventListener('click', function(e){
    /* Objednávací a formulářová tlačítka nesmí rozbalovat detail */
    if (e.target.closest('[data-select-day], [data-cancel-day], .uxv4-quick-order, button[type="submit"], a')) {
      return;
    }

    const toggle = e.target.closest('[data-uxv4-dish-toggle], .uxv4-dish-side');
    if (!toggle) return;

    const card = cardOf(toggle);
    if (!card) return;

    e.preventDefault();
    e.stopPropagation();

    const isOpen = card.classList.toggle('is-expanded');
    const main = card.querySelector('[data-uxv4-dish-toggle]');
    if (main) main.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  }, true);

  document.addEventListener('keydown', function(e){
    const main = e.target.closest('[data-uxv4-dish-toggle]');
    if (!main) return;
    if (e.key !== 'Enter' && e.key !== ' ') return;

    e.preventDefault();
    const card = cardOf(main);
    if (!card) return;

    const isOpen = card.classList.toggle('is-expanded');
    main.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  }, true);
})();

/* === ADMIN TABS RELIABLE BINDING + MOBILE DAY ACCORDION FIX === */
(function(){
  function norm(s){
    return (s || '')
      .toString()
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, '-')
      .replace(/&/g, 'and');
  }

  function initAdminTabs(){
    const adminRoot =
      document.querySelector('[data-active-page="admin"]') ||
      (document.body && document.body.dataset.activePage === 'admin' ? document.body : null);

    if (!adminRoot && location.pathname.indexOf('/admin') !== 0) return;

    const buttons = Array.from(document.querySelectorAll(
      '[data-admin-tab], .admin-tab-btn, .admin-tabs button, .admin-tabs .chip, .admin-tabs .btn-ghost'
    ));

    if (!buttons.length) return;

    const panels = Array.from(document.querySelectorAll(
      '[data-admin-tab-panel], .admin-tab-panel, .admin-section-panel, section[id], div[id]'
    ));

    function keyFromButton(btn){
      return norm(btn.dataset.adminTab || btn.getAttribute('data-tab') || btn.textContent);
    }

    function keyFromPanel(panel){
      return norm(
        panel.dataset.adminTabPanel ||
        panel.getAttribute('data-tab-panel') ||
        panel.id ||
        panel.getAttribute('aria-label') ||
        ''
      );
    }

    function activate(key){
      if (!key) return;

      buttons.forEach(btn => {
        const bkey = keyFromButton(btn);
        const active =
          bkey === key ||
          bkey.includes(key) ||
          key.includes(bkey);

        btn.classList.toggle('is-active', active);
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-selected', active ? 'true' : 'false');
      });

      let matched = false;
      panels.forEach(panel => {
        const pkey = keyFromPanel(panel);
        const active =
          pkey === key ||
          pkey.includes(key) ||
          key.includes(pkey);

        if (active) matched = true;

        if (
          pkey.includes('menu') ||
          pkey.includes('import') ||
          pkey.includes('billing') ||
          pkey.includes('uct') ||
          pkey.includes('account') ||
          pkey.includes('audit')
        ) {
          panel.classList.toggle('is-active', active);
          panel.hidden = !active;
        }
      });

      location.hash = 'tab-' + key;
    }

    buttons.forEach(btn => {
      btn.addEventListener('click', function(e){
        const key = keyFromButton(btn);
        if (!key) return;

        if (
          key.includes('menu') ||
          key.includes('import') ||
          key.includes('billing') ||
          key.includes('uct') ||
          key.includes('account') ||
          key.includes('audit')
        ) {
          e.preventDefault();
          activate(key);
        }
      }, true);
    });

    const hashKey = location.hash.replace('#tab-', '');
    if (hashKey) activate(hashKey);
    else activate(keyFromButton(buttons.find(b => b.classList.contains('active') || b.classList.contains('is-active')) || buttons[0]));
  }

  function initMobileDayAccordion(){
    if (document.body.dataset.activePage !== 'menu') return;

    const sections = Array.from(document.querySelectorAll('[data-day-section], .day-section'));
    if (!sections.length) return;

    // default: všechny dny zavřené
    sections.forEach(section => {
      section.classList.remove('is-open');
      const btn = section.querySelector('[data-day-toggle], .day-accordion-toggle');
      const content = section.querySelector('.day-content, [data-day-content]');
      if (btn) btn.setAttribute('aria-expanded', 'false');
      if (content) content.hidden = true;
    });

    document.addEventListener('click', function(e){
      const toggle = e.target.closest('[data-day-toggle], .day-accordion-toggle');
      if (!toggle) return;

      const section = toggle.closest('[data-day-section], .day-section');
      if (!section) return;

      e.preventDefault();
      e.stopPropagation();

      const willOpen = !section.classList.contains('is-open');

      // Jen jeden otevřený den najednou.
      sections.forEach(other => {
        other.classList.remove('is-open');
        const b = other.querySelector('[data-day-toggle], .day-accordion-toggle');
        const c = other.querySelector('.day-content, [data-day-content]');
        if (b) b.setAttribute('aria-expanded', 'false');
        if (c) c.hidden = true;
      });

      if (willOpen) {
        section.classList.add('is-open');
        toggle.setAttribute('aria-expanded', 'true');
        const content = section.querySelector('.day-content, [data-day-content]');
        if (content) content.hidden = false;
      }
    }, true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function(){
      initAdminTabs();
      initMobileDayAccordion();
    });
  } else {
    initAdminTabs();
    initMobileDayAccordion();
  }
})();

/* === HARD DEFAULT: collapse all day sections on page load === */
(function(){
  function collapseAllDays(){
    if (!document.body || document.body.dataset.activePage !== 'menu') return;

    document.querySelectorAll('[data-day-section], .day-section').forEach(section => {
      section.classList.remove('is-open');

      const toggle = section.querySelector('[data-day-toggle], .day-accordion-toggle');
      if (toggle) toggle.setAttribute('aria-expanded', 'false');

      section.querySelectorAll('.day-content, [data-day-content], .uxv4-dish-list').forEach(content => {
        content.hidden = true;
        content.style.display = 'none';
      });
    });
  }

  function bindDayToggle(){
    if (!document.body || document.body.dataset.activePage !== 'menu') return;

    document.addEventListener('click', function(e){
      const toggle = e.target.closest('[data-day-toggle], .day-accordion-toggle');
      if (!toggle) return;

      const section = toggle.closest('[data-day-section], .day-section');
      if (!section) return;

      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();

      const wasOpen = section.classList.contains('is-open');

      document.querySelectorAll('[data-day-section], .day-section').forEach(other => {
        other.classList.remove('is-open');

        const b = other.querySelector('[data-day-toggle], .day-accordion-toggle');
        if (b) b.setAttribute('aria-expanded', 'false');

        other.querySelectorAll('.day-content, [data-day-content], .uxv4-dish-list').forEach(content => {
          content.hidden = true;
          content.style.display = 'none';
        });
      });

      if (!wasOpen) {
        section.classList.add('is-open');
        toggle.setAttribute('aria-expanded', 'true');

        section.querySelectorAll('.day-content, [data-day-content], .uxv4-dish-list').forEach(content => {
          content.hidden = false;
          content.style.display = '';
        });
      }
    }, true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function(){
      collapseAllDays();
      bindDayToggle();
      setTimeout(collapseAllDays, 50);
      setTimeout(collapseAllDays, 250);
    });
  } else {
    collapseAllDays();
    bindDayToggle();
    setTimeout(collapseAllDays, 50);
    setTimeout(collapseAllDays, 250);
  }
})();

/* === CLEAN MENU V4 LOGIC === */
(function(){
  function csrf(){
    return document.querySelector('meta[name="csrf-token"]')?.content ||
           document.querySelector('input[name="csrf_token"]')?.value || '';
  }

  async function postForm(url, payload){
    const fd = new FormData();
    Object.entries(payload || {}).forEach(([k, v]) => fd.append(k, v));
    fd.append('csrf_token', csrf());

    const res = await fetch(url, {
      method: 'POST',
      body: fd,
      headers: {'X-CSRF-Token': csrf()}
    });

    const text = await res.text();
    let data = {};
    try { data = JSON.parse(text); } catch (_) {}

    if (!res.ok || data.success === false) {
      throw new Error(data.message || text || 'Akce se nepodařila.');
    }

    return data;
  }

  function closeAllDays(){
    document.querySelectorAll('[data-day-section]').forEach(section => {
      section.classList.remove('is-open');
      const btn = section.querySelector('[data-day-toggle]');
      const content = section.querySelector('[data-day-content]');
      if (btn) btn.setAttribute('aria-expanded', 'false');
      if (content) content.hidden = true;
    });
  }

  function openDay(day){
    closeAllDays();
    const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
    if (!section) return;

    section.classList.add('is-open');

    const btn = section.querySelector('[data-day-toggle]');
    const content = section.querySelector('[data-day-content]');
    if (btn) btn.setAttribute('aria-expanded', 'true');
    if (content) content.hidden = false;

    section.scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  function initCleanMenuV4(){
    if (!document.body || document.body.dataset.activePage !== 'menu') return;

    closeAllDays();

    document.addEventListener('click', async function(e){
      const restaurant = e.target.closest('[data-restaurant-id]');
      if (restaurant) {
        e.preventDefault();
        e.stopPropagation();

        await postForm('/restaurant/select', {restaurant_id: restaurant.dataset.restaurantId});
        location.href = location.pathname + '?v=restaurant-' + Date.now();
        return;
      }

      const tab = e.target.closest('[data-jump-day]');
      if (tab) {
        e.preventDefault();
        e.stopPropagation();
        openDay(tab.dataset.jumpDay);
        return;
      }

      const dayToggle = e.target.closest('[data-day-toggle]');
      if (dayToggle) {
        e.preventDefault();
        e.stopPropagation();

        const section = dayToggle.closest('[data-day-section]');
        const day = dayToggle.dataset.dayToggle;
        const wasOpen = section && section.classList.contains('is-open');

        closeAllDays();
        if (!wasOpen) openDay(day);
        return;
      }

      const orderBtn = e.target.closest('[data-select-day][data-select-dish-id]');
      if (orderBtn) {
        e.preventDefault();
        e.stopPropagation();

        if (orderBtn.dataset.loading === '1') return;
        orderBtn.dataset.loading = '1';
        orderBtn.textContent = '…';

        try {
          await postForm('/order-api', {
            day: orderBtn.dataset.selectDay,
            dish_id: orderBtn.dataset.selectDishId
          });
          location.href = location.pathname + '?v=order-' + Date.now();
        } catch (err) {
          alert(err.message || 'Objednávku se nepodařilo uložit.');
          orderBtn.dataset.loading = '0';
          orderBtn.textContent = '+';
        }
        return;
      }

      const cancelBtn = e.target.closest('[data-cancel-day]');
      if (cancelBtn) {
        e.preventDefault();
        e.stopPropagation();

        await postForm('/order-api/cancel', {day: cancelBtn.dataset.cancelDay});
        location.href = location.pathname + '?v=cancel-' + Date.now();
        return;
      }

      const detailToggle = e.target.closest('[data-dish-detail-toggle]');
      if (detailToggle) {
        e.preventDefault();
        e.stopPropagation();

        const card = detailToggle.closest('[data-dish-card]');
        if (!card) return;

        const detail = card.querySelector('.menu-v4-dish-detail');
        const open = !card.classList.contains('is-expanded');

        card.classList.toggle('is-expanded', open);
        detailToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (detail) detail.hidden = !open;
      }
    }, true);

    document.addEventListener('keydown', function(e){
      const detailToggle = e.target.closest('[data-dish-detail-toggle]');
      if (!detailToggle) return;
      if (e.key !== 'Enter' && e.key !== ' ') return;
      e.preventDefault();
      detailToggle.click();
    }, true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCleanMenuV4);
  } else {
    initCleanMenuV4();
  }
})();

/* === CLEAN MENU V4 LOGIC === */
(function(){
  function csrf(){
    return document.querySelector('meta[name="csrf-token"]')?.content ||
           document.querySelector('input[name="csrf_token"]')?.value || '';
  }

  async function postForm(url, payload){
    const fd = new FormData();
    Object.entries(payload || {}).forEach(([k, v]) => fd.append(k, v));
    fd.append('csrf_token', csrf());

    const res = await fetch(url, {
      method: 'POST',
      body: fd,
      headers: {'X-CSRF-Token': csrf()}
    });

    const text = await res.text();
    let data = {};
    try { data = JSON.parse(text); } catch (_) {}

    if (!res.ok || data.success === false) {
      throw new Error(data.message || text || 'Akce se nepodařila.');
    }

    return data;
  }

  function closeAllDays(){
    document.querySelectorAll('[data-day-section]').forEach(section => {
      section.classList.remove('is-open');
      const btn = section.querySelector('[data-day-toggle]');
      const content = section.querySelector('[data-day-content]');
      if (btn) btn.setAttribute('aria-expanded', 'false');
      if (content) content.hidden = true;
    });
  }

  function openDay(day){
    closeAllDays();
    const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
    if (!section) return;

    section.classList.add('is-open');

    const btn = section.querySelector('[data-day-toggle]');
    const content = section.querySelector('[data-day-content]');
    if (btn) btn.setAttribute('aria-expanded', 'true');
    if (content) content.hidden = false;

    section.scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  function initCleanMenuV4(){
    if (!document.body || document.body.dataset.activePage !== 'menu') return;

    closeAllDays();

    document.addEventListener('click', async function(e){
      const restaurant = e.target.closest('[data-restaurant-id]');
      if (restaurant) {
        e.preventDefault();
        e.stopPropagation();

        await postForm('/restaurant/select', {restaurant_id: restaurant.dataset.restaurantId});
        location.href = location.pathname + '?v=restaurant-' + Date.now();
        return;
      }

      const tab = e.target.closest('[data-jump-day]');
      if (tab) {
        e.preventDefault();
        e.stopPropagation();
        openDay(tab.dataset.jumpDay);
        return;
      }

      const dayToggle = e.target.closest('[data-day-toggle]');
      if (dayToggle) {
        e.preventDefault();
        e.stopPropagation();

        const section = dayToggle.closest('[data-day-section]');
        const day = dayToggle.dataset.dayToggle;
        const wasOpen = section && section.classList.contains('is-open');

        closeAllDays();
        if (!wasOpen) openDay(day);
        return;
      }

      const orderBtn = e.target.closest('[data-select-day][data-select-dish-id]');
      if (orderBtn) {
        e.preventDefault();
        e.stopPropagation();

        if (orderBtn.dataset.loading === '1') return;
        orderBtn.dataset.loading = '1';
        orderBtn.textContent = '…';

        try {
          await postForm('/order-api', {
            day: orderBtn.dataset.selectDay,
            dish_id: orderBtn.dataset.selectDishId
          });
          location.href = location.pathname + '?v=order-' + Date.now();
        } catch (err) {
          alert(err.message || 'Objednávku se nepodařilo uložit.');
          orderBtn.dataset.loading = '0';
          orderBtn.textContent = '+';
        }
        return;
      }

      const cancelBtn = e.target.closest('[data-cancel-day]');
      if (cancelBtn) {
        e.preventDefault();
        e.stopPropagation();

        await postForm('/order-api/cancel', {day: cancelBtn.dataset.cancelDay});
        location.href = location.pathname + '?v=cancel-' + Date.now();
        return;
      }

      const detailToggle = e.target.closest('[data-dish-detail-toggle]');
      if (detailToggle) {
        e.preventDefault();
        e.stopPropagation();

        const card = detailToggle.closest('[data-dish-card]');
        if (!card) return;

        const detail = card.querySelector('.menu-v4-dish-detail');
        const open = !card.classList.contains('is-expanded');

        card.classList.toggle('is-expanded', open);
        detailToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (detail) detail.hidden = !open;
      }
    }, true);

    document.addEventListener('keydown', function(e){
      const detailToggle = e.target.closest('[data-dish-detail-toggle]');
      if (!detailToggle) return;
      if (e.key !== 'Enter' && e.key !== ' ') return;
      e.preventDefault();
      detailToggle.click();
    }, true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCleanMenuV4);
  } else {
    initCleanMenuV4();
  }
})();

/* === SMART BOTTOM NAV MORE PANEL === */
(function(){
  function initSmartBottomNav(){
    const toggle = document.querySelector('[data-mobile-more-toggle]');
    const panel = document.querySelector('[data-mobile-more-panel]');
    if (!toggle || !panel) return;

    toggle.addEventListener('click', function(e){
      e.preventDefault();
      e.stopPropagation();
      panel.hidden = !panel.hidden;
    });

    document.addEventListener('click', function(e){
      if (panel.hidden) return;
      if (e.target.closest('[data-mobile-more-panel], [data-mobile-more-toggle]')) return;
      panel.hidden = true;
    });

    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape') panel.hidden = true;
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSmartBottomNav);
  } else {
    initSmartBottomNav();
  }
})();

/* === NATIVE APP TAB SHEET === */
(function(){
  function initNativeTabs(){
    const toggle = document.querySelector('[data-native-search]');
    const panel = document.querySelector('[data-native-search-panel]');
    if (!toggle || !panel) return;

    toggle.addEventListener('click', function(e){
      e.preventDefault();
      e.stopPropagation();
      panel.hidden = !panel.hidden;
    });

    document.addEventListener('click', function(e){
      if (panel.hidden) return;
      if (e.target.closest('[data-native-search-panel], [data-native-search]')) return;
      panel.hidden = true;
    });

    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape') panel.hidden = true;
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNativeTabs);
  } else {
    initNativeTabs();
  }
})();

/* === FINAL NATIVE BOTTOM TAB SHEET === */
(function(){
  function initFinalNativeTabs(){
    const toggle = document.querySelector('[data-native-search]');
    const panel = document.querySelector('[data-native-search-panel]');
    if (!toggle || !panel || toggle.dataset.nativeTabsReady === '1') return;

    toggle.dataset.nativeTabsReady = '1';

    function setOpen(open){
      panel.hidden = !open;
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.classList.toggle('native-sheet-open', !!open);
    }

    toggle.addEventListener('click', function(e){
      e.preventDefault();
      e.stopPropagation();
      setOpen(panel.hidden);
    });

    document.addEventListener('click', function(e){
      if (panel.hidden) return;
      if (e.target.closest('[data-native-search-panel], [data-native-search]')) return;
      setOpen(false);
    });

    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape') setOpen(false);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFinalNativeTabs);
  } else {
    initFinalNativeTabs();
  }
})();

/* === FINAL: force native sheet closed on load + stable toggle === */
(function(){
  function bootFinalNativeSheet(){
    const toggle = document.querySelector('[data-native-search]');
    const panel = document.querySelector('[data-native-search-panel]');
    if (!toggle || !panel) return;

    panel.hidden = true;
    document.body.classList.remove('native-sheet-open');
    toggle.setAttribute('aria-expanded', 'false');

    if (toggle.dataset.finalNativeSheetReady === '1') return;
    toggle.dataset.finalNativeSheetReady = '1';

    function setOpen(open){
      panel.hidden = !open;
      document.body.classList.toggle('native-sheet-open', !!open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    toggle.addEventListener('click', function(e){
      e.preventDefault();
      e.stopPropagation();
      setOpen(panel.hidden);
    }, true);

    document.addEventListener('click', function(e){
      if (panel.hidden) return;
      if (e.target.closest('[data-native-search-panel], [data-native-search]')) return;
      setOpen(false);
    }, true);

    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape') setOpen(false);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootFinalNativeSheet);
  } else {
    bootFinalNativeSheet();
  }
})();

/* ============================================================
   MOBILE NATIVE NAV CLEANUP
   - sheet hidden by default
   - only opens on "Více"
   - closes on outside click / ESC / tab click
   ============================================================ */
(function(){
  function initMobileNativeNavCleanup(){
    const toggle = document.querySelector('[data-native-search]');
    const panel = document.querySelector('[data-native-search-panel]');
    const allTabs = document.querySelectorAll('.native-tab');

    if (!toggle || !panel) return;
    if (toggle.dataset.mobileNativeCleanupReady === '1') return;
    toggle.dataset.mobileNativeCleanupReady = '1';

    function closeSheet(){
      panel.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('native-sheet-open');
    }

    function openSheet(){
      panel.hidden = false;
      toggle.setAttribute('aria-expanded', 'true');
      document.body.classList.add('native-sheet-open');
    }

    // Hard reset on load
    closeSheet();

    toggle.addEventListener('click', function(e){
      e.preventDefault();
      e.stopPropagation();

      if (panel.hidden) {
        openSheet();
      } else {
        closeSheet();
      }
    });

    document.addEventListener('click', function(e){
      if (panel.hidden) return;
      if (e.target.closest('[data-native-search-panel]')) return;
      if (e.target.closest('[data-native-search]')) return;
      closeSheet();
    });

    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape') closeSheet();
    });

    allTabs.forEach(tab => {
      if (tab === toggle) return;
      tab.addEventListener('click', function(){
        closeSheet();
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMobileNativeNavCleanup);
  } else {
    initMobileNativeNavCleanup();
  }
})();

/* === V5 NAV CLEANUP: no quick actions sheet / no overlay blur === */
(function(){
  function cleanupV5Navigation(){
    document.body.classList.remove('native-sheet-open');

    document.querySelectorAll('[data-native-search-panel], .native-more-sheet, .smart-bottom-more').forEach(function(el){
      el.hidden = true;
      el.style.display = 'none';
    });

    document.querySelectorAll('[data-native-search], [data-mobile-more-toggle]').forEach(function(btn){
      btn.setAttribute('aria-expanded', 'false');
      btn.addEventListener('click', function(e){
        const href = btn.getAttribute('href');
        if (!href) {
          e.preventDefault();
          e.stopPropagation();
          document.body.classList.remove('native-sheet-open');
        }
      }, true);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', cleanupV5Navigation);
  } else {
    cleanupV5Navigation();
  }
})();

/* === V6 HARD CLEAN: kill obsolete quick action overlays === */
(function(){
  function hardCleanV6(){
    document.body.classList.remove(
      'native-sheet-open',
      'smart-bottom-open',
      'mobile-more-open',
      'v3-day-panel-open'
    );

    document.querySelectorAll(
      '.native-more-sheet, .smart-bottom-more, [data-native-search-panel], [data-mobile-more-panel], #native-more-sheet'
    ).forEach(function(el){
      el.hidden = true;
      el.style.display = 'none';
      el.style.visibility = 'hidden';
      el.style.opacity = '0';
      el.style.pointerEvents = 'none';
    });

    document.querySelectorAll('[data-native-search], [data-mobile-more-toggle]').forEach(function(btn){
      btn.setAttribute('aria-expanded', 'false');
      btn.onclick = function(e){
        e.preventDefault();
        e.stopPropagation();
        return false;
      };
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hardCleanV6);
  } else {
    hardCleanV6();
  }

  window.addEventListener('pageshow', hardCleanV6);
})();

/* ============================================================
   V7 ADMIN MOBILE TABS FALLBACK
   ============================================================ */
(function(){
  function initAdminTabsV7(){
    const root =
      document.querySelector('[data-admin-tabs]') ||
      document.querySelector('.admin-tabs') ||
      document.querySelector('.admin-tabbar') ||
      document.querySelector('.admin-section-tabs');

    if (!root) return;
    if (root.dataset.v7TabsReady === '1') return;
    root.dataset.v7TabsReady = '1';

    const buttons = Array.from(root.querySelectorAll('button, [data-admin-tab], .admin-tab, .tab-btn'));
    if (!buttons.length) return;

    function normalizeName(txt){
      return String(txt || '')
        .toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .replace(/&/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
    }

    function targetFromButton(btn){
      const explicit =
        btn.dataset.adminTab ||
        btn.dataset.tab ||
        btn.getAttribute('aria-controls') ||
        btn.getAttribute('data-target');

      if (explicit) return explicit.replace(/^#/, '');

      const label = normalizeName(btn.textContent);
      if (label.includes('menu')) return 'menu';
      if (label.includes('billing')) return 'billing';
      if (label.includes('ucty') || label.includes('ucet')) return 'accounts';
      if (label.includes('audit')) return 'audit';
      return '';
    }

    function findPanels(){
      return Array.from(document.querySelectorAll(
        '[data-admin-panel], .admin-panel, .admin-tab-panel, .admin-section-panel, #menu, #billing, #accounts, #audit'
      ));
    }

    function panelKey(panel){
      return (
        panel.dataset.adminPanel ||
        panel.dataset.panel ||
        panel.id ||
        ''
      ).toLowerCase();
    }

    function activate(name){
      if (!name) return;

      buttons.forEach(btn => {
        const active = targetFromButton(btn) === name;
        btn.classList.toggle('active', active);
        btn.classList.toggle('is-active', active);
        btn.setAttribute('aria-selected', active ? 'true' : 'false');
      });

      const panels = findPanels();
      if (!panels.length) return;

      panels.forEach(panel => {
        const key = panelKey(panel);
        const active =
          key === name ||
          key.includes(name) ||
          (name === 'accounts' && (key.includes('ucty') || key.includes('users'))) ||
          (name === 'menu' && key.includes('import'));

        panel.hidden = !active;
        panel.classList.toggle('active', active);
        panel.classList.toggle('is-active', active);
      });
    }

    buttons.forEach(btn => {
      btn.addEventListener('click', function(e){
        const name = targetFromButton(btn);
        if (!name) return;
        e.preventDefault();
        activate(name);
      });
    });

    const current = buttons.find(btn => btn.classList.contains('active') || btn.classList.contains('is-active')) || buttons[0];
    activate(targetFromButton(current));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdminTabsV7);
  } else {
    initAdminTabsV7();
  }
})();
