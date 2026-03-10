function calculatePurchaseTotals() {
    let totalBefore = 0.0;
    let totalTax = 0.0;
    let totalWith = 0.0;

    const totalForms = parseInt(document.getElementById('id_purchaseinvoiceitem_set-TOTAL_FORMS')?.value || 0);
    for (let i = 0; i < totalForms; i++) {
        const before = parseFloat(document.getElementById(`id_purchaseinvoiceitem_set-${i}-total_before_tax`)?.value || 0);
        const tax = parseFloat(document.getElementById(`id_purchaseinvoiceitem_set-${i}-tax_amount`)?.value || 0);
        const withTax = parseFloat(document.getElementById(`id_purchaseinvoiceitem_set-${i}-total_with_tax`)?.value || 0);

        totalBefore += before;
        totalTax += tax;
        totalWith += withTax;
    }

    // تحديث الحقول
    const fieldBefore = document.getElementById('id_total_before_tax_value');
    const fieldTax = document.getElementById('id_total_tax_value');
    const fieldWith = document.getElementById('id_total_with_tax_value');

    if (fieldBefore) fieldBefore.value = totalBefore.toFixed(2);
    if (fieldTax) fieldTax.value = totalTax.toFixed(2);
    if (fieldWith) fieldWith.value = totalWith.toFixed(2);
}

function stylePurchaseTotalFields() {
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
    calculatePurchaseTotals();
    stylePurchaseTotalFields();

    document.body.addEventListener('input', calculatePurchaseTotals);
});
