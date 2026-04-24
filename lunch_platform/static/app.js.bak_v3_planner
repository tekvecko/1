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



/* === UX V3 Sticky Planner === */
(function(){
  function planner(){
    return document.querySelector('[data-v3-planner]');
  }

  function rows(){
    return Array.from(document.querySelectorAll('[data-v3-planner-day]'));
  }

  function pulse(){
    const p = planner();
    if (!p) return;
    p.classList.remove('pulse');
    void p.offsetWidth;
    p.classList.add('pulse');
  }

  function syncFromState(state){
    if (!state) return;

    const count = Number(state.cart_count || 0);
    const countEl = document.querySelector('[data-v3-planner-count]');
    if (countEl) countEl.textContent = String(count);

    const selectedByDay = state.selected_by_day || {};
    const cartItems = state.cart_items || [];

    rows().forEach((row) => {
      const day = row.dataset.v3PlannerDay;
      const food = row.querySelector('.v3-planner-day-food');
      const item = cartItems.find(x => x.day === day);
      const selectedId = Number(selectedByDay[day] || 0);

      if (item) {
        row.classList.add('active');
        if (food) food.textContent = `${item.emoji || '🍽️'} ${item.dish_name || 'Vybrané jídlo'}`;
      } else if (selectedId) {
        row.classList.add('active');
        if (food) food.textContent = '🍽️ Vybrané jídlo';
      } else {
        row.classList.remove('active');
        if (food) food.textContent = '—';
      }
    });

    pulse();
  }

  function bindPlanner(){
    const p = planner();
    if (!p || p.dataset.v3Bound === '1') return;
    p.dataset.v3Bound = '1';

    const toggle = p.querySelector('[data-v3-planner-toggle]');
    if (toggle) {
      toggle.addEventListener('click', () => {
        p.classList.toggle('expanded');
        toggle.setAttribute('aria-expanded', p.classList.contains('expanded') ? 'true' : 'false');
      });
    }

    rows().forEach((row) => {
      row.addEventListener('click', () => {
        const day = row.dataset.v3PlannerDay;
        const section = document.querySelector(`[data-day-section="${CSS.escape(day)}"]`);
        if (typeof openDaySection === 'function') {
          try { openDaySection(day); } catch(e) {}
        }
        if (section) section.scrollIntoView({behavior:'smooth', block:'start'});
        if (window.innerWidth <= 900) p.classList.remove('expanded');
      });
    });
  }

  function hookUpdateSelection(){
    if (window.__v3PlannerHooked) return;
    window.__v3PlannerHooked = true;

    const tryHook = () => {
      if (typeof updateSelectionVisuals !== 'function') return false;
      if (updateSelectionVisuals.__v3PlannerWrapped) return true;

      const original = updateSelectionVisuals;
      updateSelectionVisuals = function(state){
        const result = original(state);
        try { syncFromState(state); } catch(e) {}
        return result;
      };

      updateSelectionVisuals.__v3PlannerWrapped = true;
      return true;
    };

    if (!tryHook()) {
      setTimeout(tryHook, 250);
      setTimeout(tryHook, 900);
    }
  }

  function init(){
    bindPlanner();
    hookUpdateSelection();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
