function updatePurchaseItemTotals(row) {
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

    calculatePurchaseTotals();  // ← تحديث الإجماليات
}

function bindPurchaseItemEvents(row) {
    ['quantity', 'unit_price', 'tax_rate'].forEach(field => {
        const input = row.querySelector(`[name$="-${field}"]`);
        if (input && !input.dataset.bound) {
            input.addEventListener('input', () => updatePurchaseItemTotals(row));
            input.dataset.bound = 'true';
        }
    });
}

function bindAllPurchaseRows() {
    document.querySelectorAll('.inline-related tbody tr.form-row').forEach(row => {
        if (!row.classList.contains('empty-form')) {
            bindPurchaseItemEvents(row);
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    bindAllPurchaseRows();
    calculatePurchaseTotals();

    const observer = new MutationObserver(() => {
        bindAllPurchaseRows();
    });

    const container = document.querySelector('#purchaseinvoiceitem_set-group, .inline-group');
    if (container) {
        observer.observe(container, { childList: true, subtree: true });
    }
});
