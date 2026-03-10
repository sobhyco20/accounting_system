document.addEventListener("DOMContentLoaded", function () {
    const rows = document.querySelectorAll("tr.form-row");
    rows.forEach(row => {
        const levelCell = row.querySelector('[id$="-account_level"]');
        if (!levelCell) return;

        const level = parseInt(levelCell.textContent.trim());
        if (level !== 4) {
            const inputs = row.querySelectorAll("input[type='number']");
            inputs.forEach(input => {
                input.readOnly = true;
                input.style.backgroundColor = "#f0f0f0";
                input.style.cursor = "not-allowed";
            });
        }
    });
});
