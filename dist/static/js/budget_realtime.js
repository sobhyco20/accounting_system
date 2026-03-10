function updateAggregatesRecursive() {
    const data = {};

    // جمع القيم المدخلة
    document.querySelectorAll('.budget-input').forEach(input => {
        const acc = input.dataset.account;
        const month = input.dataset.month;
        const val = parseFloat(input.value) || 0;

        if (!data[acc]) data[acc] = {};
        data[acc][month] = val;
    });

    // دالة تجميع تكرارية
    function sumForParent(parentId) {
        let result = {};
        for (let m = 1; m <= 12; m++) result[m] = 0;

        const children = accountHierarchy[parentId] || [];
        for (const child of children) {
            let childSums = data[child] || sumForParent(child);
            for (let m = 1; m <= 12; m++) {
                result[m] += childSums[m] || 0;
            }
        }

        // تحديث العناصر في الصفحة
        let yearlyTotal = 0;
        for (let m = 1; m <= 12; m++) {
            const val = result[m];
            const cell = document.getElementById(`agg-${parentId}-m${m}`);
            if (cell) cell.innerText = val.toFixed(2);
            yearlyTotal += val;
        }

        const totalCell = document.getElementById(`agg-${parentId}-total`);
        if (totalCell) totalCell.innerText = yearlyTotal.toFixed(2);

        data[parentId] = result;
        return result;
    }

    // معالجة جميع الحسابات الجذرية
    for (const parentId in accountHierarchy) {
        sumForParent(parentId);
    }
}

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('.budget-input').forEach(input => {
        input.addEventListener('input', updateAggregatesRecursive);
    });
    updateAggregatesRecursive();
});
