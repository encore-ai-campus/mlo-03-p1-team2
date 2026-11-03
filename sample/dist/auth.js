'use strict';
// Browser-only demo authentication. Replace with server authentication for production.
const demoAuth = (() => {
  const key = 'tikit.accounts';
  const sessionKey = 'tikit.session';
  const iterations = 210000;
  function accounts() {
    try { const value = JSON.parse(localStorage.getItem(key)); return Array.isArray(value) ? value : []; }
    catch { return []; }
  }
  function publicProfile(account) { const { credentials, ...profile } = account; return profile; }
  function normalized(email) { return email.trim().toLowerCase(); }
  async function derive(password, salt) {
    if (!crypto.subtle) throw new Error('로그인은 localhost 또는 HTTPS 주소에서 이용해 주세요.');
    const material = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
    const bits = await crypto.subtle.deriveBits({name:'PBKDF2', hash:'SHA-256', salt:Uint8Array.from(salt), iterations}, material, 256);
    return Array.from(new Uint8Array(bits), byte => byte.toString(16).padStart(2, '0')).join('');
  }
  function start(account) { sessionStorage.setItem(sessionKey, account.id); return publicProfile(account); }
  return {
    current() { try { const id = sessionStorage.getItem(sessionKey); const account = accounts().find(a => a.id === id); return account ? publicProfile(account) : null; } catch { return null; } },
    async signup(profile, password) {
      if (password.length < 8 || password.length > 128) throw new Error('비밀번호는 8~128자로 입력해 주세요.');
      const email = normalized(profile.email);
      if (accounts().some(a => a.email === email)) throw new Error('이미 가입된 이메일입니다. 로그인해 주세요.');
      const salt = [...crypto.getRandomValues(new Uint8Array(16))];
      const hash = await derive(password, salt);
      const list = accounts();
      if (list.some(a => a.email === email)) throw new Error('이미 가입된 이메일입니다. 로그인해 주세요.');
      const account = {...profile, email, credentials:{algorithm:'PBKDF2-SHA-256', iterations, salt, hash}};
      try { localStorage.setItem(key, JSON.stringify([...list, account])); }
      catch { throw new Error('계정을 저장할 수 없습니다. 브라우저 저장 공간을 확인해 주세요.'); }
      return start(account);
    },
    async login(email, password) {
      const account = accounts().find(a => a.email === normalized(email));
      if (!account || await derive(password, account.credentials.salt) !== account.credentials.hash) throw new Error('이메일 또는 비밀번호가 일치하지 않습니다.');
      return start(account);
    },
    logout() { sessionStorage.removeItem(sessionKey); },
    remove(id) { localStorage.setItem(key, JSON.stringify(accounts().filter(a => a.id !== id))); sessionStorage.removeItem(sessionKey); }
  };
})();
