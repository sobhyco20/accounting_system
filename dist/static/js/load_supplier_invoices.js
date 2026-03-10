document.addEventListener('DOMContentLoaded', function () {
    const supplierSelect = document.getElementById('id_supplier');
    const invoiceSelect = document.getElementById('id_invoice');

    function clearInvoices() {
        invoiceSelect.innerHTML = '<option value="">---------</option>';
    }

    supplierSelect.addEventListener('change', function () {
        const supplierId = this.value;

        if (!supplierId) {
            clearInvoices();
            return;
        }

        fetch(`/purchases/ajax/load-supplier-invoices/?supplier=${supplierId}`)
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
