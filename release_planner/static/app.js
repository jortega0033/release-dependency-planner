(function () {
  'use strict';

  var API = '/api/v1/projects';
  var CONFLICT_MESSAGE = 'This plan changed elsewhere. Reload to see the latest version.';

  function $(id) { return document.getElementById(id); }

  var els = {
    status: $('status'),
    errorBox: $('error-box'),
    errorText: $('error-text'),
    errorDetails: $('error-details'),
    reload: $('reload-plan'),
    newPlan: $('new-plan'),
    planList: $('plan-list'),
    planListEmpty: $('plan-list-empty'),
    emptyState: $('empty-state'),
    form: $('plan-form'),
    title: $('plan-title'),
    start: $('plan-start'),
    titleErrors: $('plan-title-errors'),
    startErrors: $('plan-start-errors'),
    tasksErrors: $('tasks-errors'),
    addTask: $('add-task'),
    noTasks: $('no-tasks'),
    taskList: $('task-list'),
    save: $('save-plan'),
    del: $('delete-plan')
  };

  // State. plan.tasks[i] = {id, title, duration (string), preds (array of ids)}
  var plan = null;
  var projects = [];
  var dirty = false;
  var saving = false;
  var editSeq = 0;
  var nextTaskNum = 1;
  var feCounter = 0;
  var described = []; // [{el, id}] for field error cleanup

  // ---------- helpers ----------

  function make(tag, className, text) {
    var e = document.createElement(tag);
    if (className) { e.className = className; }
    if (text !== undefined) { e.textContent = text; }
    return e;
  }

  async function api(method, path, body) {
    var headers = { 'Accept': 'application/json' };
    var opts = { method: method, headers: headers };
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    var res;
    try {
      res = await fetch(path, opts);
    } catch (e) {
      return { ok: false, status: 0, data: null,
        error: { code: 'network', message: 'Could not reach the server. Check that it is running and try again.' } };
    }
    var data = null;
    if (res.status !== 204) {
      try { data = await res.json(); } catch (e) { data = null; }
    }
    var error = null;
    if (!res.ok) {
      error = (data && data.error) || { code: 'http', message: 'Request failed (' + res.status + ').' };
    }
    return { ok: res.ok, status: res.status, data: data, error: error };
  }

  function fromServer(p) {
    var tasks = (p.tasks || []).map(function (t) {
      return {
        id: String(t.id),
        title: String(t.title),
        duration: String(t.duration_days),
        preds: (t.predecessors || []).map(String)
      };
    });
    var max = 0;
    tasks.forEach(function (t) {
      var m = /^t(\d+)$/.exec(t.id);
      if (m) { max = Math.max(max, parseInt(m[1], 10)); }
    });
    nextTaskNum = max + 1;
    return { id: p.id, version: p.version, title: p.title, start_date: p.start_date, tasks: tasks };
  }

  function newTaskId() {
    var used = {};
    plan.tasks.forEach(function (t) { used[t.id] = true; });
    var id = 't' + nextTaskNum;
    while (used[id]) { nextTaskNum += 1; id = 't' + nextTaskNum; }
    nextTaskNum += 1;
    return id;
  }

  function taskById(id) {
    for (var i = 0; i < plan.tasks.length; i++) {
      if (plan.tasks[i].id === id) { return plan.tasks[i]; }
    }
    return null;
  }

  function titleOf(t) {
    var s = t.title.trim();
    return s === '' ? '(untitled)' : s;
  }

  function updateStatus() {
    var text = '';
    if (saving) { text = 'Saving…'; }
    else if (dirty) { text = 'Unsaved changes'; }
    else if (plan) { text = 'Saved (version ' + plan.version + ')'; }
    els.status.textContent = text;
  }

  function markDirty() {
    dirty = true;
    editSeq += 1;
    updateStatus();
  }

  function updateButtons() {
    var has = !!plan;
    els.save.disabled = !has || saving;
    els.del.disabled = !has || saving;
    els.addTask.disabled = !has;
  }

  // ---------- errors ----------

  function clearError() {
    els.errorBox.hidden = true;
    els.errorText.textContent = '';
    els.errorDetails.textContent = '';
    els.reload.hidden = true;
  }

  function showError(message, details, conflict) {
    els.errorText.textContent = message;
    els.errorDetails.textContent = '';
    (details || []).forEach(function (d) {
      var field = d && d.field ? d.field + ': ' : '';
      els.errorDetails.appendChild(make('li', '', field + (d && d.message ? d.message : (d && d.code) || 'Invalid value')));
    });
    els.reload.hidden = !conflict;
    els.errorBox.hidden = false;
  }

  function showApiError(err) {
    if (err && err.code === 'version_conflict') {
      showError(CONFLICT_MESSAGE, null, true);
      return;
    }
    showError((err && err.message) || 'Something went wrong.', err && err.details, false);
  }

  function clearFieldErrors() {
    described.forEach(function (d) {
      var cur = (d.el.getAttribute('aria-describedby') || '').split(/\s+/).filter(function (x) { return x && x !== d.id; });
      if (cur.length) { d.el.setAttribute('aria-describedby', cur.join(' ')); }
      else { d.el.removeAttribute('aria-describedby'); }
      d.el.removeAttribute('aria-invalid');
    });
    described = [];
    var old = document.querySelectorAll('.field-error');
    for (var i = 0; i < old.length; i++) { old[i].remove(); }
  }

  function addFieldError(container, target, text) {
    feCounter += 1;
    var id = 'fe-' + feCounter;
    var p = make('p', 'field-error', text);
    p.id = id;
    container.appendChild(p);
    if (target) {
      var cur = target.getAttribute('aria-describedby');
      target.setAttribute('aria-describedby', cur ? cur + ' ' + id : id);
      target.setAttribute('aria-invalid', 'true');
      described.push({ el: target, id: id });
    }
  }

  function applyFieldErrors(details) {
    (details || []).forEach(function (d) {
      if (!d || typeof d.field !== 'string') { return; }
      var msg = d.message || d.code || 'Invalid value';
      var f = d.field;
      var m = /^tasks\[(\d+)\](?:\.([A-Za-z_]+))?/.exec(f);
      if (f === 'title') {
        addFieldError(els.titleErrors, els.title, msg);
      } else if (f === 'start_date') {
        addFieldError(els.startErrors, els.start, msg);
      } else if (m) {
        var row = els.taskList.children[parseInt(m[1], 10)];
        if (!row) { addFieldError(els.tasksErrors, null, msg); return; }
        var target = null;
        if (m[2] === 'duration_days') { target = row.querySelector('[name="task-duration"]'); }
        else if (m[2] === 'predecessors') { target = row.querySelector('fieldset'); }
        else { target = row.querySelector('[name="task-title"]'); }
        addFieldError(row.querySelector('.row-errors'), target, msg);
      } else {
        addFieldError(els.tasksErrors, null, msg);
      }
    });
  }

  // ---------- rendering ----------

  function renderPlanList() {
    els.planList.textContent = '';
    projects.forEach(function (p) {
      var li = make('li', 'plan-item');
      var current = !!plan && plan.id === p.id;
      if (current) { li.classList.add('current'); }
      var text = make('div', 'plan-item-text');
      text.appendChild(make('div', 'plan-item-title', p.title));
      var n = p.task_count;
      text.appendChild(make('div', 'plan-item-meta', p.start_date + ' · ' + n + (n === 1 ? ' task' : ' tasks')));
      li.appendChild(text);
      var btn = make('button', 'btn btn-small', 'Open');
      btn.type = 'button';
      btn.setAttribute('aria-label', 'Open ' + p.title);
      if (current) { btn.setAttribute('aria-current', 'true'); }
      btn.addEventListener('click', function () { openPlan(p.id); });
      li.appendChild(btn);
      els.planList.appendChild(li);
    });
    els.planListEmpty.hidden = projects.length > 0;
  }

  function depLabelText(task) {
    var names = plan.tasks.filter(function (t) { return task.preds.indexOf(t.id) !== -1; }).map(titleOf);
    return names.length ? 'After: ' + names.join(', ') : 'No predecessors';
  }

  // Update text that depends on titles/dependencies without rebuilding rows.
  function refreshDerived() {
    var rows = els.taskList.children;
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var task = taskById(row.dataset.taskId);
      if (!task) { continue; }
      var labels = row.querySelectorAll('label[data-pred]');
      for (var j = 0; j < labels.length; j++) {
        var pt = taskById(labels[j].dataset.pred);
        if (pt) { labels[j].textContent = titleOf(pt); }
      }
      row.querySelector('.dep-text').textContent = depLabelText(task);
      var chips = row.querySelector('.dep-chips');
      chips.textContent = '';
      plan.tasks.forEach(function (t, idx) {
        if (task.preds.indexOf(t.id) !== -1) { chips.appendChild(make('span', 'chip', '#' + (idx + 1))); }
      });
      var name = titleOf(task);
      row.querySelector('.remove').setAttribute('aria-label', 'Remove ' + name);
      row.querySelector('.move-up').setAttribute('aria-label', 'Move up ' + name);
      row.querySelector('.move-down').setAttribute('aria-label', 'Move down ' + name);
    }
  }

  function buildRow(task, index) {
    var li = make('li', 'task-row');
    li.dataset.taskId = task.id;
    var pre = 'f-' + task.id;

    li.appendChild(make('div', 'order', String(index + 1)));
    var body = make('div', 'row-body');
    li.appendChild(body);

    var fields = make('div', 'row-fields');
    body.appendChild(fields);

    var fTitle = make('div', 'field grow');
    var lTitle = make('label', '', 'Task title');
    lTitle.htmlFor = pre + '-title';
    var iTitle = make('input');
    iTitle.type = 'text';
    iTitle.id = pre + '-title';
    iTitle.name = 'task-title';
    iTitle.maxLength = 120;
    iTitle.autocomplete = 'off';
    iTitle.value = task.title;
    iTitle.addEventListener('input', function () {
      task.title = iTitle.value;
      markDirty();
      refreshDerived();
    });
    fTitle.appendChild(lTitle);
    fTitle.appendChild(iTitle);
    fields.appendChild(fTitle);

    var fDur = make('div', 'field duration');
    var lDur = make('label', '', 'Duration (working days)');
    lDur.htmlFor = pre + '-duration';
    var iDur = make('input');
    iDur.type = 'number';
    iDur.id = pre + '-duration';
    iDur.name = 'task-duration';
    iDur.min = '1';
    iDur.max = '365';
    iDur.step = '1';
    iDur.value = task.duration;
    iDur.addEventListener('input', function () {
      task.duration = iDur.value;
      markDirty();
    });
    fDur.appendChild(lDur);
    fDur.appendChild(iDur);
    fields.appendChild(fDur);

    var fs = make('fieldset', 'preds');
    fs.appendChild(make('legend', '', 'Predecessors'));
    var opts = make('div', 'pred-options');
    var others = plan.tasks.filter(function (t) { return t.id !== task.id; });
    others.forEach(function (other) {
      var wrap = make('div', 'pred-option');
      var cb = make('input');
      cb.type = 'checkbox';
      cb.name = 'task-pred';
      cb.value = other.id;
      cb.id = pre + '-pred-' + other.id;
      cb.checked = task.preds.indexOf(other.id) !== -1;
      cb.addEventListener('change', function () {
        var at = task.preds.indexOf(other.id);
        if (cb.checked && at === -1) { task.preds.push(other.id); }
        if (!cb.checked && at !== -1) { task.preds.splice(at, 1); }
        markDirty();
        refreshDerived();
      });
      var lb = make('label', '', titleOf(other));
      lb.htmlFor = cb.id;
      lb.dataset.pred = other.id;
      wrap.appendChild(cb);
      wrap.appendChild(lb);
      opts.appendChild(wrap);
    });
    fs.appendChild(opts);
    if (!others.length) { fs.appendChild(make('p', 'pred-none muted', 'No other tasks to depend on.')); }
    body.appendChild(fs);

    var dep = make('p', 'dep-line');
    dep.appendChild(make('span', 'dep-text'));
    var chips = make('span', 'dep-chips');
    chips.setAttribute('aria-hidden', 'true');
    dep.appendChild(chips);
    body.appendChild(dep);

    body.appendChild(make('div', 'field-errors row-errors'));

    var actions = make('div', 'row-actions');
    var up = make('button', 'btn btn-small move-up', 'Move up');
    up.type = 'button';
    up.disabled = index === 0;
    up.addEventListener('click', function () { moveTask(task.id, -1, 'move-up'); });
    var down = make('button', 'btn btn-small move-down', 'Move down');
    down.type = 'button';
    down.disabled = index === plan.tasks.length - 1;
    down.addEventListener('click', function () { moveTask(task.id, 1, 'move-down'); });
    var rm = make('button', 'btn btn-small btn-danger remove', 'Remove');
    rm.type = 'button';
    rm.addEventListener('click', function () { removeTask(task.id); });
    actions.appendChild(up);
    actions.appendChild(down);
    actions.appendChild(rm);
    body.appendChild(actions);

    return li;
  }

  function renderTasks() {
    clearFieldErrors();
    els.taskList.textContent = '';
    plan.tasks.forEach(function (t, i) { els.taskList.appendChild(buildRow(t, i)); });
    els.noTasks.hidden = plan.tasks.length > 0;
    refreshDerived();
  }

  function findRow(id) {
    var rows = els.taskList.children;
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].dataset.taskId === id) { return rows[i]; }
    }
    return null;
  }

  function renderAll() {
    renderPlanList();
    var has = !!plan;
    els.form.hidden = !has;
    els.emptyState.hidden = has;
    if (has) {
      els.title.value = plan.title;
      els.start.value = plan.start_date;
      renderTasks();
    } else {
      els.taskList.textContent = '';
    }
    updateButtons();
    updateStatus();
  }

  // ---------- task actions ----------

  function addTask() {
    if (!plan) { return; }
    var t = { id: newTaskId(), title: 'New task', duration: '1', preds: [] };
    plan.tasks.push(t);
    markDirty();
    renderTasks();
    var row = findRow(t.id);
    if (row) {
      var input = row.querySelector('[name="task-title"]');
      input.focus();
      input.select();
    }
  }

  function removeTask(id) {
    var idx = plan.tasks.findIndex(function (t) { return t.id === id; });
    if (idx === -1) { return; }
    plan.tasks.splice(idx, 1);
    plan.tasks.forEach(function (t) {
      t.preds = t.preds.filter(function (p) { return p !== id; });
    });
    markDirty();
    renderTasks();
    var next = plan.tasks[Math.min(idx, plan.tasks.length - 1)];
    var row = next ? findRow(next.id) : null;
    if (row) { row.querySelector('[name="task-title"]').focus(); }
    else { els.addTask.focus(); }
  }

  function moveTask(id, delta, cls) {
    var idx = plan.tasks.findIndex(function (t) { return t.id === id; });
    var to = idx + delta;
    if (idx === -1 || to < 0 || to >= plan.tasks.length) { return; }
    var t = plan.tasks.splice(idx, 1)[0];
    plan.tasks.splice(to, 0, t);
    markDirty();
    renderTasks();
    var row = findRow(id);
    if (!row) { return; }
    var btn = row.querySelector('.' + cls);
    if (btn.disabled) { btn = row.querySelector(cls === 'move-up' ? '.move-down' : '.move-up'); }
    btn.focus();
  }

  // ---------- server actions ----------

  async function refreshList() {
    var r = await api('GET', API);
    if (r.ok && r.data && Array.isArray(r.data.projects)) {
      projects = r.data.projects;
    } else if (!r.ok) {
      showApiError(r.error);
    }
    renderPlanList();
    return projects;
  }

  function setPlan(p) {
    plan = p;
    dirty = false;
    clearError();
    renderAll();
  }

  async function openPlan(id) {
    if (dirty && !window.confirm('You have unsaved changes. Discard them and open another plan?')) { return; }
    var r = await api('GET', API + '/' + encodeURIComponent(id));
    if (!r.ok) { showApiError(r.error); await refreshList(); return; }
    setPlan(fromServer(r.data));
  }

  async function createPlan() {
    if (dirty && !window.confirm('You have unsaved changes. Discard them and create a new plan?')) { return; }
    var r = await api('POST', API, { title: 'Untitled plan' });
    if (!r.ok) { showApiError(r.error); return; }
    setPlan(fromServer(r.data));
    await refreshList();
    els.title.focus();
    els.title.select();
  }

  function buildPayload() {
    return {
      version: plan.version,
      title: plan.title,
      start_date: plan.start_date,
      tasks: plan.tasks.map(function (t) {
        var d = t.duration.trim();
        return {
          id: t.id,
          title: t.title,
          duration_days: /^[0-9]+$/.test(d) ? parseInt(d, 10) : t.duration,
          predecessors: plan.tasks.filter(function (o) { return t.preds.indexOf(o.id) !== -1; })
            .map(function (o) { return o.id; })
        };
      })
    };
  }

  async function savePlan() {
    if (!plan || saving) { return; }
    clearError();
    clearFieldErrors();
    saving = true;
    updateButtons();
    updateStatus();
    var seq = editSeq;
    var r = await api('PUT', API + '/' + encodeURIComponent(plan.id), buildPayload());
    saving = false;
    updateButtons();
    if (r.ok) {
      if (seq === editSeq) {
        plan = fromServer(r.data);
        dirty = false;
        renderAll();
      } else {
        // Edited while saving: keep local edits, adopt the new version.
        plan.version = r.data.version;
        updateStatus();
      }
      await refreshList();
      return;
    }
    updateStatus();
    if (r.status === 422 && r.error) {
      showError(r.error.message || 'The plan could not be saved.', r.error.details, false);
      applyFieldErrors(r.error.details);
    } else {
      showApiError(r.error);
    }
  }

  async function reloadPlan() {
    if (!plan) { return; }
    var r = await api('GET', API + '/' + encodeURIComponent(plan.id));
    if (!r.ok) {
      showApiError(r.error);
      if (r.status === 404) { await refreshList(); }
      return;
    }
    setPlan(fromServer(r.data));
    await refreshList();
  }

  async function deletePlan() {
    if (!plan || saving) { return; }
    if (!window.confirm('Delete "' + plan.title + '"? This cannot be undone.')) { return; }
    var r = await api('DELETE', API + '/' + encodeURIComponent(plan.id) + '?version=' + encodeURIComponent(plan.version));
    if (!r.ok) { showApiError(r.error); return; }
    plan = null;
    dirty = false;
    clearError();
    var list = await refreshList();
    if (list.length) { await openPlan(list[0].id); }
    else { renderAll(); els.newPlan.focus(); }
  }

  // ---------- wiring ----------

  els.title.addEventListener('input', function () {
    if (!plan) { return; }
    plan.title = els.title.value;
    markDirty();
  });
  els.start.addEventListener('input', function () {
    if (!plan) { return; }
    plan.start_date = els.start.value;
    markDirty();
  });
  els.addTask.addEventListener('click', addTask);
  els.newPlan.addEventListener('click', createPlan);
  els.del.addEventListener('click', deletePlan);
  els.reload.addEventListener('click', reloadPlan);
  els.form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    savePlan();
  });
  window.addEventListener('beforeunload', function (ev) {
    if (dirty) {
      ev.preventDefault();
      ev.returnValue = '';
    }
  });

  async function init() {
    renderAll();
    var list = await refreshList();
    if (list.length) { await openPlan(list[0].id); }
    else { renderAll(); }
  }

  init();
})();
