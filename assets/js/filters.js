(function () {
  function el(id) { return document.getElementById(id); }
  function uniq(arr) { return Array.from(new Set(arr)).filter(Boolean); }

  document.addEventListener("DOMContentLoaded", function () {
    var raw = el("resource-data");
    if (!raw) return;
    var data = JSON.parse(raw.textContent);

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
        o.value = v; o.textContent = v; sel.appendChild(o);
      });
    }
    fill("f-type", data.map(function (d) { return d.type; }));
    fill("f-status", data.map(function (d) { return d.status; }));
    fill("f-realname", data.map(function (d) { return d.need_realname; }));
    fill("f-openai", data.map(function (d) { return d.openai_compatible; }));
    fill("f-direct", data.map(function (d) { return d.access_note.indexOf("国内可直连") >= 0 ? "是" : "否"; }));

    var fmap = {
      type: "f-type", status: "f-status", realname: "f-realname",
      openai: "f-openai", direct: "f-direct"
    };
    Object.keys(fmap).forEach(function (k) {
      el(fmap[k]).addEventListener("change", applyFilter);
    });

    function applyFilter() {
      var v = {};
      Object.keys(fmap).forEach(function (k) { v[k] = el(fmap[k]).value; });
      document.querySelectorAll("#resource-list .card").forEach(function (c) {
        var ok = true;
        if (v.type && c.dataset.type !== v.type) ok = false;
        if (v.status && c.dataset.status !== v.status) ok = false;
        if (v.realname && c.dataset.realname !== v.realname) ok = false;
        if (v.openai && c.dataset.openai !== v.openai) ok = false;
        if (v.direct) {
          var isDirect = c.dataset.direct === "true" ? "是" : "否";
          if (isDirect !== v.direct) ok = false;
        }
        c.style.display = ok ? "" : "none";
      });
    }

    window.__limzeroData = data;
  });
})();
