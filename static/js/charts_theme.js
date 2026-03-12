
(function(){
  function cssVar(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  const muted = cssVar('--muted') || 'rgba(15,23,42,.65)';
  const border = cssVar('--border') || 'rgba(15,23,42,.14)';
  Chart.defaults.color = muted;
  Chart.defaults.borderColor = border;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.boxWidth = 10;
  Chart.defaults.plugins.legend.labels.boxHeight = 10;
})();
