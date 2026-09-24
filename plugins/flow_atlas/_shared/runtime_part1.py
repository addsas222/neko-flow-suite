"""浏览器端运行时（第一部分）：视图状态、平移缩放、聚焦与详情面板。"""

RUNTIME_HEAD = r"""
(function () {
  "use strict";
  var canvas = document.getElementById("atlas-canvas");
  var svg = canvas.querySelector("svg");
  var data = JSON.parse(document.getElementById("atlas-data").textContent);
  var detail = document.getElementById("atlas-detail");
  var views = document.getElementById("atlas-views");
  var search = document.getElementById("atlas-search");
  var state = { scale: 1, tx: 0, ty: 0, focus: null, view: "__all" };

  function apply() {
    svg.setAttribute("transform",
      "translate(" + state.tx + " " + state.ty + ") scale(" + state.scale + ")");
  }
  function fit() {
    var rect = canvas.getBoundingClientRect();
    var box = svg.viewBox.baseVal;
    var scale = Math.min(rect.width / (box.width || 1), rect.height / (box.height || 1));
    state.scale = Math.max(0.2, Math.min(2.5, scale));
    state.tx = 0; state.ty = 0; apply();
  }

  canvas.addEventListener("wheel", function (event) {
    event.preventDefault();
    state.scale = Math.max(0.2, Math.min(4, state.scale * (event.deltaY < 0 ? 1.1 : 0.9)));
    apply();
  }, { passive: false });

  var drag = null;
  canvas.addEventListener("pointerdown", function (event) {
    drag = { x: event.clientX, y: event.clientY, tx: state.tx, ty: state.ty };
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener("pointermove", function (event) {
    if (!drag) { return; }
    state.tx = drag.tx + (event.clientX - drag.x);
    state.ty = drag.ty + (event.clientY - drag.y);
    apply();
  });
  canvas.addEventListener("pointerup", function () { drag = null; });
  canvas.addEventListener("pointercancel", function () { drag = null; });

  var nodes = {};
  Array.prototype.forEach.call(svg.querySelectorAll(".atlas-node"), function (element) {
    nodes[element.getAttribute("data-node")] = element;
  });
  var edges = {};
  Array.prototype.forEach.call(svg.querySelectorAll(".atlas-edge"), function (element) {
    edges[element.getAttribute("data-edge")] = element;
  });

  function record(id) {
    for (var i = 0; i < data.nodes.length; i += 1) {
      if (data.nodes[i].id === id) { return data.nodes[i]; }
    }
    return null;
  }
  function neighbours(id) {
    var item = record(id);
    if (!item) { return []; }
    return item.links.concat(item.linked_from).concat([id]);
  }
  function touches(id, keep) {
    var item = record(id);
    if (!item) { return false; }
    return item.links.some(function (other) { return keep.indexOf(other) >= 0; }) ||
      item.linked_from.some(function (other) { return keep.indexOf(other) >= 0; });
  }
  function dim(keep) {
    Object.keys(nodes).forEach(function (id) {
      nodes[id].setAttribute("data-dim", keep.indexOf(id) >= 0 ? "0" : "1");
    });
    Object.keys(edges).forEach(function (edgeId) {
      var endpoints = edgeId.split("~");
      var visible = keep.indexOf(endpoints[0]) >= 0 && keep.indexOf(endpoints[1]) >= 0;
      edges[edgeId].setAttribute("data-dim", visible ? "0" : "1");
    });
  }
  function clearFocus() {
    state.focus = null;
    dim(Object.keys(nodes));
    detail.hidden = true;
  }
  function show(id) {
    var item = record(id);
    if (!item) { return; }
    state.focus = id;
    dim(neighbours(id));
    detail.hidden = false;
    var rows = row("kind", item.kind) + row("group", item.group) + row("tags", item.tags.join(", "));
    var list = neighbours(id).filter(function (other) { return other !== id; })
      .map(function (other) { return "<li>" + other + "</li>"; }).join("");
    detail.innerHTML = "<h2></h2><dl>" + rows + "</dl><p></p><h3>relations</h3><ul>" + list + "</ul>";
    detail.querySelector("h2").textContent = item.label;
    detail.querySelector("p").textContent = item.detail || "no detail recorded";
    function row(label, value) { return "<dt>" + label + "</dt><dd>" + (value || "-") + "</dd>"; }
  }
"""
