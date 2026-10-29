(function () {
  var KEY = "limzero-theme";
  function apply(t) { document.documentElement.setAttribute("data-theme", t); }
  var saved = localStorage.getItem(KEY);
  if (saved) {
    apply(saved);
  } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    apply("dark");
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
  });
})();
