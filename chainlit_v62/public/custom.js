// 隐藏"说明"和"主题切换"按钮
(function() {
    function hideButtons() {
        // 隐藏"说明"按钮
        document.querySelectorAll('a, button').forEach(function(el) {
            if (el.textContent && el.textContent.trim() === '说明') {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
            }
            if (el.getAttribute('aria-label') === 'Read the documentation') {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
            }
        });
        
        // 隐藏主题切换按钮（太阳图标）
        document.querySelectorAll('button').forEach(function(el) {
            var icon = el.querySelector('svg');
            if (icon) {
                // 检查是否有太阳/月亮相关的 SVG
                var svgContent = icon.outerHTML;
                if (svgContent.includes('sun') || svgContent.includes('moon')) {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                }
            }
        });
    }
    
    // 立即执行 + 定时检查
    hideButtons();
    setInterval(hideButtons, 1000);
    
    // DOM 变化时执行
    var observer = new MutationObserver(hideButtons);
    observer.observe(document.body, { childList: true, subtree: true });
})();
