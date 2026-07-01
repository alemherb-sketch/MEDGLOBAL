const fs = require('fs');
const path = require('path');

const dir = path.join(__dirname, 'frontend', 'src');

function traverseAndReplace(dirPath) {
    const files = fs.readdirSync(dirPath);
    files.forEach(file => {
        const fullPath = path.join(dirPath, file);
        if (fs.statSync(fullPath).isDirectory()) {
            traverseAndReplace(fullPath);
        } else if (fullPath.endsWith('.jsx')) {
            let content = fs.readFileSync(fullPath, 'utf8');
            content = content.replace(/'http:\/\/localhost:8000/g, "`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`");
            fs.writeFileSync(fullPath, content);
        }
    });
}

traverseAndReplace(dir);
console.log('Replacement complete.');
