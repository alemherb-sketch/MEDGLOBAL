const fs = require('fs');
const path = require('path');

const dir = path.join(__dirname, 'frontend', 'src');

const s1 = "(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : '${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}')";

const s2 = "(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')";

function traverseAndReplace(dirPath) {
    const files = fs.readdirSync(dirPath);
    files.forEach(file => {
        const fullPath = path.join(dirPath, file);
        if (fs.statSync(fullPath).isDirectory()) {
            traverseAndReplace(fullPath);
        } else if (fullPath.endsWith('.jsx')) {
            let content = fs.readFileSync(fullPath, 'utf8');
            
            let originalContent = content;
            
            content = content.split(s1).join('API_URL');
            content = content.split(s2).join('API_URL');
            
            if (content !== originalContent && !content.includes("import { API_URL }")) {
                const lines = content.split('\n');
                lines.splice(1, 0, "import { API_URL } from '../config';");
                content = lines.join('\n');
            }
            
            fs.writeFileSync(fullPath, content);
        }
    });
}

traverseAndReplace(dir);
console.log('Fixed everything properly.');
