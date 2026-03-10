// static/js/budget-entry.js

document.addEventListener("DOMContentLoaded", function () {
    calculateAggregates();

    const inputs = document.querySelectorAll(".budget-input");
    inputs.forEach(input => {
        input.addEventListener("input", calculateAggregates);
    });
});

function calculateAggregates() {
    const rows = document.querySelectorAll("tr[class^='level-']");
    const monthlyTotals = {};
    const accountTotals = {};

    rows.forEach(row => {
        const level = parseInt(row.className.replace("level-", ""));
        const accountId = row.querySelector("input, span")?.getAttribute("data-account") ||
                          row.querySelector("input, span")?.closest("tr").querySelector("input")?.dataset.account;

        if (!accountId) return;

        const inputs = row.querySelectorAll("input.budget-input");
        let rowTotal = 0;

        inputs.forEach(input => {
            const month = input.dataset.month;
            const amount = parseFloat(input.value) || 0;
            rowTotal += amount;

            monthlyTotals[month] = (monthlyTotals[month] || 0) + amount;
        });

        accountTotals[accountId] = rowTotal;

        const totalCell = document.getElementById(`agg-${accountId}-total`);
        if (totalCell) totalCell.textContent = rowTotal.toFixed(2);
    });

    // لاحقًا يمكننا استخدام monthlyTotals لتحديث المجاميع الشهرية
}
