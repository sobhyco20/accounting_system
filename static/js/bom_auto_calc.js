document.addEventListener("DOMContentLoaded", function () {
    function fetchAndSetUnitCost(selectElement) {
        const productId = selectElement.value;
        if (!productId) return;

        const row = selectElement.closest('tr');
        const costInput = row.querySelector('input[name$="-unit_cost"]');

        fetch(`/inventory/api/product-cost/${productId}/`)
            .then((response) => response.json())
            .then((data) => {
                if (data.average_cost && costInput) {
                    costInput.value = parseFloat(data.average_cost).toFixed(2);
                    costInput.dispatchEvent(new Event('input')); // لتحديث الإجمالي
                }
            })
            .catch((error) => {
                console.error("خطأ في جلب التكلفة:", error);
            });
    }

    function updateRowTotal(row) {
        const quantityInput = row.querySelector('input[name$="-quantity"]');
        const costInput = row.querySelector('input[name$="-unit_cost"]');
        const totalInput = row.querySelector('input[name$="-calculated_total"]');

        if (quantityInput && costInput && totalInput) {
            const quantity = parseFloat(quantityInput.value) || 0;
            const cost = parseFloat(costInput.value) || 0;
            const total = quantity * cost;
            totalInput.value = total.toFixed(2);
        } else {
            console.warn("لم يتم العثور على أحد الحقول");
        }
    }

    function bindEventsToRow(row) {
        const select = row.querySelector('select[name$="-component"]');
        const quantityInput = row.querySelector('input[name$="-quantity"]');
        const costInput = row.querySelector('input[name$="-unit_cost"]');

        if (select && !select.classList.contains('bound')) {
            select.addEventListener('change', function () {
                fetchAndSetUnitCost(this);
            });
            select.classList.add('bound');
        }

        if (quantityInput && !quantityInput.classList.contains('bound')) {
            quantityInput.addEventListener('input', () => updateRowTotal(row));
            quantityInput.classList.add('bound');
        }

        if (costInput && !costInput.classList.contains('bound')) {
            costInput.addEventListener('input', () => updateRowTotal(row));
            costInput.classList.add('bound');
        }
    }

    function bindAllRows() {
        document.querySelectorAll('#components-group tr.form-row').forEach(bindEventsToRow);
        document.querySelectorAll('#expenses-group tr.form-row').forEach(bindEventsToRow);
    }

    // عند التحميل الأول
    bindAllRows();

    // متابعة أي تغييرات (صف جديد)
    const observer = new MutationObserver(() => {
        bindAllRows();
    });

    const containers = ['#components-group', '#expenses-group'];
    containers.forEach(id => {
        const el = document.querySelector(id);
        if (el) observer.observe(el, { childList: true, subtree: true });
    });
});
(function($) {
    function calculateLineTotal(row) {
        var quantity = parseFloat($('input[id$=quantity]', row).val()) || 0;
        var price = parseFloat($('input[id$=unit_cost], input[id$=value]', row).val()) || 0;
        var total = (quantity * price).toFixed(2);
        $('td.readonly', row).text(total);
    }

    function updateAllRows() {
        $('tr.form-row').each(function() {
            calculateLineTotal($(this));
        });
    }

    $(document).ready(function() {
        $(document).on('input', 'input', function() {
            var row = $(this).closest('tr');
            calculateLineTotal(row);
        });

        updateAllRows();
    });
})(django.jQuery);
