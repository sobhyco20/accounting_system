document.addEventListener('DOMContentLoaded', function () {
    const button = document.querySelector('#load-bom-btn');
    if (!button) return;

    button.addEventListener('click', function () {
        const productSelect = document.querySelector('#id_product');
        const quantityInput = document.querySelector('#id_quantity_produced');

        const productId = productSelect?.value;
        const quantity = quantityInput?.value || 1;

        if (!productId) {
            alert("يرجى اختيار المنتج أولاً");
            return;
        }

        const url = `/manufacturing/get-bom-components/?product_id=${productId}&quantity=${quantity}`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                const compTable = document.querySelector('#bom-component-table-body');
                const expTable = document.querySelector('#bom-expense-table-body');

                if (data.success) {
                    if (compTable) {
                        compTable.innerHTML = '';
                        data.components.forEach(comp => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${comp.component_name}</td>
                                <td>${comp.unit_cost}</td>
                                <td>${comp.quantity}</td>
                                <td>${comp.total}</td>
                            `;
                            compTable.appendChild(row);
                        });
                    }

                    if (expTable) {
                        expTable.innerHTML = '';
                        data.expenses.forEach(exp => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${exp.name}</td>
                                <td>${exp.amount}</td>
                            `;
                            expTable.appendChild(row);
                        });
                    }
                } else {
                    alert(data.message || "لم يتم العثور على مكونات");
                }
            });
    });
});
