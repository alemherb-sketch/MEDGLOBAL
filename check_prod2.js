fetch('https://medglobal-frontend.onrender.com/').then(r => r.text()).then(html => {
    const match = html.match(/src="([^"]+\.js)"/);
    if (!match) return console.log('No JS found');
    const jsUrl = match[1];
    fetch('https://medglobal-frontend.onrender.com' + jsUrl).then(r => r.text()).then(code => {
        require('fs').writeFileSync('bundle.js', code);
        console.log('Saved bundle.js!');
    });
});
