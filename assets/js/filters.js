(function () {
  function el(id) { return document.getElementById(id); }
  function uniq(arr) { return Array.from(new Set(arr)).filter(Boolean); }

  // 容错解析：处理正常数组，也兜底「字符串套 JSON」的双重编码情况
  function parseData(raw) {
    if (!raw) return [];
    var text = String(raw).trim();
    if (!text) return [];
    var data = JSON.parse(text);
    if (typeof data === "string") data = JSON.parse(data);
    return Array.isArray(data) ? data : [];
  }

  document.addEventListener("DOMContentLoaded", function () {
    var raw = el("resource-data");
    if (!raw) return;
    var data = parseData(raw.textContent);
    if (!data.length) return;

    // 统计面板（页面保留 #stats 时才渲染，否则跳过，避免报错）
    var stEl = el("stats");
    if (stEl) {
      var types = {};
      var direct = 0;
      data.forEach(function (d) {
        types[d.type] = 1;
        if ((d.access_note || "").indexOf("国内可直连") >= 0) direct++;
      });
      stEl.innerHTML =
        '<div class="stat"><b>' + data.length + '</b><span>有效资源</span></div>' +
        '<div class="stat"><b>' + Object.keys(types).length + '</b><span>覆盖分类</span></div>' +
        '<div class="stat"><b>' + direct + '</b><span>国内可直连</span></div>';
    }

    // 填充筛选项
    function fill(id, label, vals) {
      var sel = el(id);
      sel.innerHTML = '<option value="">' + label + '</option>';
      uniq(vals).forEach(function (v) {
        var o = document.createElement("option");
        o.value = v; o.textContent = v;
        sel.appendChild(o);
      });
    }
    fill("f-type", "分类", data.map(function (d) { return d.type; }));
    fill("f-realname", "是否实名", data.map(function (d) { return d.need_realname; }));
    fill("f-openai", "OpenAI 兼容", data.map(function (d) { return d.openai_compatible; }));
    fill("f-direct", "国内直连", data.map(function (d) { return (d.access_note || "").indexOf("国内可直连") >= 0 ? "是" : "否"; }));
    fill("f-free", "免费类型", data.map(function (d) { return d.free_type; }));
    fill("f-credit", "信用卡要求", data.map(function (d) { return d.need_credit_card; }));

    // 当前筛选 + 搜索状态
    var state = { type: "", realname: "", openai: "", direct: "", q: "", credit: "" };

    var fmap = {
      "f-type": "type", "f-realname": "realname",
      "f-openai": "openai", "f-direct": "direct", "f-free": "free", "f-credit": "credit"
    };
    Object.keys(fmap).forEach(function (id) {
      el(id).addEventListener("change", function () {
        state[fmap[id]] = el(id).value;
        applyFilter();
      });
    });

    var searchInput = el("search-input");
    if (searchInput) {
      searchInput.addEventListener("input", function () {
        state.q = searchInput.value.trim().toLowerCase();
        applyFilter();
      });
    }

    function matchSearch(d, q) {
      if (!q) return true;
      var hay = [d.name, d.model_name, (d.tags || []).join(" "), d.type].join(" ").toLowerCase();
      return hay.indexOf(q) >= 0;
    }

    function applyFilter() {
      var shown = 0;
      document.querySelectorAll("#resource-list .card").forEach(function (c) {
        var ok = true;
        if (state.type && c.dataset.type !== state.type) ok = false;
        if (state.realname && c.dataset.realname !== state.realname) ok = false;
        if (state.openai && c.dataset.openai !== state.openai) ok = false;
        if (state.direct) {
          var isDirect = c.dataset.direct === "true" ? "是" : "否";
          if (isDirect !== state.direct) ok = false;
        }
        if (state.free && c.dataset.free !== state.free) ok = false;
        if (state.credit && c.dataset.credit !== state.credit) ok = false;
        // 与搜索联动：优先用卡片的 data-search（含名称/模型/分类/标签/避坑备注），回退到可见文本
        if (ok && state.q) {
          var text = (c.dataset.search || c.textContent || "").toLowerCase();
          if (text.indexOf(state.q) < 0) ok = false;
        }
        c.style.display = ok ? "" : "none";
        if (ok) shown++;
      });
      var nr = el("no-results");
      if (nr) nr.hidden = shown !== 0;
    }

    window.__limzeroData = data;
  });
})();
