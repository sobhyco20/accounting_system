function updateReturnItemTotals(row) {
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
}

function bindEventsToReturnRow(row) {
    ['quantity', 'price', 'tax_rate'].forEach(field => {
        const input = row.querySelector(`[name$="-${field}"]`);
        if (input && !input.dataset.bound) {
            input.addEventListener('input', () => {
                updateReturnItemTotals(row);
                calculateReturnTotals();
            });
            input.dataset.bound = "true";
        }
    });
}

function bindAllReturnRows() {
    document.querySelectorAll('tr.form-row').forEach(row => {
        if (!row.classList.contains('empty-form')) {
            bindEventsToReturnRow(row);
        }
    });
}

function calculateReturnTotals() {
    let totalBefore = 0.0;
    let totalTax = 0.0;
    let totalWith = 0.0;

    const totalForms = parseInt(document.getElementById('id_details-TOTAL_FORMS')?.value || 0);
    for (let i = 0; i < totalForms; i++) {
        const before = parseFloat(document.getElementById(`id_details-${i}-total_before_tax`)?.value || 0);
        const tax = parseFloat(document.getElementById(`id_details-${i}-tax_amount`)?.value || 0);
        const withTax = parseFloat(document.getElementById(`id_details-${i}-total_with_tax`)?.value || 0);

        totalBefore += before;
        totalTax += tax;
        totalWith += withTax;
    }

    const summaryRow = document.getElementById("sales-return-summary");
    if (summaryRow) {
        summaryRow.innerHTML = `
            <td colspan="2" style="font-weight:bold;">الإجماليات:</td>
            <td style="color: green;"><strong>${totalWith.toFixed(2)}</strong></td>
            <td style="color: orange;"><strong>${totalTax.toFixed(2)}</strong></td>
            <td style="color: blue;"><strong>${totalBefore.toFixed(2)}</strong></td>
            <td colspan="2"></td>
        `;
    }

    const fieldBefore = document.getElementById('id_total_before_tax_value');
    const fieldTax = document.getElementById('id_total_tax_value');
    const fieldWith = document.getElementById('id_total_with_tax_value');

    if (fieldBefore) fieldBefore.value = totalBefore.toFixed(2);
    if (fieldTax) fieldTax.value = totalTax.toFixed(2);
    if (fieldWith) fieldWith.value = totalWith.toFixed(2);
}

function styleReturnTotalFields() {
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

document.addEventListener('DOMContentLoaded', function () {
    bindAllReturnRows();
    calculateReturnTotals();
    styleReturnTotalFields();

    const observer = new MutationObserver(() => {
        bindAllReturnRows();
        calculateReturnTotals();
    });

    const target = document.querySelector('#salesreturnitem_set-group, .inline-group');
    if (target) {
        observer.observe(target, { childList: true, subtree: true });
    }
});
