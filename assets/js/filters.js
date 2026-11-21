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

  function isDirect(d) {
    return (d.access_note || "").indexOf("国内可直连") >= 0;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var raw = el("resource-data");
    if (!raw) return;
    var data = parseData(raw.textContent);
    if (!data.length) return;

    // slug → 数据对象。筛选与搜索都走这份 JSON，不再依赖卡片上的 data-search，
    // 这样 161 张卡不用各自背一份 name+model+tags+remark 的搜索文本（省约 60KB HTML）。
    var bySlug = {};
    data.forEach(function (d) {
      d._direct = isDirect(d);
      d._hay = [d.name, d.model_name, (d.tags || []).join(" "), d.type, d.remark, d.quota]
        .join(" ").toLowerCase();
      bySlug[d.slug] = d;
    });

    // 统计面板已改为 Hugo 构建期静态输出（见 layouts/index.html），
    // 这里不再注入，避免 JS 执行后布局位移。

    function fill(id, label, vals) {
      var sel = el(id);
      if (!sel) return;
      sel.innerHTML = '<option value="">' + label + "</option>";
      uniq(vals).forEach(function (v) {
        var o = document.createElement("option");
        o.value = v; o.textContent = v;
        sel.appendChild(o);
      });
    }
    fill("f-type", "分类", data.map(function (d) { return d.type; }));
    fill("f-realname", "是否实名", data.map(function (d) { return d.need_realname; }));
    fill("f-openai", "OpenAI 兼容", data.map(function (d) { return d.openai_compatible; }));
    fill("f-direct", "国内直连", data.map(function (d) { return d._direct ? "是" : "否"; }));
    fill("f-free", "免费类型", data.map(function (d) { return d.free_type; }));
    fill("f-credit", "信用卡要求", data.map(function (d) { return d.need_credit_card; }));

    // free 必须初始化，否则「清空筛选」时既 reset 不到、也判断不出默认值
    var state = { type: "", realname: "", openai: "", direct: "", free: "", credit: "", q: "" };

    var fmap = {
      "f-type": "type", "f-realname": "realname",
      "f-openai": "openai", "f-direct": "direct", "f-free": "free", "f-credit": "credit"
    };
    Object.keys(fmap).forEach(function (id) {
      var node = el(id);
      if (!node) return;
      node.addEventListener("change", function () {
        state[fmap[id]] = node.value;
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

    var resetBtn = el("reset-filters");
    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        Object.keys(state).forEach(function (k) { state[k] = ""; });
        Object.keys(fmap).forEach(function (id) { var n = el(id); if (n) n.value = ""; });
        if (searchInput) searchInput.value = "";
        applyFilter();
      });
    }

    function applyFilter() {
      var shown = 0;
      var cards = document.querySelectorAll("#resource-list .card");
      for (var i = 0; i < cards.length; i++) {
        var c = cards[i];
        var d = bySlug[c.dataset.slug];
        var ok = true;
        if (!d) {
          ok = false;
        } else {
          if (state.type && d.type !== state.type) ok = false;
          else if (state.realname && d.need_realname !== state.realname) ok = false;
          else if (state.openai && d.openai_compatible !== state.openai) ok = false;
          else if (state.direct && (d._direct ? "是" : "否") !== state.direct) ok = false;
          else if (state.free && d.free_type !== state.free) ok = false;
          else if (state.credit && d.need_credit_card !== state.credit) ok = false;
          else if (state.q && d._hay.indexOf(state.q) < 0) ok = false;
        }
        c.style.display = ok ? "" : "none";
        if (ok) shown++;
      }
      var nr = el("no-results");
      if (nr) nr.hidden = shown !== 0;
    }

    window.__limzeroData = data;
  });
})();
