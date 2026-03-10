from django.shortcuts import render, get_object_or_404, redirect
from .models import Budget, BudgetEntry
from accounts.models import Account, AccountDirection, JournalEntryLine
from django.db.models import Sum
from decimal import Decimal
from django.http import HttpResponse
from .constants import MONTHS


# المساعدة: جلب كل الأبناء من المستوى الرابع
from collections import deque
def get_all_children(account):
    result = []
    queue = deque([account])
    while queue:
        current = queue.popleft()
        children = Account.objects.filter(parent=current)
        for child in children:
            if child.level == 4:
                result.append(child)
            else:
                queue.append(child)
    return result

# مجموع الفعلي لحساب
def get_actual_total(account, year, month):
    result = JournalEntryLine.objects.filter(
        account=account,
        journal_entry__date__year=year,
        journal_entry__date__month=month
    ).aggregate(
        debit_sum=Sum('debit'),
        credit_sum=Sum('credit')
    )
    debit = result['debit_sum'] or Decimal('0.00')
    credit = result['credit_sum'] or Decimal('0.00')
    return debit - credit

########################################
# إدخال الموازنة
########################################
def budget_entry_view(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    accounts = Account.objects.filter(level=4).order_by('code')

    if request.method == 'POST':
        for account in accounts:
            entry, _ = BudgetEntry.objects.get_or_create(budget=budget, account=account)
            for month in MONTHS:
                value = request.POST.get(f"{account.id}_{month}", "0")
                setattr(entry, month, float(value or 0))
            entry.save()
        return redirect(request.path)

    entries = {
        e.account_id: e for e in BudgetEntry.objects.filter(budget=budget)
    }

    return render(request, 'budget/budget_entry.html', {
        'budget': budget,
        'accounts': accounts,
        'months': MONTHS,
        'entries': entries,
    })

########################################
# صفحة اختيار التقارير
########################################
def budget_reports_home(request):
    return render(request, 'budget/reports/reports_home.html')


########################################
# تقرير ملخص الموازنة
########################################
def budget_summary_report(request):
    budget = Budget.objects.filter(year=2025).first()
    if not budget:
        return render(request, 'budget/reports/summary.html', {'entries': [], 'months': []})

    entries = BudgetEntry.objects.filter(budget=budget).select_related('account').order_by('account__code')

    return render(request, 'budget/reports/summary.html', {
        'entries': entries,
        'months': MONTHS,
        'budget': budget,
    })

########################################
# تقرير المقارنة بين الموازنة والفعلي
########################################
from django.db.models import Q, Sum
from decimal import Decimal
from django.shortcuts import render
from .models import Account, Budget, BudgetEntry


def get_all_children(account):
    # استدعاء الدالة التي تجلب كل الأبناء للحساب
    return Account.objects.filter(parent=account)




MONTHS = {
    'jan': 'يناير',
    'feb': 'فبراير',
    'mar': 'مارس',
    'apr': 'أبريل',
    'may': 'مايو',
    'jun': 'يونيو',
    'jul': 'يوليو',
    'aug': 'أغسطس',
    'sep': 'سبتمبر',
    'oct': 'أكتوبر',
    'nov': 'نوفمبر',
    'dec': 'ديسمبر',
}

# budget/views.py
from django.shortcuts import render
from accounts.models import Account
from budget.models import Budget, BudgetEntry
from accounts.models import JournalEntryLine
from django.db.models import Sum, Q
from datetime import datetime

#############################################################################################################

from collections import defaultdict
from django.db.models import Sum, F, Value as V
from django.db.models.functions import Coalesce
from datetime import datetime
from decimal import Decimal

def budget_comparison_report(request):
    selected_year = int(request.GET.get('year', datetime.today().year))
    selected_month = request.GET.get('month', '')

    months = [
        ('jan', 'يناير'), ('feb', 'فبراير'), ('mar', 'مارس'), ('apr', 'أبريل'),
        ('may', 'مايو'), ('jun', 'يونيو'), ('jul', 'يوليو'), ('aug', 'أغسطس'),
        ('sep', 'سبتمبر'), ('oct', 'أكتوبر'), ('nov', 'نوفمبر'), ('dec', 'ديسمبر'),
    ]

    direction_is = AccountDirection.objects.get(code='IS')
    accounts = Account.objects.filter(level=4, direction=direction_is).order_by('code')

    budget = Budget.objects.filter(year=selected_year).first()
    entries = {}
    if budget:
        entries = {
            e.account_id: {
                'jan': e.jan, 'feb': e.feb, 'mar': e.mar, 'apr': e.apr,
                'may': e.may, 'jun': e.jun, 'jul': e.jul, 'aug': e.aug,
                'sep': e.sep, 'oct': e.oct, 'nov': e.nov, 'dec': e.dec
            }
            for e in BudgetEntry.objects.filter(budget=budget)
        }

    # تحميل الفعلي من JournalEntryLine
    actuals = {
        acc.id: {m[0]: Decimal('0.00') for m in months}
        for acc in accounts
    }

    journal_lines = JournalEntryLine.objects.filter(
        journal_entry__date__year=selected_year,
        account__in=accounts
    ).select_related('journal_entry')

    for line in journal_lines:
        account_id = line.account_id
        entry_date = line.journal_entry.date
        month_code = entry_date.strftime('%b').lower()[:3]

        if account_id in actuals and month_code in actuals[account_id]:
            actuals[account_id][month_code] += line.debit - line.credit

    # إعداد البيانات
    data = []
    for account in accounts:
        est_raw = entries.get(account.id, {m[0]: 0.0 for m in months})
        est = {k: Decimal(str(v)) for k, v in est_raw.items()}
        act = actuals.get(account.id, {m[0]: Decimal('0.00') for m in months})

        if selected_month:
            data.append({
                'account': account,
                'estimated': {selected_month: est.get(selected_month, Decimal('0.00'))},
                'actual': {selected_month: act.get(selected_month, Decimal('0.00'))},
                'total_difference': act.get(selected_month, Decimal('0.00')) - est.get(selected_month, Decimal('0.00')),
            })
        else:
            total_estimated = sum(est.values())
            total_actual = sum(act.values())
            data.append({
                'account': account,
                'estimated': est,
                'actual': act,
                'total_estimated': total_estimated,
                'total_actual': total_actual,
                'total_difference': total_actual - total_estimated,
            })


    return render(request, 'budget/reports/comparison.html', {
        'data': data,
        'months': months,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'years': list(range(2020, datetime.today().year + 2))
    })

########################################
# تقرير حسب الحساب
########################################
from django.db.models import Prefetch
from decimal import Decimal
from accounts.models import Account
from .models import Budget, BudgetEntry

MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

def get_all_children(account):
    return Account.objects.filter(code__startswith=account.code, level=4)

def budget_by_account_report(request):
    selected_account = request.GET.get("account")
    selected_month = request.GET.get("month")
    year = 2025

    accounts = Account.objects.filter(direction__code='IS').order_by('code')
    if selected_account:
        accounts = accounts.filter(id=selected_account)

    budget = Budget.objects.filter(year=year).first()
    entries = BudgetEntry.objects.filter(budget=budget)
    entry_map = {
        (entry.account_id): entry for entry in entries
    }

    data = []
    for account in accounts:
        monthly_data = {}
        for month in MONTHS:
            if selected_month and month != selected_month:
                continue

            if account.level == 4:
                entry = entry_map.get(account.id)
                monthly_data[month] = Decimal(str(getattr(entry, month, 0))) if entry else Decimal('0')
            else:
                total = Decimal('0')
                children = get_all_children(account)
                for child in children:
                    entry = entry_map.get(child.id)
                    if entry:
                        total += Decimal(str(getattr(entry, month, 0)))
                monthly_data[month] = total

        total_sum = sum(monthly_data.values())
        data.append({
            'account': account,
            'monthly': monthly_data,
            'total': total_sum,
        })

    context = {
        'data': data,
        'months': MONTHS,
        'selected_account': int(selected_account) if selected_account else '',
        'selected_month': selected_month,
        'all_accounts': Account.objects.filter(direction__code='IS').order_by('code'),
    }
    return render(request, 'budget/reports/by_account.html', context)
