"""浏览器端运行时（第二部分）：搜索、语义视图、导出与动效开关。"""

RUNTIME_TAIL = r"""
  Object.keys(nodes).forEach(function (id) {
    nodes[id].addEventListener("click", function () {
      if (state.focus === id) { clearFocus(); return; }
      show(id);
    });
    nodes[id].addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); show(id); }
    });
  });

  search.addEventListener("input", function () {
    var query = search.value.trim().toLowerCase();
    if (!query) { dim(Object.keys(nodes)); return; }
    var keep = [];
    data.nodes.forEach(function (item) {
      var hay = (item.label + " " + item.id + " " + item.kind + " " + item.tags.join(" ")).toLowerCase();
      if (hay.indexOf(query) >= 0) { keep.push(item.id); }
    });
    dim(keep);
    if (keep.length === 1) { show(keep[0]); }
  });

  function inGroup(id, groupId) {
    return nodes[id] && nodes[id].getAttribute("data-group") === groupId;
  }
  function applyView(viewId) {
    state.view = viewId;
    Array.prototype.forEach.call(views.querySelectorAll(".atlas-view-btn"), function (button) {
      button.setAttribute("aria-pressed",
        button.getAttribute("data-view") === viewId ? "true" : "false");
    });
    if (viewId === "__all") { clearFocus(); return; }
    dim(Object.keys(nodes).filter(function (id) { return inGroup(id, viewId); }));
    var first = data.nodes.filter(function (item) { return String(item.group) === viewId; })[0];
    if (first) { show(first.id); }
  }
  if (views.children.length) {
    views.hidden = false;
    views.addEventListener("click", function (event) {
      var button = event.target.closest(".atlas-view-btn");
      if (button) { applyView(button.getAttribute("data-view")); }
    });
  }

  document.getElementById("atlas-fit").addEventListener("click", fit);
  document.getElementById("atlas-theme").addEventListener("click", function () {
    var root = document.documentElement;
    root.setAttribute("data-theme", root.getAttribute("data-theme") === "dark" ? "light" : "dark");
  });
  document.getElementById("atlas-export-svg").addEventListener("click", function () {
    var source = new XMLSerializer().serializeToString(svg.cloneNode(true));
    download("diagram.svg", "image/svg+xml", source);
  });
  document.getElementById("atlas-export-png").addEventListener("click", function () {
    var source = new XMLSerializer().serializeToString(svg.cloneNode(true));
    var image = new Image();
    image.onload = function () {
      var box = svg.viewBox.baseVal;
      var target = document.createElement("canvas");
      target.width = box.width * 2; target.height = box.height * 2;
      var context = target.getContext("2d");
      context.scale(2, 2); context.drawImage(image, 0, 0);
      download("diagram.png", "image/png", target.toDataURL("image/png"), true);
    };
    image.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(source);
  });
  function download(name, type, payload, isDataUrl) {
    var href = isDataUrl ? payload : URL.createObjectURL(new Blob([payload], { type: type }));
    var link = document.createElement("a");
    link.href = href; link.download = name;
    document.body.appendChild(link); link.click(); document.body.removeChild(link);
    if (!isDataUrl) { URL.revokeObjectURL(href); }
  }

  if (data.animation === "trace") {
    Array.prototype.forEach.call(svg.querySelectorAll(".atlas-edge-line"), function (line) {
      line.setAttribute("data-trace", "1");
    });
  }

  fit();
})();
"""
