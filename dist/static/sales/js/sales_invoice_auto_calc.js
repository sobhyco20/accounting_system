function updateSalesItemTotals(row) {
    const qty = row.querySelector('[name$="-quantity"]');
    const price = row.querySelector('[name$="-unit_price"]');
    const taxRate = row.querySelector('[name$="-tax_rate"]');
    const totalBefore = row.querySelector('[name$="-total_before_tax"]');
    const tax = row.querySelector('[name$="-tax_amount"]');
    const totalWith = row.querySelector('[name$="-total_with_tax"]');

    if (qty && price && taxRate && totalBefore && tax && totalWith) {
        const q = parseFloat(qty.value) || 0;
        const p = parseFloat(price.value) || 0;
        const r = parseFloat(taxRate.value) || 0;
        const before = q * p;
        const t = before * r / 100;
        const withTax = before + t;

        totalBefore.value = before.toFixed(2);
        tax.value = t.toFixed(2);
        totalWith.value = withTax.toFixed(2);
    }
}

function bindEventsToRow(row) {
    ['quantity', 'unit_price', 'tax_rate'].forEach(field => {
        const input = row.querySelector(`[name$="-${field}"]`);
        if (input && !input.dataset.bound) {
            input.addEventListener('input', () => updateSalesItemTotals(row));
            input.dataset.bound = "true";
        }
    });
}

function bindAllRows() {
    document.querySelectorAll('tr.form-row').forEach(row => {
        if (!row.classList.contains('empty-form')) {
            bindEventsToRow(row);
        }
    });
}

// تشغيل عند تحميل الصفحة
window.addEventListener('load', () => {
    bindAllRows();

    // مراقبة الإضافات باستخدام MutationObserver
    const observer = new MutationObserver(() => {
        bindAllRows();
    });

    const target = document.querySelector('#salesinvoiceitem_set-group, .inline-group');
    if (target) {
        observer.observe(target, { childList: true, subtree: true });
    }
});
