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

    const quantityProducedInput = document.querySelector('#id_quantity_produced');
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

    const quantityProducedInput = document.querySelector('#id_quantity_produced');
    if (quantityProducedInput) {
        quantityProducedInput.addEventListener('input', updateHeaderTotals);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    attachAllListeners();
    updateHeaderTotals();

    // إعادة الربط عند إضافة صف جديد
    document.body.addEventListener('click', function (e) {
        if (e.target && e.target.closest('.add-row')) {
            setTimeout(() => {
                attachAllListeners();
                updateHeaderTotals();
            }, 500);
        }
    });
});

function parseFloatOrZero(value) {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? 0 : parsed;
}

function animateChange(element) {
    element.style.transition = 'background-color 0.5s';
    element.style.backgroundColor = '#d4edda'; // أخضر فاتح
    setTimeout(() => {
        element.style.backgroundColor = '';
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

function attachEventListenersToRow(row) {
    const qtyInput = row.querySelector('input[name$="-quantity"]');
    const costInput = row.querySelector('input[name$="-unit_cost"]');

    if (qtyInput) {
        qtyInput.addEventListener('input', () => updateComponentRowTotal(row));
    }
    if (costInput) {
        costInput.addEventListener('input', () => updateComponentRowTotal(row));
    }
}

function initializeAllRows() {
    document.querySelectorAll('tr.form-row').forEach((row) => {
        if (row.querySelector('.field-component')) {
            attachEventListenersToRow(row);
            updateComponentRowTotal(row); // احتساب أولي
        }
    });
}

window.addEventListener('load', function () {
    initializeAllRows();

    // عند إضافة صف جديد (inline)
    const formset = document.getElementById('billofmaterialscomponent_set-group');
    if (formset) {
        formset.addEventListener('click', function (event) {
            if (event.target && event.target.classList.contains('add-row')) {
                setTimeout(() => {
                    initializeAllRows();
                }, 100); // تأخير بسيط لضمان ظهور الصف الجديد
            }
        });
    }
});
