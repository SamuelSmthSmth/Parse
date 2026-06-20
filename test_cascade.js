const fs = require('fs');
const content = fs.readFileSync('index.html', 'utf8');
if (content.includes('for (let i = currentIndex + 1; i < blocks.length; i++) {')) {
    console.log("SUCCESS");
} else {
    console.log("FAILURE");
}
