(() => {
  'use strict';
  const c = window.owrEditorConfig, el = id => document.getElementById('owr-' + id);
  let snapshot, request = null, busy = false, dirty = false;
  const status = (text, state) => { el('status').textContent = text; el('status').dataset.state = state; };
  function lock(locked) { el('fields').disabled = locked; el('save').disabled = locked; }
  function paragraph(text) {
    const p = document.createElement('p'), a = document.createElement('textarea');
    a.className = 'large-text'; a.rows = 3; a.value = text; a.setAttribute('aria-label', '本文の段落');
    p.append(a); el('paragraphs').append(p);
  }
  function display(pages) {
    const p = pages[c.role]; el('title').value = p.title; el('slug').value = p.slug;
    el('paragraphs').replaceChildren(); p.paragraphs.forEach(paragraph); dirty = false;
  }
  async function call(path, body) {
    const u = new URL(c.api); // WordPress may use ?rest_route= instead of pretty permalinks.
    if (u.searchParams.has('rest_route')) u.searchParams.set('rest_route', u.searchParams.get('rest_route') + path);
    else u.pathname += path;
    const r = await fetch(u, {method: body ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store',
      headers: {'X-WP-Nonce': c.nonce, 'Content-Type': 'application/json'}, ...(body ? {body: JSON.stringify(body)} : {})});
    const value = await r.json(); if (!r.ok) throw Object.assign(new Error('Request failed'), {code: value.code}); return value;
  }
  async function load() {
    lock(true); el('resume').hidden = true;
    try {
      snapshot = await call('editor'); request = snapshot.pending ? snapshot.pending.input : null;
      display(request ? request.pages : snapshot.pages);
      el('generation').textContent = '公開反映済みの世代: ' + snapshot.sequence;
      if (snapshot.drift) {status('保護対象に別経路の変更があります。担当者による確認が必要です。', 'blocked'); return false;}
      if (request) {el('resume').hidden = false; status(snapshot.pending.phase === 'stored' ? 'S3確定済み・WordPress反映待ちです。同じ保存を再開できます。' : '未完了の保存があります。内容を変えず、同じ保存を再開してください。', 'pending');}
      else { lock(false); status('編集できます。保存するまで公開内容は変わりません。', 'ready'); }
      return true;
    } catch (_) {status('状態を取得できません。ログイン状態・権限・登録状態を確認してください。', 'unavailable');return false;}
  }
  async function save() {
    if (busy) return;
    busy = true; lock(true); el('resume').hidden = true; el('reload').disabled = true;
    status('S3への保存・確定とWordPressへの反映を確認しています。', 'saving');
    try {
      await call('save', request); request = null; const loaded = await load();
      if (loaded && snapshot && !snapshot.pending && !snapshot.drift) status('S3確定後、公開内容へ反映しました。', 'applied');
    } catch (error) {
      if (error.code === 'owr_input') {request = null; lock(false); status('入力が対応範囲を超えています。内容を修正して保存してください。', 'invalid'); return;}
      const attempted = request;
      try {
        const current = await call('editor');
        if (!current.pending && !current.drift && current.applied_operation === attempted.operation_id) {
          const loaded = await load();
          if (loaded && !snapshot.pending && snapshot.applied_operation === attempted.operation_id) status('同じ保存の反映完了を確認しました。', 'applied');
        } else if (current.pending && current.pending.input.operation_id === attempted.operation_id) {
          request = current.pending.input; el('resume').hidden = false;
          status(current.pending.phase === 'stored' ? 'S3確定済みですが反映は未完了です。同じ保存を再開してください。' : '保存は未完了です。公開内容を更新していません。同じ保存を再開してください。', 'unresolved');
        } else if (current.sequence !== snapshot.sequence || current.pending || current.drift || error.code === 'owr_save_conflict') {
          status('競合、または別経路の変更を検出しました。古い内容では上書きしません。最新状態を読み直してください。', 'conflict');
        } else {
          el('resume').hidden = false; status('保存の成否を確認できません。同じ要求で再確認できます。', 'unresolved');
        }
      } catch (_) {el('resume').hidden = false; status('通信が途切れ、成否は不明です。同じ保存で再確認してください。', 'unresolved');}
    } finally {busy = false; el('reload').disabled = false;}
  }
  el('form').addEventListener('input', () => {dirty = true;});
  el('add').addEventListener('click', () => {if(el('paragraphs').children.length < 100) {paragraph('');dirty = true;}});
  el('form').addEventListener('submit', event => {
    event.preventDefault(); if (busy || !snapshot || request) return;
    const pages = JSON.parse(JSON.stringify(snapshot.pages));
    pages[c.role] = {title: el('title').value, slug: el('slug').value, paragraphs: [...el('paragraphs').querySelectorAll('textarea')].map(x => x.value)};
    request = {operation_id: 'editor-' + crypto.randomUUID(), expected_sequence: snapshot.sequence, pages}; save();
  });
  el('resume').addEventListener('click', () => {if(request) save();});
  el('reload').addEventListener('click', () => {if(!busy && (!dirty || confirm('未保存の編集内容を破棄して、最新状態を読み直しますか？'))) load();});
  window.addEventListener('beforeunload', event => {if(dirty || busy) {event.preventDefault();event.returnValue = '';}});
  load();
})();
