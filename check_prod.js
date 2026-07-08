fetch('https://medglobal-frontend.onrender.com/').then(r => r.text()).then(html => {
    const match = html.match(/src="([^"]+\.js)"/);
    if (!match) return console.log('No JS found');
    const jsUrl = match[1];
    fetch('https://medglobal-frontend.onrender.com' + jsUrl).then(r => r.text()).then(code => {
        const urls = code.match(/https:\/\/[a-zA-Z0-9-]+\.onrender\.com/g);
        console.log('Backend URLs found:', urls ? [...new Set(urls)] : 'NONE');
        const localhost = code.match(/http:\/\/localhost:8000/g);
        console.log('Localhost found:', localhost ? localhost.length : 0);
    });
});
