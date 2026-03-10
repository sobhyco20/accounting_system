from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from accounts.models import Account, JournalEntry, JournalEntryLine
from django.db.models import Q, Sum
from calendar import monthrange
from decimal import Decimal



class Department(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("اسم الإدارة"))
    salary_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='salary_departments', verbose_name=_("حساب الرواتب"))
    bonus_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='bonus_departments', verbose_name=_("حساب المكافآت"))
    deduction_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='deduction_departments', verbose_name=_("حساب الخصومات"))
    leave_allowance_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_allowance_departments', verbose_name=_("حساب بدل الإجازة"))
    eos_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='eos_departments', verbose_name=_("حساب مكافأة نهاية الخدمة"))
    accrual_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='accrual_departments', verbose_name=_("حساب الرواتب المستحقة"))
    payment_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_departments', verbose_name=_("حساب الصرف"))


    class Meta:
        verbose_name = "إدارة"
        verbose_name_plural = "الإدارات"


    def __str__(self):
        return self.name


class Division(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "قسم"
        verbose_name_plural = "الأقسام"


    def __str__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_code = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    hire_date = models.DateField()
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    division = models.ForeignKey(Division, on_delete=models.SET_NULL, null=True, blank=True)
    position_title = models.CharField(max_length=100)
    annual_leave_days = models.IntegerField(default=0)
    leave_days_per_year = models.PositiveIntegerField(default=21, verbose_name="أيام الإجازة السنوية")
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonuses = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    opening_advance_balance = models.DecimalField(default=0, max_digits=10, decimal_places=2, verbose_name="رصيد أولي للسلف")


    class Meta:
        verbose_name = "موظف"
        verbose_name_plural = "الموظفون"



    def save(self, *args, **kwargs):
        total_allowances = self.housing_allowance + self.transport_allowance + self.other_allowances
        self.net_salary = self.base_salary + total_allowances + self.bonuses - self.deductions
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_code} - {self.full_name}"


    def accrued_leave_days(self, up_to_date=None):
        if not self.hire_date:
            return 0
        if up_to_date is None:
            up_to_date = date.today()

        # عدد الأشهر منذ التعيين
        months = relativedelta(up_to_date, self.hire_date).months + (relativedelta(up_to_date, self.hire_date).years * 12)
        # عدد الأيام المتراكمة (مثال: 30 يوم بالسنة = 2.5 يوم بالشهر)
        return round(months * (self.annual_leave_days / 12), 2)

    def used_leave_days(self, exclude_request=None):
        from .models import LeaveRequest
        qs = LeaveRequest.objects.filter(employee=self, leave_type='annual')
        if exclude_request:
            qs = qs.exclude(id=exclude_request.id)
        return sum(req.days for req in qs)

    def remaining_leave_days(self, exclude_request=None):
        return self.accrued_leave_days() - self.used_leave_days(exclude_request)
    
    @property
    def available_leave_balance(self):
        """
        الرصيد المتاح الفعلي (المتراكم - المستخدم).
        """
        return max(self.accrued_annual_leave - self.used_leave_days, 0)



    def get_accrued_leave_days_until(self, to_date: date):
        if not self.hire_date:
            return 0
        days_per_year = self.annual_leave_days or 21
        delta_days = (to_date - self.hire_date).days
        accrued = (delta_days / 365.0) * days_per_year
        return round(accrued, 2)
    
        
    def get_daily_leave_allowance_rate(self):
        """
        احتساب معدل بدل الإجازة اليومي للموظف
        عبر قسمة الراتب الأساسي على عدد الأيام السنوية المستحقة
        """
        if not self.base_salary:
            return Decimal("0.00")
        
        days_per_year = self.annual_leave_days or 21  # عدد الأيام المستحقة سنويًا
        if days_per_year == 0:
            return Decimal("0.00")

        return round(self.base_salary / Decimal(days_per_year), 2)

#######################################################################################################

from decimal import Decimal
from django.db import models, transaction
from django.contrib.contenttypes.models import ContentType
from accounts.models import JournalEntry, JournalEntryLine, Account
from hr.models import Employee
from django.utils import timezone

class LeaveAllowance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="الموظف")
    pay_date = models.DateField(verbose_name="تاريخ الصرف", default=timezone.now)
    days_entitled = models.PositiveIntegerField(default=0, verbose_name="الأيام المستحقة")

    base_salary_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    housing_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transport_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_allowances_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    extra_benefits = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="تذاكر و مزايا إضافية")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    is_posted = models.BooleanField(default=False, verbose_name="تم الترحيل")

    class Meta:
        verbose_name = "بدل الإجازة"
        verbose_name_plural = "بدلات الإجازة"


    def __str__(self):
        return f"بدل إجازة - {self.employee.full_name} ({self.pay_date})"

    def calculate_days_entitled(self):
        """
        حساب عدد الأيام المستحقة تلقائيًا:
        - إذا لم يتم صرف بدل سابق: من تاريخ التعيين حتى تاريخ الصرف.
        - إذا تم صرف بدل سابق: من تاريخ العودة من آخر إجازة سنوية حتى تاريخ الصرف.
        """
        from hr.models import LeaveReturn, LeaveAllowance

        last_paid = LeaveAllowance.objects.filter(employee=self.employee, is_posted=True).exclude(id=self.id).order_by('-pay_date').first()
        if last_paid:
            last_return = LeaveReturn.objects.filter(employee=self.employee, return_date__gt=last_paid.pay_date).order_by('return_date').first()
            start_date = last_return.return_date if last_return else self.employee.hire_date
        else:
            start_date = self.employee.hire_date

        delta_days = (self.pay_date - start_date).days
        self.days_entitled = max(0, round((delta_days / 365.0) * self.employee.leave_days_per_year))

    def calculate_amounts(self):
        emp = self.employee
        days = Decimal(self.days_entitled or 0)
        self.base_salary_amount = emp.base_salary * days / Decimal(30)
        self.housing_amount = emp.housing_allowance * days / Decimal(30)
        self.transport_amount = emp.transport_allowance * days / Decimal(30)
        self.other_allowances_amount = emp.other_allowances * days / Decimal(30)

        self.total_amount = (
            self.base_salary_amount +
            self.housing_amount +
            self.transport_amount +
            self.other_allowances_amount +
            self.extra_benefits
        )

    def update_data(self):
        self.calculate_days_entitled()
        self.calculate_amounts()

    def save(self, *args, **kwargs):
        self.update_data()
        super().save(*args, **kwargs)


    @transaction.atomic
    def post_journal_entry(self):
        if self.is_posted:
            return

        if not self.employee.department or not self.employee.department.leave_allowance_account or not self.employee.department.payment_account:
            raise ValueError("يرجى ضبط حسابات بدل الإجازة والصرف في الإدارة.")

        emp_name = self.employee.full_name
        emp_code = self.employee.employee_code
        notes_text = f"صرف بدل الإجازة للموظف {emp_name} ({emp_code})"

        journal = JournalEntry.objects.create(
            date=self.pay_date,
            description=f"صرف بدل إجازة - {emp_name}",
            notes=notes_text,
            is_auto=True,
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id,
        )

        JournalEntryLine.objects.create(
            journal_entry=journal,
            account=self.employee.department.leave_allowance_account,
            debit=self.total_amount,
            credit=0,
            description=notes_text
        )

        JournalEntryLine.objects.create(
            journal_entry=journal,
            account=self.employee.department.payment_account,
            debit=0,
            credit=self.total_amount,
            description=notes_text
        )

        self.is_posted = True
        self.save()

##########################################################################################################################
class EndOfServiceReason(models.TextChoices):
    RESIGNATION = 'resignation', "استقالة"
    TERMINATION = 'termination', "إنهاء من قبل الشركة"
    RETIREMENT = 'retirement', "تقاعد"
    OTHER = 'other', "أخرى"




##############################################################################################################################
from django.db import models, transaction
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.contrib.contenttypes.models import ContentType
from accounts.models import JournalEntry, JournalEntryLine
from hr.models import Employee


class EndOfServicePolicy(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Code")
    name = models.CharField(max_length=100, verbose_name="سبب نهاية الخدمة")
    first_years = models.PositiveIntegerField(default=5, verbose_name="عدد السنوات الأولى")
    reward_per_year_first = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="عدد الأيام لكل سنة في السنوات 5 الأولى")
    reward_per_year_after = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="عدد الأيام لكل سنة بعد السنوات 5 الأولى")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100, verbose_name="النسبة من المكافأة (٪)")


    class Meta:
        verbose_name = "سياسة نهاية الخدمة"
        verbose_name_plural = "سياسات نهاية الخدمة"


    def __str__(self):
        return self.name


class EndOfServiceReward(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="الموظف")
    reward_date = models.DateField(default=timezone.now, verbose_name="تاريخ الاستحقاق")
    reason = models.ForeignKey(EndOfServicePolicy, on_delete=models.PROTECT, verbose_name="سبب انتهاء الخدمة")

    # مدة الخدمة التفصيلية
    years = models.PositiveIntegerField(default=0, verbose_name="عدد السنوات", editable=False)
    months = models.PositiveIntegerField(default=0, verbose_name="عدد الأشهر", editable=False)
    days = models.PositiveIntegerField(default=0, verbose_name="عدد الأيام", editable=False)
    years_of_service = models.DecimalField(max_digits=5, decimal_places=2, editable=False, verbose_name="سنوات الخدمة المكافئة")

    reward_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="مكافأة نهاية الخدمة")
    is_posted = models.BooleanField(default=False, verbose_name="تم الترحيل")

    class Meta:
        verbose_name = "مكافأة نهاية الخدمة"
        verbose_name_plural = "مكافآت نهاية الخدمة"



    def calculate_service_duration(self):
        start_date = self.employee.hire_date
        end_date = self.reward_date or timezone.now().date()
        delta = relativedelta(end_date, start_date)

        self.years = delta.years
        self.months = delta.months
        self.days = delta.days

        total_years = self.years + (self.months / 12) + (self.days / 365)
        self.years_of_service = round(total_years, 2)

    def calculate_last_salary(self):
        emp = self.employee
        return emp.base_salary + emp.housing_allowance + emp.transport_allowance + emp.other_allowances

    def calculate_reward(self):
        self.calculate_service_duration()
        last_salary = float(self.calculate_last_salary())
        years = float(self.years_of_service)

        policy = self.reason

        # احتساب حسب عدد الأيام لكل سنة
        if years <= policy.first_years:
            total_days = years * float(policy.reward_per_year_first)
        else:
            total_days = (policy.first_years * float(policy.reward_per_year_first)) + \
                         ((years - policy.first_years) * float(policy.reward_per_year_after))

        total_amount = (last_salary / 30) * total_days  # يتم الحساب على أساس 30 يوم = راتب شهري
        self.reward_amount = round(total_amount * (float(policy.percentage) / 100), 2)

    def save(self, *args, **kwargs):
        self.calculate_reward()
        super().save(*args, **kwargs)

    @transaction.atomic
    def post_journal_entry(self):
        if self.is_posted:
            return

        if not self.employee.department.eos_account or not self.employee.department.payment_account:
            raise ValueError("يرجى ضبط حساب مكافأة نهاية الخدمة وحساب الصرف للإدارة.")

        emp_name = self.employee.full_name
        emp_code = self.employee.employee_code
        notes = f"صرف مكافأة نهاية الخدمة للموظف {emp_name} ({emp_code})"

        journal = JournalEntry.objects.create(
            date=self.reward_date,
            is_auto=True,
            description=notes,
            notes=notes,
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id,
        )

        JournalEntryLine.objects.create(
            journal_entry=journal,
            account=self.employee.department.eos_account,
            debit=self.reward_amount,
            credit=0,
            description=notes
        )

        JournalEntryLine.objects.create(
            journal_entry=journal,
            account=self.employee.department.payment_account,
            debit=0,
            credit=self.reward_amount,
            description=notes
        )

        self.is_posted = True
        self.save()

    def unpost(self):
        JournalEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id
        ).delete()
        self.is_posted = False
        self.save()

##########################################################################################################    

class LeaveType(models.TextChoices):
    ANNUAL = 'annual', _("إجازة سنوية")
    SICK = 'sick', _("إجازة مرضية")
    UNPAID = 'unpaid', _("إجازة بدون راتب")
    MATERNITY = 'maternity', _("إجازة وضع")
    HAJJ = 'hajj', _("إجازة حج")
    EMERGENCY = 'emergency', _("إجازة اضطرارية")
    DEATH_OR_MARRIAGE = 'death_or_marriage', _("زواج أو وفاة")
    STUDY = 'study', _("إجازة دراسية")

from django.db import models
from django.core.exceptions import ValidationError
from datetime import datetime

class LeaveRequest(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, verbose_name="الموظف")
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices, verbose_name="نوع الإجازة")
    start_date = models.DateField(verbose_name="تاريخ البداية")
    end_date = models.DateField(verbose_name="تاريخ النهاية")
    days = models.PositiveIntegerField(editable=False, verbose_name="عدد الأيام")
    deduction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="مبلغ الخصم")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "طلب إجازة"
        verbose_name_plural = "طلبات الإجازة"



    def is_returned(self):
        return hasattr(self, 'return_record')

    def clean(self):
        if self.start_date and self.end_date:
            self.days = (self.end_date - self.start_date).days + 1
            if self.leave_type == 'annual':
                total_remaining = self.employee.remaining_leave_days(exclude_request=self if self.pk else None)
                if self.days > total_remaining:
                    raise ValidationError(
                        f"عدد الأيام المطلوبة ({self.days}) يتجاوز الرصيد المتاح ({total_remaining:.2f})"
                    )


    def save(self, *args, **kwargs):
        self.days = (self.end_date - self.start_date).days + 1

        if self.leave_type in ['unpaid', 'study']:
            daily_rate = (self.employee.base_salary - self.employee.housing_allowance) / 30
            self.deduction_amount = daily_rate * self.days
        else:
            self.deduction_amount = 0

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.full_name} - {self.get_leave_type_display()} ({self.start_date} إلى {self.end_date})"


class LeaveReturn(models.Model):
    leave = models.OneToOneField('LeaveRequest', on_delete=models.CASCADE, related_name='return_record', verbose_name="الإجازة")
    return_date = models.DateField(verbose_name="تاريخ العودة الفعلية", default=datetime.now)
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "عودة من إجازة"
        verbose_name_plural = "العودة من الإجازات"

    def __str__(self):
        return f"عودة {self.leave.employee.full_name} بتاريخ {self.return_date}"


class PayrollAdjustmentHeader(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name="الإدارة")
    month = models.PositiveIntegerField(verbose_name="الشهر")
    year = models.PositiveIntegerField(verbose_name="السنة")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['department', 'month', 'year']

    class Meta:
        verbose_name = "تعديل على الراتب"
        verbose_name_plural = "تعديلات الرواتب"


    def __str__(self):
        return f"تعديلات {self.department.name} - {self.month}/{self.year}"

    def create_lines_for_employees(self):
        existing_employees = set(self.lines.values_list('employee_id', flat=True))
        employees = Employee.objects.filter(department=self.department, is_active=True)
        for emp in employees:
            if emp.id not in existing_employees:
                PayrollAdjustmentLine.objects.create(header=self, employee=emp)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.create_lines_for_employees()


class PayrollAdjustmentLine(models.Model):
    header = models.ForeignKey(PayrollAdjustmentHeader, related_name='lines', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    absence_days = models.PositiveIntegerField(default=0)
    deduction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ['header', 'employee']

    def save(self, *args, **kwargs):
        daily_rate = (self.employee.base_salary - self.employee.housing_allowance) / 30
        self.deduction_amount = daily_rate * self.absence_days
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.full_name} - {self.header.month}/{self.header.year}"


class PayrollBatch(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name="الإدارة")
    year = models.PositiveIntegerField(verbose_name="السنة", default=datetime.now().year)
    month = models.PositiveIntegerField(verbose_name="الشهر", validators=[MinValueValidator(1), MaxValueValidator(12)], default=datetime.now().month)
    created_at = models.DateTimeField(auto_now_add=True)
    posting_date = models.DateField(default=timezone.now)
    payment_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الصرف")

    total_base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_bonuses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    accrual_posted = models.BooleanField(default=False)
    payment_posted = models.BooleanField(default=False)

    class Meta:
        verbose_name = "مسير رواتب"
        verbose_name_plural = "مسيرات الرواتب"


    def __str__(self):
        return f"رواتب {self.department.name} - {self.month:02d}/{self.year}"


    def generate_lines_from_adjustments(self):
        self.lines.all().delete()
        employees = Employee.objects.filter(department=self.department, is_active=True)

        # خصومات الغياب/الإدارية
        adjustment_header = PayrollAdjustmentHeader.objects.filter(
            department=self.department, year=self.year, month=self.month
        ).first()

        adjustment_dict = {}
        if adjustment_header:
            adjustment_dict = {
                line.employee_id: line.deduction_amount
                for line in adjustment_header.lines.all()
            }

        # أقساط السلف المستحقة لهذا الشهر
        installments = AdvanceInstallment.objects.filter(
            year=self.year,
            month=self.month,
            is_paid=False,
            advance__employee__in=employees
        )

        advance_dict = {}
        for inst in installments:
            advance_dict.setdefault(inst.advance.employee_id, 0)
            advance_dict[inst.advance.employee_id] += inst.amount

        # لكل موظف
        for emp in employees:
            unpaid_days = 0

            # تحقق من وجود إجازة سنوية وعودة خلال نفس الشهر
            leave = LeaveRequest.objects.filter(
                employee=emp,
                leave_type='annual',
                start_date__lte=date(self.year, self.month, monthrange(self.year, self.month)[1]),
                end_date__gte=date(self.year, self.month, 1)
            ).first()

            if leave and hasattr(leave, 'return_record'):
                return_date = leave.return_record.return_date
                if return_date.year == self.year and return_date.month == self.month:
                    unpaid_days = return_date.day - 1

            # معدل الخصم اليومي
            daily_rate = (emp.base_salary + emp.housing_allowance + emp.transport_allowance + emp.other_allowances) / 30
            absence_deduction = daily_rate * unpaid_days

            # خصم السلفة لهذا الشهر
            adv_deduct = advance_dict.get(emp.id, 0)

            # إجمالي الخصومات
            total_deductions = emp.deductions + adjustment_dict.get(emp.id, 0) + adv_deduct + absence_deduction

            PayrollLine.objects.create(
                batch=self,
                employee=emp,
                base_salary=emp.base_salary,
                housing_allowance=emp.housing_allowance,
                transport_allowance=emp.transport_allowance,
                other_allowances=emp.other_allowances,
                bonuses=emp.bonuses,
                advance_deduction=adv_deduct,
                deductions=total_deductions,
            )

        # تحديث الأقساط المسددة لهذا الشهر
        installments.update(is_paid=True)

        # تحديث الإجماليات
        self.update_totals()


    def update_totals(self):
        lines = self.lines.all()
        self.total_base_salary = sum(l.base_salary for l in lines)
        self.total_allowances = sum(l.housing_allowance + l.transport_allowance + l.other_allowances for l in lines)
        self.total_bonuses = sum(l.bonuses for l in lines)
        self.total_deductions = sum(l.deductions for l in lines)
        self.total_net_salary = sum(l.net_salary for l in lines)
        self.save()

    def post_accrual(self):
        if self.accrual_posted:
            return
        if not self.department.salary_account or not self.department.accrual_account:
            raise ValueError("يرجى ضبط حسابات الرواتب والمستحقات في الإدارة.")

        journal = JournalEntry.objects.create(
            date=self.posting_date,
            is_auto=True,
            description=f"قيد الاستحقاق - رواتب {self.month:02d}/{self.year}",
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id,
        )

        for line in self.lines.all():
            JournalEntryLine.objects.create(journal_entry=journal, account=self.department.salary_account, debit=line.net_salary, credit=0, description=f"راتب {line.employee.full_name}")
            JournalEntryLine.objects.create(journal_entry=journal, account=self.department.accrual_account, debit=0, credit=line.net_salary, description=f"رواتب مستحقة - {line.employee.full_name}")

        self.accrual_posted = True
        self.save()

    def unpost_accrual(self):
        if not self.accrual_posted:
            return
        content_type = ContentType.objects.get_for_model(self)
        JournalEntry.objects.filter(content_type=content_type, object_id=self.id, description__icontains="الاستحقاق").delete()
        self.accrual_posted = False
        self.save()

    def post_payment(self):
        if self.payment_posted:
            return
        if not self.department.accrual_account or not self.department.payment_account:
            raise ValueError("يرجى ضبط حساب الصرف في الإدارة.")

        journal = JournalEntry.objects.create(
            date=self.payment_date or timezone.now().date(),
            is_auto=True,
            description=f"قيد الصرف - رواتب {self.month:02d}/{self.year}",
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id,
        )

        for line in self.lines.all():
            JournalEntryLine.objects.create(journal_entry=journal, account=self.department.accrual_account, debit=line.net_salary, credit=0, description=f"صرف راتب {line.employee.full_name}")
            JournalEntryLine.objects.create(journal_entry=journal, account=self.department.payment_account, debit=0, credit=line.net_salary, description=f"صرف راتب {line.employee.full_name}")

        self.payment_posted = True
        self.save()

    def unpost_payment(self):
        if not self.payment_posted:
            return
        content_type = ContentType.objects.get_for_model(self)
        JournalEntry.objects.filter(content_type=content_type, object_id=self.id, description__icontains="الصرف").delete()
        self.payment_posted = False
        self.save()

    def unpost_all(self):
        self.unpost_accrual()
        self.unpost_payment()


class PayrollLine(models.Model):
    batch = models.ForeignKey(PayrollBatch, related_name='lines', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonuses = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    advance_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="خصم السلفة")
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        total_allowance = self.housing_allowance + self.transport_allowance + self.other_allowances
        total_deductions = self.deductions + self.advance_deduction
        self.net_salary = self.base_salary + total_allowance + self.bonuses - total_deductions
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.full_name} - {self.batch.month:02d}/{self.batch.year}"


###########################################################################################################################

from accounts.models import JournalEntry, JournalEntryLine, Account
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from accounts.models import JournalEntry, JournalEntryLine, Account
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction

class Advance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="الموظف")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مبلغ السلفة")
    start_month = models.PositiveIntegerField(verbose_name="شهر البداية")
    start_year = models.PositiveIntegerField(verbose_name="سنة البداية")
    months_count = models.PositiveIntegerField(verbose_name="عدد الأشهر للخصم")
    created_at = models.DateTimeField(auto_now_add=True)

    journal_entry = models.ForeignKey(
        "accounts.JournalEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="قيد السلفة"
    )

    loan_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        verbose_name="حساب السلف",
        related_name="advance_loans"
    )
    cash_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        verbose_name="حساب الصرف",
        related_name="advance_cash"
    )


    class Meta:
        verbose_name = "سلفة"
        verbose_name_plural = "السلف"



    def __str__(self):
        return f"سلفة {self.employee.full_name} - {self.amount} ريال"

    def generate_schedule(self):
        self.installments.all().delete()
        monthly_amount = self.amount / self.months_count
        for i in range(self.months_count):
            due_month = (self.start_month + i - 1) % 12 + 1
            due_year = self.start_year + (self.start_month + i - 1) // 12
            AdvanceInstallment.objects.create(
                advance=self,
                month=due_month,
                year=due_year,
                amount=monthly_amount
            )

    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        self.generate_schedule()

        # ✅ أنشئ القيد فقط عند الإنشاء أو التعديل
        self.create_or_update_journal_entry()

    def create_or_update_journal_entry(self):
        from datetime import date

        # حذف القيد السابق إن وجد
        if self.journal_entry:
            self.journal_entry.delete()

        # إنشاء القيد الجديد
        journal = JournalEntry.objects.create(
            date=date.today(),
            description=f"صرف سلفة للموظف {self.employee.full_name}",
            is_auto=True,
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id
        )

        JournalEntryLine.objects.create(
            journal_entry=journal,
            account=self.loan_account,
            debit=self.amount,
            credit=0,
            description="صرف سلفة"
        )

        JournalEntryLine.objects.create(
            journal_entry=journal,
            account=self.cash_account,
            debit=0,
            credit=self.amount,
            description="صرف سلفة"
        )

        # ✅ تحديث بدون تكرار الحفظ
        Advance.objects.filter(pk=self.pk).update(journal_entry=journal)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        if self.journal_entry:
            self.journal_entry.delete()
        super().delete(*args, **kwargs)



class AdvanceInstallment(models.Model):
    advance = models.ForeignKey(Advance, on_delete=models.CASCADE, related_name="installments")
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.advance.employee.full_name} - {self.month}/{self.year}: {self.amount} ريال"


