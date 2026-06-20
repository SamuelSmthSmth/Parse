const jsdom = require("jsdom");
const { JSDOM } = jsdom;
const html = `<!DOCTYPE html><html><head>
<script src="https://unpkg.com/d3@3/d3.min.js"></script>
<script src="https://unpkg.com/function-plot/dist/function-plot.js"></script>
</head><body><div id="plot"></div>
<script>
  try {
      const inst = functionPlot({ target: '#plot', data: [{fn: 'x'}] });
      console.log('Type of inst.on:', typeof inst.on);
      if (typeof inst.on === 'function') {
          inst.on('after:draw', () => console.log('DRAWN EVENT'));
      }
  } catch (e) { console.log("ERR", e); }
</script></body></html>`;
const dom = new JSDOM(html, { runScripts: "dangerously", resources: "usable" });
dom.window.console.log = (msg) => { console.log("LOG:", msg); };
