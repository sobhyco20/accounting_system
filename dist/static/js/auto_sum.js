document.addEventListener('DOMContentLoaded', function () {
    setTimeout(initAutoSum, 500);  // تأخير بسيط لضمان تحميل الحقول
});

function initAutoSum() {
    const months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];

    function calculateTotals() {
        const totals = {};
        months.forEach(month => totals[month] = 0);

        months.forEach(month => {
            const inputs = document.querySelectorAll(`input[name$='-${month}']`);
            inputs.forEach(input => {
                if (!input.disabled && input.value !== '') {
                    totals[month] += parseFloat(input.value) || 0;
                }
            });
        });

        console.clear();
        console.table(totals);

        const container = document.getElementById("budget-summary");
        if (container) {
            container.innerHTML = '<strong>الإجماليات:</strong><br>' +
                months.map(m => `${m.toUpperCase()}: ${totals[m].toFixed(2)}`).join(' | ');
        }
    }

    // أضف Listeners للحقل بعد التأكد من وجوده
    months.forEach(month => {
        const inputs = document.querySelectorAll(`input[name$='-${month}']`);
        inputs.forEach(input => {
            input.addEventListener('input', calculateTotals);
        });
    });

    calculateTotals();  // تشغيل مبدئي
}
