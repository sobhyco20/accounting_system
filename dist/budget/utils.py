# budgeting/utils.py

from .models import BudgetActual
from accounts.models import JournalEntryLine
from django.db.models import Sum

def update_actuals_for_budget(budget):
    for item in budget.items.all():
        month_start = f"{budget.year}-{item.month:02d}-01"
        month_end = f"{budget.year}-{item.month:02d}-31"  # تبسيط (يفضّل استخدام `calendar`)

        filters = {
            "account": item.account,
            "journal_entry__date__range": [month_start, month_end]
        }

        if item.cost_center:
            filters["cost_center"] = item.cost_center

        actual_sum = JournalEntryLine.objects.filter(**filters).aggregate(
            total=Sum('debit') - Sum('credit')
        )['total'] or 0

        BudgetActual.objects.update_or_create(
            budget_item=item,
            defaults={"actual_amount": actual_sum}
        )
