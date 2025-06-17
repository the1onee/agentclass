// تحميل البيانات باستخدام AJAX
function loadStats() {
    fetch('/api/dashboard-stats/')
        .then(response => response.json())
        .then(data => {
            document.getElementById('orders-count').textContent = data.orders;
            document.getElementById('containers-count').textContent = data.containers;
        });
}

window.addEventListener('load', loadStats); 