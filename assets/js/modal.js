(function () {
  function el(id) { return document.getElementById(id); }
  function esc(s) {
    return (s == null ? "" : String(s)).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function row(k, v) {
    return "<dt>" + esc(k) + "</dt><dd>" + esc(v || "—") + "</dd>";
  }
  function open(slug) {
    var data = window.__limzeroData || [];
    var d = data.find(function (x) { return x.slug === slug; });
    if (!d) return;
    var tags = (d.tags || []).map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join(" ");
    el("modal-card").innerHTML =
      '<button class="modal-close" data-close aria-label="关闭">×</button>' +
      "<h2>" + esc(d.name) + (d.model_name ? ' <span class="model">· ' + esc(d.model_name) + "</span>" : "") + "</h2>" +
      '<span class="badge verify status-' + esc(d.status) + '">' + esc(d.verify_status) + "</span>" +
      '<dl class="fields">' +
      row("分类", d.type) + row("免费类型", d.free_type) + row("额度说明", d.quota) +
      row("有效期", d.validity) + row("是否实名", d.need_realname) + row("OpenAI 兼容", d.openai_compatible) +
      row("访问备注", d.access_note) + row("核验", d.verify_status + "（" + d.verify_time + "）") +
      "</dl>" +
      '<p class="remark"><b>避坑备注：</b>' + esc(d.remark) + "</p>" +
      '<div class="card-tags">' + tags + "</div>" +
      '<div class="detail-actions">' +
      '<a class="btn primary" href="' + esc(d.official_url) + '" target="_blank" rel="noopener noreferrer">官方领取 ↗</a>' +
      '<a class="btn ghost" href="' + esc(d.rule_url) + '" target="_blank" rel="noopener noreferrer">官方规则 ↗</a>' +
      '<a class="btn link" href="/resources/' + encodeURIComponent(d.slug) + '/">查看详情页 ↗</a>' +
      "</div>";
    var m = el("modal");
    m.classList.remove("hidden");
    m.setAttribute("aria-hidden", "false");
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.addEventListener("click", function (e) {
      if (e.target.closest("[data-close]")) {
        el("modal").classList.add("hidden");
        return;
      }
      var card = e.target.closest(".card");
      if (card && card.dataset.slug) open(card.dataset.slug);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") el("modal").classList.add("hidden");
    });
  });
})();
