function calculateTotals() {
    let debitTotal = 0.0;
    let creditTotal = 0.0;

    document.querySelectorAll('input[name$="-debit"]').forEach(input => {
        debitTotal += parseFloat(input.value) || 0;
    });

    document.querySelectorAll('input[name$="-credit"]').forEach(input => {
        creditTotal += parseFloat(input.value) || 0;
    });

    const diff = Math.abs(debitTotal - creditTotal).toFixed(2);
    const balanced = diff == 0;

    let footer = document.getElementById("opening-balance-totals");
    if (!footer) {
        footer = document.createElement("tr");
        footer.id = "opening-balance-totals";
        footer.innerHTML = `
            <td colspan="2"><strong>الإجمالي:</strong></td>
            <td id="total-debit"></td>
            <td id="total-credit"></td>
            <td id="balance-status"></td>
        `;
        const table = document.querySelector(".tabular.inline-related tbody");
        table.appendChild(footer);
    }

    document.getElementById("total-debit").innerText = debitTotal.toFixed(2);
    document.getElementById("total-credit").innerText = creditTotal.toFixed(2);
    document.getElementById("balance-status").innerText = balanced ? "✔ متوازن" : `✖ الفرق: ${diff}`;
}

document.addEventListener("DOMContentLoaded", () => {
    calculateTotals();
    document.querySelectorAll('input[name$="-debit"], input[name$="-credit"]').forEach(input => {
        input.addEventListener('input', calculateTotals);
    });
});
