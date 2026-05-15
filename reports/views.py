from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from datetime import datetime, timedelta, date
from receipts.models import Receipt
from expenses.models import Expense
from students.models import Student

@login_required
def reports_dashboard(request):
    """Main reports dashboard"""
    return render(request, 'reports/dashboard.html')

@login_required
def daily_cash_report(request):
    """Daily cash position report"""
    report_date = request.GET.get('date', date.today())
    if isinstance(report_date, str):
        report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    
    receipts = Receipt.objects.filter(payment_date=report_date, is_voided=False)
    total_collected_lrd = receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_collected_usd = receipts.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    expenses = Expense.objects.filter(expense_date=report_date)
    total_expenses_lrd = expenses.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_expenses_usd = expenses.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    exchange_rate = 200
    closing_balance = (total_collected_lrd - total_expenses_lrd) + \
                      ((total_collected_usd - total_expenses_usd) * exchange_rate)
    
    context = {
        'report_date': report_date,
        'total_collected_lrd': total_collected_lrd,
        'total_collected_usd': total_collected_usd,
        'total_expenses_lrd': total_expenses_lrd,
        'total_expenses_usd': total_expenses_usd,
        'closing_balance': closing_balance,
        'receipts': receipts,
        'expenses': expenses,
    }
    return render(request, 'reports/daily_cash.html', context)

@login_required
def weekly_collections(request):
    """Weekly fee collection by class"""
    week_start = request.GET.get('week_start', date.today() - timedelta(days=7))
    if isinstance(week_start, str):
        week_start = datetime.strptime(week_start, '%Y-%m-%d').date()
    week_end = week_start + timedelta(days=6)
    
    receipts = Receipt.objects.filter(
        payment_date__gte=week_start,
        payment_date__lte=week_end,
        is_voided=False
    )
    
    collections_by_class = {}
    for receipt in receipts:
        class_name = receipt.student.class_name or "Not Assigned"
        if class_name not in collections_by_class:
            collections_by_class[class_name] = {'lrd': 0, 'usd': 0, 'count': 0}
        collections_by_class[class_name]['lrd'] += float(receipt.amount_lrd)
        collections_by_class[class_name]['usd'] += float(receipt.amount_usd)
        collections_by_class[class_name]['count'] += 1
    
    context = {
        'week_start': week_start,
        'week_end': week_end,
        'collections_by_class': collections_by_class,
        'total_lrd': sum(c['lrd'] for c in collections_by_class.values()),
        'total_usd': sum(c['usd'] for c in collections_by_class.values()),
    }
    return render(request, 'reports/weekly_collections.html', context)

@login_required
def termly_summary(request):
    """Termly income/expenditure summary"""
    term = request.GET.get('term', 'Term 1')
    year = request.GET.get('year', date.today().year)
    
    current_month = date.today().month
    month_start = date(date.today().year, current_month, 1)
    month_end = date.today()
    
    receipts = Receipt.objects.filter(
        payment_date__gte=month_start,
        payment_date__lte=month_end,
        is_voided=False
    )
    expenses = Expense.objects.filter(
        expense_date__gte=month_start,
        expense_date__lte=month_end
    )
    
    total_income_lrd = receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_income_usd = receipts.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    total_expenses_lrd = expenses.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_expenses_usd = expenses.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    context = {
        'term': term,
        'year': year,
        'period_start': month_start,
        'period_end': month_end,
        'total_income_lrd': total_income_lrd,
        'total_income_usd': total_income_usd,
        'total_expenses_lrd': total_expenses_lrd,
        'total_expenses_usd': total_expenses_usd,
        'net_lrd': total_income_lrd - total_expenses_lrd,
        'net_usd': total_income_usd - total_expenses_usd,
    }
    return render(request, 'reports/termly_summary.html', context)

@login_required
def arrears_report(request):
    """Students with outstanding balances"""
    students_with_receipts = Student.objects.filter(receipts__isnull=False).distinct()
    context = {
        'students': students_with_receipts,
        'total_students': students_with_receipts.count(),
    }
    return render(request, 'reports/arrears.html', context)
