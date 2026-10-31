// ManimGX 站点脚本：首页重画定积分场景、作品页按学科筛选、同时只播一个视频。
(function () {
  "use strict";

  var SVG = "http://www.w3.org/2000/svg";
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

  function el(name, attrs, parent) {
    var node = document.createElementNS(SVG, name);
    for (var k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }

  function wait(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function fade(node, from, to, ms, delay) {
    node.style.opacity = to;
    if (!node.animate) return Promise.resolve();
    return node.animate([{ opacity: from }, { opacity: to }], {
      duration: ms, delay: delay || 0, easing: "ease-in-out", fill: "backwards"
    }).finished;
  }

  function draw(path, ms) {
    var len = path.getTotalLength();
    path.style.strokeDasharray = len;
    path.style.strokeDashoffset = 0;
    if (!path.animate) return Promise.resolve();
    return path.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], {
      duration: ms, easing: "ease-in-out", fill: "backwards"
    }).finished;
  }

  // ------------------------------------------------------------------ 首页
  // 照 DefiniteIntegralArea_scene.py：Axes x∈[0, 2.3]、y∈[0, 4.5]，y = x²，
  // 左端取样的黎曼矩形 4、16、64 个，最后填满 [0, 2] 下的面积。
  function riemann(svg) {
    var X0 = 64, X1 = 604, Y0 = 380, Y1 = 30;
    var sx = function (x) { return X0 + (x / 2.3) * (X1 - X0); };
    var sy = function (y) { return Y0 - (y / 4.5) * (Y0 - Y1); };
    var f = function (x) { return x * x; };
    var ink = "#142536", muted = "#41556a";
    var blue = [44, 125, 160], green = [62, 142, 78];

    function mix(t) {
      var c = blue.map(function (b, i) { return Math.round(b + (green[i] - b) * t); });
      return "rgb(" + c.join(",") + ")";
    }

    var layer = {};
    function reset() {
      while (svg.lastChild && svg.lastChild.nodeName !== "desc") svg.removeChild(svg.lastChild);

      var defs = el("defs", {}, svg);
      var grad = el("linearGradient", { id: "area-grad", x1: "0", x2: "1", y1: "0", y2: "0" }, defs);
      el("stop", { offset: "0", "stop-color": mix(0) }, grad);
      el("stop", { offset: "1", "stop-color": mix(1) }, grad);
      var tip = el("marker", { id: "tip", viewBox: "0 0 10 10", refX: "8", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" }, defs);
      el("path", { d: "M0 0L10 5L0 10z", fill: muted }, tip);

      layer.area = el("path", {
        d: areaPath(), fill: "url(#area-grad)", "fill-opacity": "0.85", opacity: "0"
      }, svg);
      layer.rects = el("g", {}, svg);

      var axes = el("g", { stroke: muted, "stroke-width": "2", fill: "none" }, svg);
      layer.xAxis = el("path", { d: "M" + X0 + " " + Y0 + "H" + (X1 + 14), "marker-end": "url(#tip)" }, axes);
      layer.yAxis = el("path", { d: "M" + X0 + " " + Y0 + "V" + (Y1 - 14), "marker-end": "url(#tip)" }, axes);

      layer.ticks = el("g", { "font-size": "20", "text-anchor": "middle", opacity: "0" }, svg);
      [0.5, 1, 1.5, 2].forEach(function (x) {
        el("line", { x1: sx(x), x2: sx(x), y1: Y0 - 5, y2: Y0 + 5, stroke: muted, "stroke-width": "1.5" }, layer.ticks);
        el("text", { x: sx(x), y: Y0 + 26 }, layer.ticks).textContent = x;
      });
      [1, 2, 3, 4].forEach(function (y) {
        el("line", { x1: X0 - 5, x2: X0 + 5, y1: sy(y), y2: sy(y), stroke: muted, "stroke-width": "1.5" }, layer.ticks);
        el("text", { x: X0 - 18, y: sy(y) + 6 }, layer.ticks).textContent = y;
      });
      el("text", { x: X1 + 30, y: Y0 + 6, "font-style": "italic", "font-size": "22" }, layer.ticks).textContent = "x";
      el("text", { x: X0, y: Y1 - 26, "font-style": "italic", "font-size": "22" }, layer.ticks).textContent = "y";

      var d = "";
      for (var i = 0; i <= 80; i++) {
        var x = (2 * i) / 80;
        d += (i ? "L" : "M") + sx(x).toFixed(2) + " " + sy(f(x)).toFixed(2);
      }
      layer.curve = el("path", { d: d, fill: "none", stroke: "#9a5f00", "stroke-width": "4", "stroke-linecap": "round" }, svg);
      layer.fLabel = el("text", { x: sx(2) + 14, y: sy(4) + 8, "font-size": "22", "font-style": "italic", fill: "#9a5f00", opacity: "0" }, svg);
      layer.fLabel.style.fill = "#9a5f00";
      layer.fLabel.textContent = "y = x²";

      layer.count = el("text", { x: X0 + 18, y: Y1 + 8, "font-size": "21", "class": "cjk", opacity: "0" }, svg);
      layer.count.style.fill = ink;
    }

    function areaPath() {
      var d = "M" + sx(0) + " " + Y0;
      for (var i = 0; i <= 80; i++) {
        var x = (2 * i) / 80;
        d += "L" + sx(x).toFixed(2) + " " + sy(f(x)).toFixed(2);
      }
      return d + "L" + sx(2) + " " + Y0 + "Z";
    }

    function rects(n) {
      var g = el("g", { opacity: "0" }, layer.rects);
      var dx = 2 / n;
      for (var i = 0; i < n; i++) {
        var x = i * dx, h = f(x);
        if (h === 0) continue;
        el("rect", {
          x: sx(x), y: sy(h), width: sx(dx) - sx(0), height: Y0 - sy(h),
          fill: mix(n > 1 ? i / (n - 1) : 0), "fill-opacity": "0.75",
          stroke: "#0c1016", "stroke-width": n > 16 ? "0.5" : "1"
        }, g);
      }
      return g;
    }

    var lines = document.querySelectorAll(".plot-code li");
    function code(step) {
      lines.forEach(function (li) { li.classList.toggle("on", Number(li.dataset.step) === step); });
    }

    var replay = document.getElementById("replay");
    var running = false;

    function finalState() {
      reset();
      [layer.ticks, layer.fLabel, layer.count].forEach(function (n) { n.style.opacity = 1; });
      layer.area.style.opacity = 1;
      layer.count.textContent = "矩形越细，面积越接近定积分";
      code(2);
    }

    async function play() {
      running = true;
      if (replay) replay.hidden = true;
      reset();
      code(-1);
      await Promise.all([draw(layer.xAxis, 700), draw(layer.yAxis, 700), fade(layer.ticks, 0, 1, 700)]);
      await Promise.all([draw(layer.curve, 1300), fade(layer.fLabel, 0, 1, 900, 400)]);
      await wait(400);

      code(0);
      var current = rects(4);
      layer.count.textContent = "分成 4 个矩形";
      await Promise.all([fade(current, 0, 1, 1100), fade(layer.count, 0, 1, 500)]);
      await wait(700);

      code(1);
      for (var n of [16, 64]) {
        var next = rects(n);
        layer.count.textContent = "分成 " + n + " 个矩形";
        var old = current;
        await Promise.all([fade(old, 1, 0, 1000), fade(next, 0, 1, 1000)]);
        old.remove();
        current = next;
        await wait(600);
      }

      code(2);
      layer.count.textContent = "矩形越细，面积越接近定积分";
      await Promise.all([fade(current, 1, 0, 1300), fade(layer.area, 0, 1, 1300)]);
      current.remove();
      running = false;
      if (replay) replay.hidden = false;
    }

    if (replay) {
      replay.addEventListener("click", function () {
        if (running) return;
        if (reduce.matches) finalState();
        else play();
      });
    }

    if (reduce.matches) {
      finalState();
      if (replay) replay.hidden = true;
    } else {
      play();
    }
  }

  var plot = document.getElementById("riemann");
  if (plot) riemann(plot);

  // ------------------------------------------------------------------ 作品页筛选
  var filter = document.querySelector(".filter");
  if (filter) {
    var status = document.getElementById("filter-status");
    var names = { all: "全部", math: "数学", physics: "物理", cs: "计算机" };
    filter.addEventListener("click", function (event) {
      var button = event.target.closest("button[data-filter]");
      if (!button) return;
      var key = button.dataset.filter;
      filter.querySelectorAll("button").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b === button));
      });
      var shown = 0;
      document.querySelectorAll(".work").forEach(function (work) {
        var visible = key === "all" || work.dataset.subject === key;
        work.hidden = !visible;
        if (!visible) {
          var v = work.querySelector("video");
          if (v) v.pause();
        } else shown++;
      });
      status.textContent = (key === "all" ? "共 " : names[key] + "：") + shown + " 集";
    });
  }

  // ------------------------------------------------------------------ 同一时间只播一个视频
  document.addEventListener("play", function (event) {
    document.querySelectorAll("video").forEach(function (v) {
      if (v !== event.target) v.pause();
    });
  }, true);
})();
