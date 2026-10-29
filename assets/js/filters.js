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

    // 统计面板
    var s = { verified: 0, pending: 0, expired: 0 };
    data.forEach(function (d) { if (s[d.status] != null) s[d.status]++; });
    el("stats").innerHTML =
      '<div class="stat"><b>' + data.length + '</b><span>有效资源</span></div>' +
      '<div class="stat warn"><b>' + s.pending + '</b><span>待复核</span></div>' +
      '<div class="stat off"><b>' + s.expired + '</b><span>已失效</span></div>';

    // 填充筛选项
    function fill(id, vals) {
      var sel = el(id);
      sel.innerHTML = '<option value="">全部</option>';
      uniq(vals).forEach(function (v) {
        var o = document.createElement("option");
        o.value = v; o.textContent = v;
        sel.appendChild(o);
      });
    }
    fill("f-type", data.map(function (d) { return d.type; }));
    fill("f-status", data.map(function (d) { return d.status; }));
    fill("f-realname", data.map(function (d) { return d.need_realname; }));
    fill("f-openai", data.map(function (d) { return d.openai_compatible; }));
    fill("f-direct", data.map(function (d) { return d.access_note.indexOf("国内可直连") >= 0 ? "是" : "否"; }));

    // 当前筛选 + 搜索状态
    var state = { type: "", status: "", realname: "", openai: "", direct: "", q: "" };

    var fmap = {
      "f-type": "type", "f-status": "status", "f-realname": "realname",
      "f-openai": "openai", "f-direct": "direct"
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
        if (state.status && c.dataset.status !== state.status) ok = false;
        if (state.realname && c.dataset.realname !== state.realname) ok = false;
        if (state.openai && c.dataset.openai !== state.openai) ok = false;
        if (state.direct) {
          var isDirect = c.dataset.direct === "true" ? "是" : "否";
          if (isDirect !== state.direct) ok = false;
        }
        // 与搜索联动：用卡片上已渲染的可见文本做匹配（名称/模型/标签/分类）
        if (ok && state.q) {
          var text = (c.textContent || "").toLowerCase();
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
