// Theme Toggle Script - Include in all pages
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    const checkbox = document.getElementById('checkbox');
    const themeIcon = document.querySelector('.theme-icon-main');
    
    if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark-mode');
        if (checkbox) checkbox.checked = true;
        if (themeIcon) themeIcon.textContent = '☀️';
    } else {
        document.documentElement.classList.remove('dark-mode');
        if (checkbox) checkbox.checked = false;
        if (themeIcon) themeIcon.textContent = '🌙';
    }
}

document.addEventListener('DOMContentLoaded', initTheme);

function toggleTheme() {
    const checkbox = document.getElementById('checkbox');
    let isDark;
    
    if (checkbox) {
        isDark = checkbox.checked;
    } else {
        isDark = document.documentElement.classList.toggle('dark-mode');
    }
    
    if (isDark) {
        document.documentElement.classList.add('dark-mode');
        localStorage.setItem('theme', 'dark');
    } else {
        document.documentElement.classList.remove('dark-mode');
        localStorage.setItem('theme', 'light');
    }
    
    const themeIcon = document.querySelector('.theme-icon-main');
    if (themeIcon) themeIcon.textContent = isDark ? '☀️' : '🌙';
}

// Inject toggle HTML if it doesn't exist
function injectThemeToggle() {
    if (document.querySelector('.theme-switch-wrapper')) return;
    
    const wrapper = document.createElement('div');
    wrapper.className = 'theme-switch-wrapper';
    wrapper.innerHTML = `
        <span class="theme-icon">🌙</span>
        <label class="theme-switch" for="checkbox">
            <input type="checkbox" id="checkbox" onchange="toggleTheme()" />
            <div class="slider round"></div>
        </label>
        <span class="theme-icon">☀️</span>
    `;
    document.body.prepend(wrapper);
    initTheme();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectThemeToggle);
} else {
    injectThemeToggle();
}
