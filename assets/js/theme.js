(function () {
  var KEY = "limzero-theme";
  function apply(t) {
    document.documentElement.setAttribute("data-theme", t);
    var sw = document.getElementById("theme-toggle");
    if (sw) {
      sw.setAttribute("data-active", t);
      sw.setAttribute("aria-pressed", t === "dark" ? "true" : "false");
    }
  }
  var saved = localStorage.getItem(KEY);
  if (saved) {
    apply(saved);
  } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    apply("dark");
  } else {
    apply("light");
  }
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.onclick = function () {
        var cur = document.documentElement.getAttribute("data-theme");
        var next = cur === "dark" ? "light" : "dark";
        apply(next);
        localStorage.setItem(KEY, next);
      };
    }

    // 导航栏分类下拉（无 JS 也可用：首屏 CSS 默认展开于 :focus-within 之外的降级在 baseof 里无必要，
    // 因为分类页同时出现在页脚，纯 JS 失效时仍有入口）
    var toggle = document.querySelector(".nav-dropdown-toggle");
    var menu = document.querySelector(".nav-dropdown-menu");
    if (toggle && menu) {
      toggle.addEventListener("click", function (e) {
        e.stopPropagation();
        var open = menu.classList.toggle("open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
      document.addEventListener("click", function () {
        menu.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
          menu.classList.remove("open");
          toggle.setAttribute("aria-expanded", "false");
        }
      });
    }
  });
})();
