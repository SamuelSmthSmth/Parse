const jsdom = require("jsdom");
const { JSDOM } = jsdom;
const html = `<!DOCTYPE html><html><head>
<script src="https://unpkg.com/d3@3/d3.min.js"></script>
<script src="https://unpkg.com/function-plot/dist/function-plot.js"></script>
</head><body><div id="plot"></div>
<script>
  try {
      functionPlot({ target: '#plot', disableZoom: true, data: [{fn: 'x'}] });
      const svg = document.querySelector('#plot svg');
      const originLines = svg.querySelectorAll('.origin line');
      let xZero = null, yZero = null;
      originLines.forEach(l => {
        if (l.getAttribute('x1') === l.getAttribute('x2')) xZero = l.getAttribute('x1');
        if (l.getAttribute('y1') === l.getAttribute('y2')) yZero = l.getAttribute('y1');
      });
      console.log('xZero:', xZero, 'yZero:', yZero);
  } catch (e) { console.log("ERR", e); }
</script></body></html>`;
const dom = new JSDOM(html, { runScripts: "dangerously", resources: "usable" });
dom.window.console.log = (msg) => { console.log("LOG:", msg); };
