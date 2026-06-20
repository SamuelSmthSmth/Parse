const jsdom = require("jsdom");
const { JSDOM } = jsdom;
const html = `<!DOCTYPE html><html><head>
<script src="https://unpkg.com/d3@3/d3.min.js"></script>
<script src="https://unpkg.com/function-plot/dist/function-plot.js"></script>
</head><body><div id="plot"></div>
<script>
  const inst = functionPlot({ target: '#plot', data: [{fn: 'x'}] });
  console.log('Events:', Object.keys(inst._events || {}));
  inst.on('after:draw', () => console.log('DRAWN!'));
</script></body></html>`;
const dom = new JSDOM(html, { runScripts: "dangerously", resources: "usable" });
dom.window.console.log = (msg) => { console.log("LOG:", msg); };
