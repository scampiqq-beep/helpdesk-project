// Theme переключатель (light/dark)
// - применяем через <html data-theme="...">
// - сохраняем в localStorage
// - сохраняем в профиле через /api/ui/theme (если пользователь залогинен)

(function(){
  const root = document.documentElement;
  const btn = document.getElementById('themeToggle');

  function currentTheme(){
    return (root.getAttribute('data-theme') || 'light').toLowerCase();
  }

  function setTheme(theme){
    theme = (theme === 'dark') ? 'dark' : 'light';
    root.setAttribute('data-theme', theme);
    try{ localStorage.setItem('hd_theme', theme); }catch(e){}

    // Пытаемся сохранить на сервер (не критично)
    fetch('/api/ui/theme', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({theme})
    }).catch(()=>{});
  }

  // Инициализация: localStorage → (уже выставлено сервером) → оставляем
  try{
    const saved = (localStorage.getItem('hd_theme') || '').toLowerCase();
    if(saved === 'light' || saved === 'dark'){
      setTheme(saved);
    }
  }catch(e){}

  if(btn){
    btn.addEventListener('click', function(){
      setTheme(currentTheme() === 'dark' ? 'light' : 'dark');
    });
  }
})();
