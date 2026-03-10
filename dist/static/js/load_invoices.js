document.addEventListener('DOMContentLoaded', function () {
    const customerSelect = document.getElementById('id_customer');
    const invoiceSelect = document.getElementById('id_invoice');

    function clearInvoices() {
        invoiceSelect.innerHTML = '<option value="">---------</option>';
    }

    customerSelect.addEventListener('change', function () {
        const customerId = this.value;

        if (!customerId) {
            clearInvoices();
            return;
        }

        fetch(`/sales/ajax/load-customer-invoices/?customer=${customerId}`)
            .then(response => response.json())
            .then(data => {
                clearInvoices();
                data.forEach(function (invoice) {
                    const option = document.createElement('option');
                    option.value = invoice.id;
                    option.textContent = invoice.invoice_number;
                    invoiceSelect.appendChild(option);
                });
            });
    });
});
