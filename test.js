const fs = require('fs');
const jsdom = require("jsdom");
const { JSDOM } = jsdom;

const html = `
<!DOCTYPE html>
<html>
<head>
  <script src="https://unpkg.com/function-plot/dist/function-plot.js"></script>
</head>
<body>
  <div id="plot"></div>
  <script>
    try {
      functionPlot({
        target: '#plot',
        data: [{ fn: 'x^2' }]
      });
      console.log("SUCCESS");
    } catch (e) {
      console.error(e.toString());
    }
  </script>
</body>
</html>
`;
const dom = new JSDOM(html, { runScripts: "dangerously", resources: "usable" });
dom.window.console.error = (msg) => { console.log("ERROR:", msg); };
dom.window.console.log = (msg) => { console.log("LOG:", msg); };
