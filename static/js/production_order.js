document.addEventListener('DOMContentLoaded', function () {
    function fetchComponents(productId, quantity) {
        const url = `/manufacturing/get-bom-components/?product_id=${productId}&quantity=${quantity}`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                const tableBody = document.querySelector('#bom-component-table-body');
                if (!tableBody) return;

                tableBody.innerHTML = '';

                if (data.success) {
                    data.components.forEach(comp => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${comp.component_name}</td>
                            <td>${comp.unit_cost}</td>
                            <td>${comp.quantity}</td>
                            <td>${comp.total}</td>
                        `;
                        tableBody.appendChild(row);
                    });
                } else {
                    tableBody.innerHTML = `<tr><td colspan="4">${data.message}</td></tr>`;
                }
            });
    }

    const productSelect = document.querySelector('#id_product');
    const quantityInput = document.querySelector('#id_quantity');

    function triggerFetch() {
        const productId = productSelect?.value;
        const quantity = quantityInput?.value || 1;
        if (productId) {
            fetchComponents(productId, quantity);
        }
    }

    if (productSelect && quantityInput) {
        productSelect.addEventListener('change', triggerFetch);
        quantityInput.addEventListener('input', triggerFetch);
        // تشغيل عند أول تحميل
        triggerFetch();
    }
});
