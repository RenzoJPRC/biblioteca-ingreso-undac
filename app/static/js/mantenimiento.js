// Auto Logout - 10 Minutos
(function () {
    let timeout;
    const LIMIT = 10 * 60 * 1000; // 10 min

    function resetTimer() {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            window.location.href = '/logout';
        }, LIMIT);
    }

    window.onload = resetTimer;
    document.onmousemove = resetTimer;
    document.onkeypress = resetTimer;
    document.onclick = resetTimer;
    document.onscroll = resetTimer;
})();
