// تحديث إحصائيات لوحة التحكم بشكل دوري
function updateDashboardStats() {
    fetch('/port/api/dashboard-stats/')
        .then(response => response.json())
        .then(data => {
            // تحديث بطاقات الإحصائيات
            document.getElementById('total-orders').textContent = data.orders.total;
            document.getElementById('active-orders').textContent = data.orders.active;
            
            document.getElementById('total-containers').textContent = data.containers.total;
            document.getElementById('assigned-containers').textContent = data.containers.assigned;
            
            document.getElementById('total-trucks').textContent = data.trucks.total;
            document.getElementById('active-trucks').textContent = data.trucks.active;
            
            document.getElementById('drivers-count').textContent = data.drivers_count;
            
            // تحديث وقت آخر تحديث
            const lastUpdate = new Date(data.last_update);
            document.getElementById('last-update-time').textContent = lastUpdate.toLocaleTimeString('ar-IQ');
            
            // تحديث شريط التقدم
            updateProgressBars(data);
        })
        .catch(error => console.error('خطأ في تحديث البيانات:', error));
}

// تحديث أشرطة التقدم
function updateProgressBars(data) {
    // أوامر التسليم
    const ordersProgress = document.querySelector('#orders-card .progress-bar');
    const ordersPercentage = (data.orders.active / data.orders.total) * 100 || 0;
    ordersProgress.style.width = `${ordersPercentage}%`;
    ordersProgress.setAttribute('aria-valuenow', data.orders.active);
    ordersProgress.setAttribute('aria-valuemax', data.orders.total);
    
    // الحاويات
    const containersProgress = document.querySelector('#containers-card .progress-bar');
    const containersPercentage = (data.containers.assigned / data.containers.total) * 100 || 0;
    containersProgress.style.width = `${containersPercentage}%`;
    
    // الشاحنات
    const trucksProgress = document.querySelector('#trucks-card .progress-bar');
    const trucksPercentage = (data.trucks.active / data.trucks.total) * 100 || 0;
    trucksProgress.style.width = `${trucksPercentage}%`;
}

// تحديث البيانات عند تحميل الصفحة ثم كل 30 ثانية
document.addEventListener('DOMContentLoaded', function() {
    // التحقق من وجود العناصر قبل تحديث البيانات
    if (document.getElementById('total-orders')) {
        updateDashboardStats();
        setInterval(updateDashboardStats, 30000);
    }
}); 