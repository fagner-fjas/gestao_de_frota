document.addEventListener('DOMContentLoaded', () => {
  const pageSize = 8;
  const normalize = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  document.querySelectorAll('[data-passenger-picker]').forEach((picker) => {
    const native = [...picker.querySelectorAll('[data-ps-native] input[type="checkbox"]')];
    const modal = picker.querySelector('[data-ps-modal]');
    const dialog = picker.querySelector('[data-ps-dialog]');
    const search = picker.querySelector('[data-ps-search]');
    const availableList = picker.querySelector('[data-ps-available-list]');
    const selectedList = picker.querySelector('[data-ps-selected-list]');
    const selectPage = picker.querySelector('[data-ps-select-page]');
    const prevPage = picker.querySelector('[data-ps-prev]');
    const nextPage = picker.querySelector('[data-ps-next]');
    const filters = [...picker.querySelectorAll('[data-ps-filter]')];
    if (!modal || !dialog || !search) return;

    const people = native.map((checkbox) => {
      const label = checkbox.closest('label');
      const name = (label ? label.textContent : checkbox.value).trim();
      return {
        id: checkbox.value,
        name,
        document: checkbox.dataset.documento || '',
        active: checkbox.dataset.ativo !== 'false',
        linked: checkbox.dataset.vinculado === 'true',
        checkbox,
      };
    });
    const peopleById = new Map(people.map((person) => [person.id, person]));
    let draft = new Set();
    let filter = 'all';
    let page = 1;
    let lastFocus = null;

    const countLabel = (count) => `${count} ${count === 1 ? 'passageiro selecionado' : 'passageiros selecionados'}`;

    function updateSummary() {
      const count = native.filter((checkbox) => checkbox.checked).length;
      picker.querySelector('[data-ps-summary]').textContent = count ? countLabel(count) : 'Nenhum passageiro selecionado';
    }

    function filteredAvailable() {
      const term = normalize(search.value.trim());
      return people.filter((person) => {
        if (draft.has(person.id)) return false;
        if (filter === 'active' && !person.active) return false;
        if (filter === 'unlinked' && person.linked) return false;
        return !term || normalize(`${person.name} ${person.document}`).includes(term);
      });
    }

    function avatar(person) {
      return el('span', 'ps-avatar', person.name.slice(0, 1).toLocaleUpperCase('pt-BR'));
    }

    function personName(person) {
      const details = el('div', 'ps-row-data');
      details.append(el('div', 'ps-row-name', person.name));
      const status = person.active ? 'Ativo' : 'Inativo';
      details.append(el('div', 'ps-row-meta', `Cadastro #${person.id} · ${status}`));
      return details;
    }

    function renderAvailable(peopleOnPage) {
      availableList.replaceChildren();
      if (!peopleOnPage.length) {
        availableList.append(el('p', 'ps-empty', 'Nenhum passageiro encontrado para estes filtros.'));
      }
      peopleOnPage.forEach((person) => {
        const row = el('div', 'ps-row');
        const checkbox = el('input', 'ps-row-checkbox');
        checkbox.type = 'checkbox';
        checkbox.checked = false;
        checkbox.setAttribute('aria-label', `Selecionar ${person.name}`);
        checkbox.addEventListener('change', () => add(person.id));
        const addButton = el('button', 'ps-row-action', '+ Adicionar');
        addButton.type = 'button';
        addButton.setAttribute('aria-label', `Adicionar ${person.name}`);
        addButton.addEventListener('click', () => add(person.id));
        row.append(checkbox, avatar(person), personName(person), addButton);
        availableList.append(row);
      });
    }

    function renderSelected() {
      selectedList.replaceChildren();
      const count = draft.size;
      picker.querySelector('[data-ps-count]').textContent = String(count);
      picker.querySelector('[data-ps-footer-count]').textContent = `${count} ${count === 1 ? 'selecionado' : 'selecionados'}`;
      picker.querySelector('[data-ps-selected-description]').textContent = `${count} ${count === 1 ? 'passageiro escolhido' : 'passageiros escolhidos'}`;
      if (!count) selectedList.append(el('p', 'ps-empty', 'Nenhum passageiro selecionado.'));
      draft.forEach((id) => {
        const person = peopleById.get(id);
        if (!person) return;
        const row = el('div', 'ps-selected-item');
        const removeButton = el('button', 'ps-row-action', 'Remover ×');
        removeButton.type = 'button';
        removeButton.setAttribute('aria-label', `Remover ${person.name}`);
        removeButton.addEventListener('click', () => remove(id));
        row.append(avatar(person), personName(person), removeButton);
        selectedList.append(row);
      });
      picker.querySelector('[data-ps-clear-all]').disabled = count === 0;
    }

    function render() {
      const matches = filteredAvailable();
      const pages = Math.max(1, Math.ceil(matches.length / pageSize));
      page = Math.max(1, Math.min(page, pages));
      const visible = matches.slice((page - 1) * pageSize, page * pageSize);
      picker.querySelector('[data-ps-results-count]').textContent = `${matches.length} ${matches.length === 1 ? 'resultado' : 'resultados'} para a busca`;
      picker.querySelector('[data-ps-page-status]').textContent = `${page} de ${pages}`;
      selectPage.textContent = `Selecionar todos os ${visible.length} resultados visíveis`;
      selectPage.disabled = visible.length === 0;
      prevPage.disabled = page <= 1;
      nextPage.disabled = page >= pages;
      renderAvailable(visible);
      renderSelected();
    }

    function add(id) {
      draft.add(id);
      render();
    }

    function remove(id) {
      draft.delete(id);
      render();
    }

    function setFilter(value) {
      filter = value;
      page = 1;
      filters.forEach((button) => {
        const active = button.dataset.psFilter === value;
        button.classList.toggle('ps-filter-active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      render();
    }

    function onKeys(event) {
      if (modal.hidden) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        close();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = [...dialog.querySelectorAll('button:not([disabled]),input:not([disabled]),[tabindex="0"]')]
        .filter((node) => node.getClientRects().length > 0);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    function open() {
      lastFocus = document.activeElement;
      draft = new Set(native.filter((checkbox) => checkbox.checked).map((checkbox) => checkbox.value));
      search.value = '';
      filter = 'all';
      page = 1;
      modal.hidden = false;
      document.body.classList.add('ps-dialog-open');
      setFilter('all');
      document.addEventListener('keydown', onKeys);
      search.focus();
    }

    function close() {
      modal.hidden = true;
      if (!document.querySelector('[data-ps-modal]:not([hidden])')) document.body.classList.remove('ps-dialog-open');
      document.removeEventListener('keydown', onKeys);
      if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
    }

    picker.querySelector('[data-ps-open]').addEventListener('click', open);
    picker.querySelectorAll('[data-ps-cancel]').forEach((button) => button.addEventListener('click', close));
    picker.querySelector('[data-ps-apply]').addEventListener('click', () => {
      native.forEach((checkbox) => {
        const next = draft.has(checkbox.value);
        if (checkbox.checked !== next) {
          checkbox.checked = next;
          checkbox.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
      updateSummary();
      close();
    });
    search.addEventListener('input', () => {
      page = 1;
      render();
    });
    picker.querySelector('[data-ps-clear]').addEventListener('click', () => {
      search.value = '';
      page = 1;
      render();
      search.focus();
    });
    filters.forEach((button) => button.addEventListener('click', () => setFilter(button.dataset.psFilter)));
    selectPage.addEventListener('click', () => {
      filteredAvailable().slice((page - 1) * pageSize, page * pageSize).forEach((person) => draft.add(person.id));
      render();
    });
    picker.querySelector('[data-ps-clear-all]').addEventListener('click', () => {
      draft.clear();
      render();
    });
    prevPage.addEventListener('click', () => {
      page -= 1;
      render();
    });
    nextPage.addEventListener('click', () => {
      page += 1;
      render();
    });
    picker.classList.add('ps-enhanced');
    updateSummary();
  });
});
