// RainTranslator - UI Logic (simplified)
const API = 'http://127.0.0.1:18765';

// Elements
var el = {
  input:   document.getElementById('inputText'),
  output:  document.getElementById('outputText'),
  srcLang: document.getElementById('sourceLang'),
  tgtLang: document.getElementById('targetLang'),
  translateBtn: document.getElementById('translateBtn'),
  inputCount: document.getElementById('inputCount'),
  transTime: document.getElementById('transTime'),
  statusDot: document.getElementById('statusDot'),
  statusText: document.getElementById('statusText'),
};
var translating = false;
var currentMode = 'auto';

// ===== Init =====
(function init() {
  loadLanguages();
  loadMode();
  tickStatus();
  setInterval(tickStatus, 5000);

  el.input.addEventListener('input', function() {
    el.inputCount.textContent = el.input.value.length + ' / 5000';
  });
  el.input.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); doTranslate(); }
  });
  document.getElementById('translateBtn').addEventListener('click', doTranslate);
  document.getElementById('swapBtn').addEventListener('click', swapLangs);
  document.getElementById('clearBtn').addEventListener('click', function(){ el.input.value=''; el.input.focus(); });
  document.getElementById('pasteBtn').addEventListener('click', function(){
    navigator.clipboard.readText().then(t => { el.input.value = t; });
  });
  document.getElementById('copyBtn').addEventListener('click', function(){
    var t = el.output.textContent;
    if (t && !t.includes('翻译结果')) navigator.clipboard.writeText(t).then(function(){ toast('已复制到剪贴板'); });
  });

  // Select arrow rotation (mousedown + blur for reliability)
  document.querySelectorAll('.lang-select').forEach(function(s){
    var wrapper = s.parentElement;
    s.addEventListener('mousedown', function(){
      // Toggle: if already open, close; if closed, open
      if (wrapper.classList.contains('open')) {
        wrapper.classList.remove('open');
      } else {
        wrapper.classList.add('open');
      }
    });
    s.addEventListener('blur', function(){
      wrapper.classList.remove('open');
    });
    s.addEventListener('change', function(){
      wrapper.classList.remove('open');
    });
  });
})();

// ===== Mode =====
function setMode(mode) {
  if (mode === currentMode) return;

  // 切换到"本地"模式，检查是否有模型
  if (mode === 'local') {
    fetch(API+'/api/mode').then(function(r){ return r.json(); }).then(function(d){
      if (!d.has_model) {
        // 没有模型，显示下载面板
        showDownloadPanel();
        return;
      }
      doSetMode(mode);
    });
  } else {
    doSetMode(mode);
  }
}

function doSetMode(mode) {
  fetch(API+'/api/mode', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({mode:mode})
  }).then(function(r){ return r.json(); }).then(function(d){
    if (d.error) { toast(d.error); return; }
    currentMode = d.mode;
    var names = {auto:'自动模式 (本地优先)', local:'仅本地模式', online:'仅在线模式'};
    toast('已切换为' + (names[mode]||mode), 4000);
    loadMode();
    tickStatus();
  }).catch(function(){ toast('模式切换失败'); });
}

// ===== Download Panel =====
var downloadTimer = null;

function showDownloadPanel() {
  document.getElementById('downloadPanel').style.display = 'block';
  document.getElementById('startDownloadBtn').style.display = 'block';
  document.getElementById('cancelDownloadBtn').style.display = 'none';
  document.getElementById('dlProgressText').textContent = '0%';
  document.getElementById('dlProgressFill').style.width = '0%';
}

document.getElementById('closeDownloadBtn').addEventListener('click', function(){
  document.getElementById('downloadPanel').style.display = 'none';
  if (downloadTimer) { clearInterval(downloadTimer); downloadTimer = null; }
});

document.getElementById('startDownloadBtn').addEventListener('click', function(){
  fetch(API+'/api/model/download/start', {method:'POST'}).then(function(r){ return r.json(); }).then(function(d){
    if (d.error) { toast(d.error); return; }
    document.getElementById('startDownloadBtn').style.display = 'none';
    document.getElementById('cancelDownloadBtn').style.display = 'block';
    pollDownloadProgress();
  }).catch(function(){ toast('下载启动失败'); });
});

document.getElementById('cancelDownloadBtn').addEventListener('click', function(){
  if (downloadTimer) { clearInterval(downloadTimer); downloadTimer = null; }
  document.getElementById('downloadPanel').style.display = 'none';
  toast('下载已取消(后台继续)');
});

function pollDownloadProgress() {
  fetch(API+'/api/model/status').then(function(r){ return r.json(); }).then(function(d){
    document.getElementById('dlSource').textContent = d.source || '-';
    document.getElementById('dlSize').textContent = d.total_mb ? d.downloaded_mb + ' / ' + d.total_mb + ' MB' : '-';
    document.getElementById('dlSpeed').textContent = d.speed_mbps ? d.speed_mbps + ' MB/s' : '-';
    var eta = d.eta_seconds;
    if (eta > 60) document.getElementById('dlEta').textContent = Math.round(eta/60) + ' 分钟';
    else if (eta > 0) document.getElementById('dlEta').textContent = eta + ' 秒';
    else document.getElementById('dlEta').textContent = '-';
    document.getElementById('dlProgressFill').style.width = d.progress + '%';
    document.getElementById('dlProgressText').textContent = d.progress + '%';
    
    if (d.done) {
      document.getElementById('downloadPanel').style.display = 'none';
      if (downloadTimer) { clearInterval(downloadTimer); downloadTimer = null; }
      toast('模型下载完成！已切换到本地模式', 4000);
      doSetMode('local');
      tickStatus();
    } else if (d.error) {
      document.getElementById('dlProgressText').textContent = '错误: ' + d.error;
      toast('下载失败: ' + d.error);
      if (downloadTimer) { clearInterval(downloadTimer); downloadTimer = null; }
    }
  }).catch(function(e){
    console.error('Poll error:', e);
  });
  
  if (downloadTimer) clearInterval(downloadTimer);
  downloadTimer = setInterval(pollDownloadProgress, 1000);
}

function loadMode() {
  fetch(API+'/api/mode').then(function(r){ return r.json(); }).then(function(d){
    currentMode = d.mode;
    var btns = document.querySelectorAll('.mode-btn');
    btns.forEach(function(b){
      b.classList.toggle('active', b.getAttribute('data-mode') === d.mode);
      if (b.getAttribute('data-mode') === 'local' && !d.has_model) b.classList.add('disabled');
      else b.classList.remove('disabled');
    });
  });
}

function loadLanguages() {
  fetch(API+'/api/languages').then(function(r){ return r.json(); }).then(function(d){
    var s = el.srcLang, t = el.tgtLang;
    var sv = s.value, tv = t.value;
    s.innerHTML = '<option value="自动检测">[Auto] 自动检测</option>';
    t.innerHTML = '';
    d.languages.forEach(function(l){
      if (l.code !== '自动检测') {
        var o1 = document.createElement('option'); o1.value = l.code; o1.textContent = l.name; s.appendChild(o1);
        var o2 = document.createElement('option'); o2.value = l.code; o2.textContent = l.name; t.appendChild(o2);
      }
    });
    if (sv) s.value = sv;
    if (tv) t.value = tv;
  });
}

function tickStatus() {
  fetch(API+'/api/status').then(function(r){ return r.json(); }).then(function(d){
    if (d.model_loaded) {
      el.statusDot.className = 'status-dot';
      el.statusText.textContent = '本地模型就绪';
    } else if (d.load_error) {
      el.statusDot.className = 'status-dot error';
      el.statusText.textContent = '仅在线模式';
    }
  }).catch(function(){
    el.statusDot.className = 'status-dot error';
    el.statusText.textContent = '后端未连接';
  });
}

// ===== Translate =====
function doTranslate() {
  var text = el.input.value.trim();
  if (!text) { toast('请输入要翻译的文本'); return; }
  if (translating) return;
  translating = true;
  el.translateBtn.classList.add('translating');
  el.translateBtn.querySelector('span').textContent = '翻译中...';
  el.output.innerHTML = '<span class="placeholder">正在翻译...</span>';
  el.output.className = 'text-area output-area';

  fetch(API+'/api/translate', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({text:text, source:el.srcLang.value, target:el.tgtLang.value})
  }).then(function(r){ return r.json(); }).then(function(d){
    if (d.error) {
      el.output.innerHTML = '<span style="color:var(--red)">[X] '+d.error+'</span>';
      el.output.className = 'text-area output-area error';
      el.transTime.textContent = '';
      if (currentMode === 'local') toast('本地翻译失败，可切换为自动或在线模式');
    } else {
      el.output.textContent = d.text;
      el.output.className = 'text-area output-area translated';
      el.transTime.textContent = d.time+'s';
      if (d.notification) toast(d.notification, 3000);
    }
  }).catch(function(e){
    el.output.innerHTML = '<span style="color:var(--red)">[X] 网络错误</span>';
    el.output.className = 'text-area output-area error';
  }).then(function(){
    translating = false;
    el.translateBtn.classList.remove('translating');
    el.translateBtn.querySelector('span').textContent = '翻译';
  });
}

// ===== Tools =====
function swapLangs() {
  var s = el.srcLang.value, t = el.tgtLang.value;
  if (s === '自动检测') return;
  el.srcLang.value = t; el.tgtLang.value = s;
  if (el.output.textContent && el.output.className.indexOf('placeholder')<0) {
    el.input.value = el.output.textContent;
    el.output.innerHTML = '<span class="placeholder">翻译结果将在这里显示</span>';
    el.output.className = 'text-area output-area';
  }
}

var toastTimer;
function toast(msg, dur) {
  dur = dur || 2000;
  var t = document.querySelector('.toast');
  if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function(){ t.classList.remove('show'); }, dur);
}
