(function($) {
    $(document).ready(function () {
        $('#id_employee').change(function () {
            const empId = $(this).val();
            if (empId) {
                $.ajax({
                    url: '/admin/hr/get-leave-balance/',  // سنعدله في الخطوة التالية
                    data: {
                        'employee_id': empId
                    },
                    dataType: 'json',
                    success: function (data) {
                        $('#id_leave_balance').val(data.balance);
                    }
                });
            } else {
                $('#id_leave_balance').val('');
            }
        });

        // Trigger on load
        $('#id_employee').trigger('change');
    });
})(django.jQuery);
