function updateInvoiceItemTotals(row) {
    const qty = row.querySelector('[name$="-quantity"]');
    const price = row.querySelector('[name$="-price"]');
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

    updateInvoiceTotals();
}

function bindEventsToRow(row) {
    ['quantity', 'price', 'tax_rate'].forEach(field => {
        const input = row.querySelector(`[name$="-${field}"]`);
        if (input && !input.dataset.bound) {
            input.addEventListener('input', () => updateInvoiceItemTotals(row));
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

function updateInvoiceTotals() {
    let totalBefore = 0.0;
    let totalTax = 0.0;
    let totalWith = 0.0;

    document.querySelectorAll('tr.form-row').forEach(row => {
        if (!row.classList.contains('empty-form')) {
            const before = parseFloat(row.querySelector('[name$="-total_before_tax"]')?.value || 0);
            const tax = parseFloat(row.querySelector('[name$="-tax_amount"]')?.value || 0);
            const withTax = parseFloat(row.querySelector('[name$="-total_with_tax"]')?.value || 0);

            totalBefore += before;
            totalTax += tax;
            totalWith += withTax;
        }
    });

    const fieldBefore = document.getElementById('id_total_before_tax_value');
    const fieldTax = document.getElementById('id_total_tax_value');
    const fieldWith = document.getElementById('id_total_with_tax_value');

    if (fieldBefore) fieldBefore.value = totalBefore.toFixed(2);
    if (fieldTax) fieldTax.value = totalTax.toFixed(2);
    if (fieldWith) fieldWith.value = totalWith.toFixed(2);
}

function styleTotalFields() {
    const totalFields = [
        document.getElementById('id_total_before_tax_value'),
        document.getElementById('id_total_tax_value'),
        document.getElementById('id_total_with_tax_value')
    ];

    totalFields.forEach(field => {
        if (field) {
            field.style.backgroundColor = '#edee94';
            field.style.fontWeight = 'normal';
            field.style.color = '#000000';
        }
    });
}

// تشغيل عند تحميل الصفحة
window.addEventListener('load', () => {
    console.log(" تم تحميل ملف auto_calc الموحد بنجاح");

    bindAllRows();
    updateInvoiceTotals();
    styleTotalFields();

    const observer = new MutationObserver(() => {
        bindAllRows();
        updateInvoiceTotals();
    });

    document.querySelectorAll('.inline-group').forEach(group => {
        observer.observe(group, { childList: true, subtree: true });
    });

    document.body.addEventListener('input', updateInvoiceTotals);
});
