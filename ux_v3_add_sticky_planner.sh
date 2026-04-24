#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=== UX V3 STICKY PLANNER ==="

cp lunch_platform/templates/orders/index.html lunch_platform/templates/orders/index.html.bak_v3_planner || true
cp lunch_platform/static/navy.css lunch_platform/static/navy.css.bak_v3_planner || true
cp lunch_platform/static/app.js lunch_platform/static/app.js.bak_v3_planner || true

python - <<'PY'
from pathlib import Path

p = Path("lunch_platform/templates/orders/index.html")
t = p.read_text(encoding="utf-8")

planner = """
<section class="v3-planner" data-v3-planner>
  <button type="button" class="v3-planner-head" data-v3-planner-toggle aria-expanded="false">
    <span>🛒 Týdenní plán</span>
    <strong><span data-v3-planner-count>{{ state.cart_count }}</span>/{{ state.menu_days|length }}</strong>
  </button>

  <div class="v3-planner-days" data-v3-planner-days>
    {% for planner_day in state.menu_days %}
      {% set planner_item = (state.cart_items | selectattr('day', 'equalto', planner_day) | list | first) %}
      <button type="button"
              class="v3-planner-day {% if planner_item %}active{% endif %}"
              data-v3-planner-day="{{ planner_day }}">
        <span class="v3-planner-day-name">{{ planner_day[:2] }}</span>
        <span class="v3-planner-day-food">
          {% if planner_item %}{{ planner_item.emoji }} {{ planner_item.dish_name }}{% else %}—{% endif %}
        </span>
      </button>
    {% endfor %}
  </div>
</section>
"""

if 'data-v3-planner' not in t:
    if '{% endblock %}' not in t:
        raise SystemExit("TARGET NOT FOUND: endblock")
    t = t.replace('{% endblock %}', planner + '\n{% endblock %}', 1)

p.write_text(t, encoding="utf-8")
print("template planner inserted")

p = Path("lunch_platform/static/navy.css")
c = p.read_text(encoding="utf-8")

css = r"""
/* === UX V3 Sticky Planner === */
.v3-planner {
  position: fixed;
  left: 14px;
  right: 14px;
  bottom: 14px;
  z-index: 90;
  border-radius: 24px;
  background: rgba(6,13,26,.94);
  border: 1px solid rgba(255,255,255,.12);
  box-shadow: 0 22px 56px rgba(0,0,0,.42);
  backdrop-filter: blur(18px);
  overflow: hidden;
}

.v3-planner-head {
  width: 100%;
  min-height: 58px;
  border: 0;
  background: linear-gradient(135deg, rgba(245,197,24,.98), rgba(245,158,11,.92));
  color: #07111f;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  font-weight: 900;
  cursor: pointer;
}

.v3-planner-days {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  padding: 10px;
}

.v3-planner-day {
  min-width: 0;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: rgba(255,255,255,.82);
  border-radius: 16px;
  padding: 8px 6px;
  cursor: pointer;
}

.v3-planner-day.active {
  background: rgba(37,99,235,.22);
  border-color: rgba(96,165,250,.44);
  color: #fff;
}

.v3-planner-day-name {
  display: block;
  font-weight: 900;
  font-size: .9rem;
}

.v3-planner-day-food {
  display: block;
  margin-top: 3px;
  font-size: .72rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.v3-planner.pulse {
  animation: v3PlannerPulse .55s cubic-bezier(.2,.9,.22,1.2);
}

@keyframes v3PlannerPulse {
  0% { transform: scale(1); }
  35% { transform: scale(1.035); }
  100% { transform: scale(1); }
}

@media (max-width: 900px) {
  .container {
    padding-bottom: 156px !important;
  }

  .v3-planner:not(.expanded) .v3-planner-days {
    display: none;
  }

  .v3-planner.expanded .v3-planner-days {
    display: grid;
  }
}

@media (min-width: 901px) {
  .v3-planner {
    left: auto;
    right: 24px;
    bottom: 24px;
    width: min(480px, calc(100vw - 48px));
  }
}
"""

if "UX V3 Sticky Planner" not in c:
    c += "\n\n" + css

p.write_text(c, encoding="utf-8")
print("css planner inserted")

p = Path("lunch_platform/static/app.js")
j = p.read_text(encoding="utf-8")

js = r"""
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
"""

if "UX V3 Sticky Planner" not in j:
    j += "\n\n" + js

p.write_text(j, encoding="utf-8")
print("js planner inserted")
PY

pytest -q
