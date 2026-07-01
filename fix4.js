const fs = require('fs');
const path = require('path');

const dir = path.join(__dirname, 'frontend', 'src');

const injectedAPI = "${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}";

function traverseAndReplace(dirPath) {
    const files = fs.readdirSync(dirPath);
    files.forEach(file => {
        const fullPath = path.join(dirPath, file);
        if (fs.statSync(fullPath).isDirectory()) {
            traverseAndReplace(fullPath);
        } else if (fullPath.endsWith('.jsx')) {
            let content = fs.readFileSync(fullPath, 'utf8');
            
            // Replace `http://localhost:8000
            // Because they are inside backticks: `http://localhost:8000/something/${id}`
            content = content.replace(/http:\/\/localhost:8000/g, injectedAPI);
            
            fs.writeFileSync(fullPath, content);
        }
    });
}

traverseAndReplace(dir);
console.log('Fixed hardcoded localhost inside backticks.');
