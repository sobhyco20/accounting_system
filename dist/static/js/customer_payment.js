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

    // تحميل الفواتير بناء على العميل المختار
    const customerSelect = document.getElementById('id_customer');
    const invoiceSelect = document.getElementById('id_invoice');

    if (customerSelect) {
        customerSelect.addEventListener('change', function () {
            const customerId = this.value;
            if (!customerId) {
                invoiceSelect.innerHTML = '<option value="">---------</option>';
                return;
            }

            fetch(`/sales/ajax/load-customer-invoices/?customer_id=${customerId}`)
                .then(response => response.json())
                .then(data => {
                    invoiceSelect.innerHTML = '<option value="">---------</option>';
                    data.invoices.forEach(invoice => {
                        invoiceSelect.innerHTML += `<option value="${invoice.id}">فاتورة رقم ${invoice.number} | المبلغ: ${invoice.total}</option>`;
                    });
                })
                .catch(error => {
                    console.error('حدث خطأ أثناء تحميل الفواتير:', error);
                });
        });
    }

});
