document.addEventListener('DOMContentLoaded', function () {

    // دالة لإظهار وإخفاء الحقول بناء على طريقة السداد
    function toggleFields() {
        var methodField = document.getElementById('id_method');
        var treasuryBoxField = document.querySelector('.form-row.field-treasury_box');
        var bankAccountField = document.querySelector('.form-row.field-bank_account');

        if (!methodField) return;

        treasuryBoxField.style.display = 'none';
        bankAccountField.style.display = 'none';

        if (methodField.value === 'cash') {
            treasuryBoxField.style.display = 'block';
        } else if (methodField.value === 'bank') {
            bankAccountField.style.display = 'block';
        }
    }

    // تشغيل الدالة عند تحميل الصفحة
    toggleFields();

    // تشغيلها عند تغيير طريقة السداد
    var methodField = document.getElementById('id_method');
    if (methodField) {
        methodField.addEventListener('change', toggleFields);
    }

    // تحميل الفواتير بناء على المورد المختار
    const supplierSelect = document.getElementById('id_supplier');
    const invoiceSelect = document.getElementById('id_invoice');

    if (supplierSelect) {
        supplierSelect.addEventListener('change', function () {
            const supplierId = this.value;
            if (!supplierId) {
                invoiceSelect.innerHTML = '<option value="">---------</option>';
                return;
            }

            fetch(`/purchases/ajax/load-supplier-invoices/?supplier=${supplierId}`)
                .then(response => response.json())
                .then(data => {
                    invoiceSelect.innerHTML = '<option value="">---------</option>';
                    data.forEach(invoice => {
                        const option = document.createElement('option');
                        option.value = invoice.id;
                        option.textContent = `فاتورة رقم ${invoice.invoice_number} | مبلغ الفاتورة: ${invoice.total}`;
                        invoiceSelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('حدث خطأ أثناء تحميل الفواتير:', error);
                });
        });
    }

});
