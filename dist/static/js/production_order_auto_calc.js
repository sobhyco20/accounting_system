
function parseFloatOrZero(value) {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? 0 : parsed;
}

function animateChange(el) {
    if (!el) return;
    el.style.transition = 'background-color 0.3s ease';
    el.style.backgroundColor = '#fff3cd'; // لون تنبيه
    setTimeout(() => {
        el.style.backgroundColor = '';
    }, 500);
}

function updateComponentRowTotal(row) {
    const qtyInput = row.querySelector('input[name$="-quantity"]');
    const costInput = row.querySelector('input[name$="-unit_cost"]');
    const totalCell = row.querySelector('.field-calculated_total');

    if (qtyInput && costInput && totalCell) {
        const quantity = parseFloatOrZero(qtyInput.value);
        const unitCost = parseFloatOrZero(costInput.value);
        const total = quantity * unitCost;
        totalCell.textContent = total.toFixed(2);
        animateChange(totalCell);
    }
}

function updateExpenseRowTotal(row) {
    const qtyInput = row.querySelector('input[name$="-quantity"]');
    const valueInput = row.querySelector('input[name$="-value"]');
    const totalCell = row.querySelector('.field-total_display');

    if (qtyInput && valueInput && totalCell) {
        const quantity = parseFloatOrZero(qtyInput.value);
        const value = parseFloatOrZero(valueInput.value);
        const total = quantity * value;
        totalCell.textContent = total.toFixed(2);
        animateChange(totalCell);
    }
}

function setValueById(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value.toFixed(2);
        animateChange(el);
    }
}

function updateHeaderTotals() {
    let totalComponent = 0;
    let totalExpense = 0;

    document.querySelectorAll('.field-calculated_total').forEach(cell => {
        totalComponent += parseFloatOrZero(cell.textContent);
    });

    document.querySelectorAll('.field-total_display').forEach(cell => {
        totalExpense += parseFloatOrZero(cell.textContent);
    });

    const totalCost = totalComponent + totalExpense;

    const quantityProducedInput = document.querySelector('#id_quantity');
    const quantityProduced = quantityProducedInput ? parseFloatOrZero(quantityProducedInput.value) : 0;
    const unitCost = quantityProduced > 0 ? totalCost / quantityProduced : 0;

    setValueById("total_component_cost_display", totalComponent);
    setValueById("total_expense_cost_display", totalExpense);
    setValueById("total_cost_display", totalCost);
    setValueById("unit_cost_display", unitCost);
}

function attachAllListeners() {
    const rows = document.querySelectorAll('tr.form-row');

    rows.forEach(row => {
        const isComponent = row.querySelector('input[name$="-unit_cost"]');
        const isExpense = row.querySelector('input[name$="-value"]');

        if (isComponent) {
            const qty = row.querySelector('input[name$="-quantity"]');
            const cost = row.querySelector('input[name$="-unit_cost"]');
            if (qty) qty.addEventListener('input', () => {
                updateComponentRowTotal(row);
                updateHeaderTotals();
            });
            if (cost) cost.addEventListener('input', () => {
                updateComponentRowTotal(row);
                updateHeaderTotals();
            });
        }

        if (isExpense) {
            const qty = row.querySelector('input[name$="-quantity"]');
            const value = row.querySelector('input[name$="-value"]');
            if (qty) qty.addEventListener('input', () => {
                updateExpenseRowTotal(row);
                updateHeaderTotals();
            });
            if (value) value.addEventListener('input', () => {
                updateExpenseRowTotal(row);
                updateHeaderTotals();
            });
        }
    });

const quantityProducedInput = document.querySelector('#id_quantity');
    if (quantityProducedInput) {
        quantityProducedInput.addEventListener('input', () => {
            updateHeaderTotals();

            const quantity = parseFloatOrZero(quantityProducedInput.value);
            const pathParts = window.location.pathname.split('/').filter(Boolean);
            const orderId = pathParts.includes('change') ? pathParts[pathParts.length - 2] : null;

            if (quantity > 0 && orderId) {
                fetch(`/manufacturing/update_bom/${orderId}/${quantity}/`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // تحديث كميات المكونات
                            document.querySelectorAll('tr.form-row').forEach(row => {
                                const productField = row.querySelector('select[name$="-product"]');
                                const qtyInput = row.querySelector('input[name$="-quantity"]');
                                const costInput = row.querySelector('input[name$="-unit_cost"]');

                                if (productField && qtyInput && costInput) {
                                    const selectedId = parseInt(productField.value);
                                    const match = data.components.find(c => c.product_id === selectedId);
                                    if (match) {
                                        qtyInput.value = match.quantity.toFixed(2);
                                        costInput.value = match.unit_cost.toFixed(2);
                                        updateComponentRowTotal(row);
                                    }
                                }
                            });

                            // تحديث كميات المصاريف
                            document.querySelectorAll('tr.form-row').forEach(row => {
                                const expenseField = row.querySelector('select[name$="-expense"]');
                                const qtyInput = row.querySelector('input[name$="-quantity"]');
                                const valueInput = row.querySelector('input[name$="-value"]');

                                if (expenseField && qtyInput && valueInput) {
                                    const selectedId = parseInt(expenseField.value);
                                    const match = data.expenses.find(e => e.expense_id === selectedId);
                                    if (match) {
                                        qtyInput.value = match.quantity.toFixed(2);
                                        valueInput.value = match.value.toFixed(2);
                                        updateExpenseRowTotal(row);
                                    }
                                }
                            });

                            updateHeaderTotals();
                        } else {
                            alert('خطأ: ' + data.message);
                        }
                    })
                    .catch(err => alert('خطأ في الاتصال بالخادم'));
}

        });
}

    
}


document.addEventListener('DOMContentLoaded', function () {
    const quantityInput = document.querySelector('#id_quantity');
    const pathParts = window.location.pathname.split('/').filter(Boolean);
    
    // تأكد من أن الرابط يحتوي على "change" ورقم ID
    const isChangePage = pathParts.includes('change');
    const orderId = isChangePage ? pathParts[pathParts.length - 2] : null;

    if (quantityInput && orderId) {
        quantityInput.addEventListener('input', function () {
            const quantity = parseFloat(quantityInput.value || 0);
            if (!quantity || quantity <= 0) return;

            fetch(`/manufacturing/update_bom/${orderId}/${quantity}/`)
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        alert('خطأ: ' + data.message);
                        return;
                    }

                    const componentRows = document.querySelectorAll('tr.dynamic-productionordercomponent_set');
                    data.components.forEach((component, index) => {
                        if (componentRows[index]) {
                            const qtyInput = componentRows[index].querySelector('input[name$="-quantity"]');
                            const costInput = componentRows[index].querySelector('input[name$="-unit_cost"]');
                            if (qtyInput) qtyInput.value = component.quantity.toFixed(2);
                            if (costInput) costInput.value = component.unit_cost.toFixed(2);
                        }
                    });

                    const expenseRows = document.querySelectorAll('tr.dynamic-productionorderexpense_set');
                    data.expenses.forEach((expense, index) => {
                        if (expenseRows[index]) {
                            const qtyInput = expenseRows[index].querySelector('input[name$="-quantity"]');
                            const valueInput = expenseRows[index].querySelector('input[name$="-value"]');
                            if (qtyInput) qtyInput.value = expense.quantity.toFixed(2);
                            if (valueInput) valueInput.value = expense.value.toFixed(2);
                        }
                    });

                    if (typeof updateHeaderTotals === 'function') {
                        updateHeaderTotals();
                    }
                })
                .catch(error => {
                    alert('فشل الاتصال بالخادم');
                    console.error(error);
                });
        });
    } else {
        console.log('صفحة الإضافة: لا يمكن تنفيذ التحديث التلقائي حتى يتم الحفظ الأولي.');
    }
});
