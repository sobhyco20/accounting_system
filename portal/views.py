from django.shortcuts import render

# Create your views here.
from django.core.paginator import Paginator
from django.db.models import Q
from sales.models import SalesInvoice


from django.contrib.auth.decorators import login_required

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("app_home")
    return redirect("login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("app_home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        next_url = request.POST.get("next") or request.GET.get("next") or reverse("app_home")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url)

        messages.error(request, "بيانات الدخول غير صحيحة.")

    return render(request, "portal/login.html", {
        "next": request.GET.get("next", ""),
    })


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def app_home(request):
    return render(request, "portal/app_home.html")


from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from sales.models import SalesInvoice

@staff_member_required
def app_sales_invoice_list(request):
    qs = SalesInvoice.objects.select_related("customer").all().order_by("-id")

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(number__icontains=search) | Q(customer__name__icontains=search))

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    # ✅ مهم: نرسل invoices = page_obj علشان القالب يشتغل
    return render(request, "portal/sales_invoice_list.html", {
        "invoices": page_obj,     # هذا اللي القالب بيستخدمه
        "page_obj": page_obj,     # احتياطي لو حبيت pagination
    })


from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required

from sales.models import SalesInvoice, SalesInvoiceItem, Customer, SalesRepresentative
from inventory.models import Warehouse, Product





@staff_member_required
def app_sales_invoice_create(request):
    customers = Customer.objects.all().order_by("name")
    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    reps = SalesRepresentative.objects.all().order_by("name")

    if request.method == "POST":
        action = request.POST.get("action")

        date = request.POST.get("date")
        customer_id = request.POST.get("customer")
        warehouse_id = request.POST.get("warehouse")
        rep_id = request.POST.get("sales_rep") or None

        invoice = SalesInvoice.objects.create(
            date=date,
            customer_id=customer_id,
            warehouse_id=warehouse_id,
            sales_rep_id=rep_id,
        )

        # حفظ البنود
        product_ids = request.POST.getlist("product[]")
        qtys = request.POST.getlist("qty[]")
        prices = request.POST.getlist("price[]")
        tax_rates = request.POST.getlist("tax_rate[]")

        for pid, q, p, t in zip(product_ids, qtys, prices, tax_rates):
            if not pid:
                continue
            SalesInvoiceItem.objects.create(
                invoice=invoice,
                product_id=int(pid),
                quantity=Decimal(q or "0"),
                unit_price=Decimal(p or "0"),
                tax_rate=Decimal(t or "0"),
            )

        # إعادة حساب إجماليات الفاتورة (أفضل من الاعتماد على is_new داخل save)
        total_before = sum(i.total_before_tax for i in invoice.items.all())
        total_tax = sum(i.tax_amount for i in invoice.items.all())
        invoice.total_before_tax_value = total_before
        invoice.total_tax_value = total_tax
        invoice.total_with_tax_value = total_before + total_tax
        invoice.save(update_fields=["total_before_tax_value", "total_tax_value", "total_with_tax_value"])

        if action == "save_post":
            try:
                invoice.post_invoice()
                messages.success(request, "تم الحفظ والترحيل بنجاح ✅")
            except Exception as e:
                messages.error(request, f"تم الحفظ لكن فشل الترحيل: {e}")

        else:
            messages.success(request, "تم حفظ الفاتورة ✅")

        return redirect("app_sales_invoice_list")

    locked = False

    return render(request, "portal/sales_invoice_form.html", {
        "invoice": None,
        "items": [],
        "customers": customers,
        "warehouses": warehouses,
        "products": products,
        "reps": reps,
        "locked": locked,
    })


from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required

from sales.models import SalesInvoice, SalesInvoiceItem, Customer, SalesRepresentative
from inventory.models import Warehouse, Product


@staff_member_required
def app_sales_invoice_edit(request, pk):
    invoice = get_object_or_404(SalesInvoice, pk=pk)

    customers = Customer.objects.all().order_by("name")
    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    reps = SalesRepresentative.objects.all().order_by("name")

    # ✅ لو الفاتورة مرحّلة: امنع أي تعديل POST إلا unpost فقط
    if request.method == "POST" and invoice.is_posted:
        action = request.POST.get("action")
        if action != "unpost":
            messages.error(request, "⚠️ لا يمكن تعديل فاتورة مرحّلة. قم بإلغاء الترحيل أولاً.")
            return redirect("app_sales_invoice_edit", pk=invoice.pk)

    if request.method == "POST":
        action = request.POST.get("action")

        # ✅ إلغاء الترحيل فقط
        if action == "unpost":
            try:
                invoice.unpost_invoice()
                messages.success(request, "تم إلغاء الترحيل ✅")
            except Exception as e:
                messages.error(request, f"فشل إلغاء الترحيل: {e}")
            return redirect("app_sales_invoice_edit", pk=invoice.pk)

        # ✅ تعديل البيانات (فقط لو غير مرحّلة)
        invoice.date = request.POST.get("date")
        invoice.customer_id = request.POST.get("customer")
        invoice.warehouse_id = request.POST.get("warehouse")
        invoice.sales_rep_id = request.POST.get("sales_rep") or None
        invoice.save()

        # حذف البنود القديمة وإعادة إنشائها
        invoice.items.all().delete()

        product_ids = request.POST.getlist("product[]")
        qtys = request.POST.getlist("qty[]")
        prices = request.POST.getlist("price[]")
        tax_rates = request.POST.getlist("tax_rate[]")

        for pid, q, p, t in zip(product_ids, qtys, prices, tax_rates):
            if not pid:
                continue
            SalesInvoiceItem.objects.create(
                invoice=invoice,
                product_id=int(pid),
                quantity=Decimal(q or "0"),
                unit_price=Decimal(p or "0"),
                tax_rate=Decimal(t or "0"),
            )

        # تحديث الإجماليات
        total_before = sum(i.total_before_tax for i in invoice.items.all())
        total_tax = sum(i.tax_amount for i in invoice.items.all())
        invoice.total_before_tax_value = total_before
        invoice.total_tax_value = total_tax
        invoice.total_with_tax_value = total_before + total_tax
        invoice.save(update_fields=["total_before_tax_value", "total_tax_value", "total_with_tax_value"])

        # حفظ وترحيل
        if action == "save_post":
            try:
                invoice.post_invoice()
                messages.success(request, "تم الحفظ والترحيل ✅")
            except Exception as e:
                messages.error(request, f"تم الحفظ لكن فشل الترحيل: {e}")
        else:
            messages.success(request, "تم حفظ التعديل ✅")

        return redirect("app_sales_invoice_list")

    locked = bool(invoice and getattr(invoice, "is_posted", False))

    return render(request, "portal/sales_invoice_form.html", {
        "invoice": invoice,
        "items": invoice.items.select_related("product").all(),
        "customers": customers,
        "warehouses": warehouses,
        "products": products,
        "reps": reps,
        "locked": locked,
    })





from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from sales.models import SalesInvoice

@login_required
def sales_invoice_detail(request, pk):
    invoice = get_object_or_404(SalesInvoice.objects.select_related("customer"), pk=pk)

    # حسب موديلك: items related_name غالبًا "items"
    items = invoice.items.select_related("product").all()

    subtotal = 0
    tax_total = 0
    grand_total = 0

    for it in items:
        # لو عندك حقول جاهزة استخدمها، وإلا نحسب
        line_subtotal = getattr(it, "total_before_tax", None)
        if line_subtotal is None:
            line_subtotal = (it.quantity or 0) * (it.unit_price or 0)

        line_tax = getattr(it, "tax_amount", None) or 0
        line_total = line_subtotal + line_tax

        subtotal += line_subtotal
        tax_total += line_tax
        grand_total += line_total

    return render(request, "portal/sales_invoice_detail.html", {
        "invoice": invoice,
        "items": items,
        "subtotal": subtotal,
        "tax_total": tax_total,
        "grand_total": grand_total,
    })




from sales.models import SalesReturn, SalesReturnItem
from inventory.models import Warehouse, Product
from sales.models import Customer, SalesRepresentative
from decimal import Decimal


@staff_member_required
def app_sales_return_list(request):
    qs = SalesReturn.objects.select_related("customer").order_by("-id")

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(number__icontains=search) |
            Q(customer__name__icontains=search)
        )

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "portal/sales_return_list.html", {
        "returns": page_obj,
        "page_obj": page_obj,
    })


@staff_member_required
def app_sales_return_create(request):
    customers = Customer.objects.all().order_by("name")
    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    reps = SalesRepresentative.objects.all().order_by("name")

    if request.method == "POST":
        action = request.POST.get("action")

        return_obj = SalesReturn.objects.create(
            date=request.POST.get("date"),
            customer_id=request.POST.get("customer"),
            warehouse_id=request.POST.get("warehouse"),
            sales_rep_id=request.POST.get("sales_rep") or None,
        )

        product_ids = request.POST.getlist("product[]")
        qtys = request.POST.getlist("qty[]")
        prices = request.POST.getlist("price[]")
        tax_rates = request.POST.getlist("tax_rate[]")

        for pid, q, p, t in zip(product_ids, qtys, prices, tax_rates):
            if not pid:
                continue
            SalesReturnItem.objects.create(
                sales_return=return_obj,
                product_id=int(pid),
                quantity=Decimal(q or "0"),
                price=Decimal(p or "0"),
                tax_rate=Decimal(t or "0"),
            )

        if action == "save_post":
            try:
                return_obj.post_return()
                messages.success(request, "تم الحفظ والترحيل ✅")
            except Exception as e:
                messages.error(request, f"فشل الترحيل: {e}")
        else:
            messages.success(request, "تم الحفظ ✅")

        return redirect("app_sales_return_list")

    return render(request, "portal/sales_return_form.html", {
        "return_obj": None,
        "items": [],
        "customers": customers,
        "warehouses": warehouses,
        "products": products,
        "reps": reps,
        "locked": False,
    })

@staff_member_required
def app_sales_return_edit(request, pk):
    return_obj = get_object_or_404(SalesReturn, pk=pk)

    customers = Customer.objects.all().order_by("name")
    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    reps = SalesRepresentative.objects.all().order_by("name")

    if request.method == "POST" and return_obj.is_posted:
        action = request.POST.get("action")
        if action != "unpost":
            messages.error(request, "⚠️ لا يمكن تعديل مردود مرحّل.")
            return redirect("app_sales_return_edit", pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "unpost":
            return_obj.unpost_return()
            messages.success(request, "تم إلغاء الترحيل ✅")
            return redirect("app_sales_return_edit", pk=pk)

        return_obj.date = request.POST.get("date")
        return_obj.customer_id = request.POST.get("customer")
        return_obj.warehouse_id = request.POST.get("warehouse")
        return_obj.sales_rep_id = request.POST.get("sales_rep") or None
        return_obj.save()

        return_obj.details.all().delete()

        product_ids = request.POST.getlist("product[]")
        qtys = request.POST.getlist("qty[]")
        prices = request.POST.getlist("price[]")
        tax_rates = request.POST.getlist("tax_rate[]")

        for pid, q, p, t in zip(product_ids, qtys, prices, tax_rates):
            if not pid:
                continue
            SalesReturnItem.objects.create(
                sales_return=return_obj,
                product_id=int(pid),
                quantity=Decimal(q or "0"),
                price=Decimal(p or "0"),
                tax_rate=Decimal(t or "0"),
            )

        if action == "save_post":
            return_obj.post_return()
            messages.success(request, "تم الحفظ والترحيل ✅")
        else:
            messages.success(request, "تم حفظ التعديل ✅")

        return redirect("app_sales_return_list")

    locked = return_obj.is_posted

    return render(request, "portal/sales_return_form.html", {
        "return_obj": return_obj,
        "items": return_obj.details.select_related("product").all(),
        "customers": customers,
        "warehouses": warehouses,
        "products": products,
        "reps": reps,
        "locked": locked,
    })




from decimal import Decimal
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect

from purchases.models import PurchaseReturn, PurchaseReturnItem, Supplier
from inventory.models import Warehouse, Product
from sales.models import SalesRepresentative


@staff_member_required
def app_purchase_return_list(request):
    qs = PurchaseReturn.objects.select_related("supplier").order_by("-id")

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(number__icontains=search) | Q(supplier__name__icontains=search))

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "portal/purchase_return_list.html", {
        "returns": page_obj,
        "page_obj": page_obj,
    })


@staff_member_required
def app_purchase_return_create(request):
    suppliers = Supplier.objects.all().order_by("name")
    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    reps = SalesRepresentative.objects.all().order_by("name")

    if request.method == "POST":
        action = request.POST.get("action")

        return_obj = PurchaseReturn.objects.create(
            date=request.POST.get("date"),
            supplier_id=request.POST.get("supplier"),
            warehouse_id=request.POST.get("warehouse"),
            sales_rep_id=request.POST.get("sales_rep") or None,
        )

        product_ids = request.POST.getlist("product[]")
        qtys = request.POST.getlist("qty[]")
        prices = request.POST.getlist("price[]")
        tax_rates = request.POST.getlist("tax_rate[]")

        for pid, q, p, t in zip(product_ids, qtys, prices, tax_rates):
            if not pid:
                continue
            PurchaseReturnItem.objects.create(
                purchase_return=return_obj,          # related_name = details :contentReference[oaicite:4]{index=4}
                product_id=int(pid),
                quantity=Decimal(q or "0"),
                price=Decimal(p or "0"),
                tax_rate=Decimal(t or "0"),
            )

        # ✅ مهم جداً: PurchaseReturn.post_return يعتمد على total_*_value
        total_before = sum(i.total_before_tax for i in return_obj.details.all())
        total_tax = sum(i.tax_amount for i in return_obj.details.all())
        return_obj.total_before_tax_value = total_before
        return_obj.total_tax_value = total_tax
        return_obj.total_with_tax_value = total_before + total_tax
        return_obj.save(update_fields=["total_before_tax_value", "total_tax_value", "total_with_tax_value"])

        if action == "save_post":
            try:
                return_obj.post_return()
                messages.success(request, "تم الحفظ والترحيل ✅")
            except Exception as e:
                messages.error(request, f"تم الحفظ لكن فشل الترحيل: {e}")
        else:
            messages.success(request, "تم الحفظ ✅")

        return redirect("app_purchase_return_list")

    return render(request, "portal/purchase_return_form.html", {
        "return_obj": None,
        "items": [],
        "suppliers": suppliers,
        "warehouses": warehouses,
        "products": products,
        "reps": reps,
        "locked": False,
    })


@staff_member_required
def app_purchase_return_edit(request, pk):
    return_obj = get_object_or_404(PurchaseReturn, pk=pk)

    suppliers = Supplier.objects.all().order_by("name")
    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    reps = SalesRepresentative.objects.all().order_by("name")

    # ✅ نفس نظام القفل: ممنوع تعديل إذا مرحّل إلا unpost
    if request.method == "POST" and return_obj.is_posted:
        action = request.POST.get("action")
        if action != "unpost":
            messages.error(request, "⚠️ لا يمكن تعديل مردود مشتريات مرحّل. قم بإلغاء الترحيل أولاً.")
            return redirect("app_purchase_return_edit", pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "unpost":
            try:
                return_obj.unpost_return()
                messages.success(request, "تم إلغاء الترحيل ✅")
            except Exception as e:
                messages.error(request, f"فشل إلغاء الترحيل: {e}")
            return redirect("app_purchase_return_edit", pk=pk)

        # تعديل الهيدر
        return_obj.date = request.POST.get("date")
        return_obj.supplier_id = request.POST.get("supplier")
        return_obj.warehouse_id = request.POST.get("warehouse")
        return_obj.sales_rep_id = request.POST.get("sales_rep") or None
        return_obj.save()

        # حذف البنود وإعادة إنشائها (نفس نمط المبيعات)
        return_obj.details.all().delete()

        product_ids = request.POST.getlist("product[]")
        qtys = request.POST.getlist("qty[]")
        prices = request.POST.getlist("price[]")
        tax_rates = request.POST.getlist("tax_rate[]")

        for pid, q, p, t in zip(product_ids, qtys, prices, tax_rates):
            if not pid:
                continue
            PurchaseReturnItem.objects.create(
                purchase_return=return_obj,
                product_id=int(pid),
                quantity=Decimal(q or "0"),
                price=Decimal(p or "0"),
                tax_rate=Decimal(t or "0"),
            )

        # تحديث الإجماليات
        total_before = sum(i.total_before_tax for i in return_obj.details.all())
        total_tax = sum(i.tax_amount for i in return_obj.details.all())
        return_obj.total_before_tax_value = total_before
        return_obj.total_tax_value = total_tax
        return_obj.total_with_tax_value = total_before + total_tax
        return_obj.save(update_fields=["total_before_tax_value", "total_tax_value", "total_with_tax_value"])

        if action == "save_post":
            try:
                return_obj.post_return()
                messages.success(request, "تم الحفظ والترحيل ✅")
            except Exception as e:
                messages.error(request, f"تم الحفظ لكن فشل الترحيل: {e}")
        else:
            messages.success(request, "تم حفظ التعديل ✅")

        return redirect("app_purchase_return_list")

    locked = return_obj.is_posted

    return render(request, "portal/purchase_return_form.html", {
        "return_obj": return_obj,
        "items": return_obj.details.select_related("product").all(),
        "suppliers": suppliers,
        "warehouses": warehouses,
        "products": products,
        "reps": reps,
        "locked": locked,
    })



from decimal import Decimal
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect

from purchases.models import PurchaseInvoice, PurchaseInvoiceItem, Supplier
from inventory.models import Warehouse, Product
from sales.models import SalesRepresentative


@staff_member_required
def app_purchase_invoice_list(request):
    qs = PurchaseInvoice.objects.select_related("supplier").all().order_by("-id")

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(number__icontains=search) | Q(supplier__name__icontains=search))

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "portal/purchase_invoice_list.html", {
        "invoices": page_obj,  # نفس اسم المتغير في قالب المبيعات :contentReference[oaicite:6]{index=6}
        "page_obj": page_obj,
    })


@staff_member_required
def app_purchase_invoice_create(request):
    suppliers = Supplier.objects.all().order_by("name")
    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    reps = SalesRepresentative.objects.all().order_by("name")

    if request.method == "POST":
        action = request.POST.get("action")

        invoice = PurchaseInvoice.objects.create(
            date=request.POST.get("date"),
            supplier_id=request.POST.get("supplier"),
            warehouse_id=request.POST.get("warehouse"),
            sales_rep_id=request.POST.get("sales_rep") or None,
        )

        product_ids = request.POST.getlist("product[]")
        qtys = request.POST.getlist("qty[]")
        prices = request.POST.getlist("price[]")
        tax_rates = request.POST.getlist("tax_rate[]")

        for pid, q, p, t in zip(product_ids, qtys, prices, tax_rates):
            if not pid:
                continue
            PurchaseInvoiceItem.objects.create(
                invoice=invoice,
                product_id=int(pid),
                quantity=Decimal(q or "0"),
                unit_price=Decimal(p or "0"),
                tax_rate=Decimal(t or "0"),
            )

        # تحديث الإجماليات (نفس المبيعات)
        total_before = sum(i.total_before_tax for i in invoice.items.all())
        total_tax = sum(i.tax_amount for i in invoice.items.all())
        invoice.total_before_tax_value = total_before
        invoice.total_tax_value = total_tax
        invoice.total_with_tax_value = total_before + total_tax
        invoice.save(update_fields=["total_before_tax_value", "total_tax_value", "total_with_tax_value"])

        if action == "save_post":
            try:
                invoice.post_invoice()  # موجود بالموديل :contentReference[oaicite:7]{index=7}
                messages.success(request, "تم الحفظ والترحيل بنجاح ✅")
            except Exception as e:
                messages.error(request, f"تم الحفظ لكن فشل الترحيل: {e}")
        else:
            messages.success(request, "تم حفظ الفاتورة ✅")

        return redirect("app_purchase_invoice_list")

    return render(request, "portal/purchase_invoice_form.html", {
        "invoice": None,
        "items": [],
        "suppliers": suppliers,
        "warehouses": warehouses,
        "products": products,
        "reps": reps,
        "locked": False,
    })


@staff_member_required
def app_purchase_invoice_edit(request, pk):
    invoice = get_object_or_404(PurchaseInvoice, pk=pk)

    suppliers = Supplier.objects.all().order_by("name")
    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    reps = SalesRepresentative.objects.all().order_by("name")

    # ✅ نفس نظام القفل بالمبيعات: امنع أي POST إلا unpost لو مرحّلة :contentReference[oaicite:8]{index=8}
    if request.method == "POST" and invoice.is_posted:
        action = request.POST.get("action")
        if action != "unpost":
            messages.error(request, "⚠️ لا يمكن تعديل فاتورة مشتريات مرحّلة. قم بإلغاء الترحيل أولاً.")
            return redirect("app_purchase_invoice_edit", pk=invoice.pk)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "unpost":
            try:
                invoice.unpost_invoice()  # موجود بالموديل :contentReference[oaicite:9]{index=9}
                messages.success(request, "تم إلغاء الترحيل ✅")
            except Exception as e:
                messages.error(request, f"فشل إلغاء الترحيل: {e}")
            return redirect("app_purchase_invoice_edit", pk=invoice.pk)

        # تعديل الهيدر
        invoice.date = request.POST.get("date")
        invoice.supplier_id = request.POST.get("supplier")
        invoice.warehouse_id = request.POST.get("warehouse")
        invoice.sales_rep_id = request.POST.get("sales_rep") or None
        invoice.save()

        # حذف البنود وإعادة إنشائها (نفس المبيعات :contentReference[oaicite:10]{index=10})
        invoice.items.all().delete()

        product_ids = request.POST.getlist("product[]")
        qtys = request.POST.getlist("qty[]")
        prices = request.POST.getlist("price[]")
        tax_rates = request.POST.getlist("tax_rate[]")

        for pid, q, p, t in zip(product_ids, qtys, prices, tax_rates):
            if not pid:
                continue
            PurchaseInvoiceItem.objects.create(
                invoice=invoice,
                product_id=int(pid),
                quantity=Decimal(q or "0"),
                unit_price=Decimal(p or "0"),
                tax_rate=Decimal(t or "0"),
            )

        # تحديث الإجماليات
        total_before = sum(i.total_before_tax for i in invoice.items.all())
        total_tax = sum(i.tax_amount for i in invoice.items.all())
        invoice.total_before_tax_value = total_before
        invoice.total_tax_value = total_tax
        invoice.total_with_tax_value = total_before + total_tax
        invoice.save(update_fields=["total_before_tax_value", "total_tax_value", "total_with_tax_value"])

        if action == "save_post":
            try:
                invoice.post_invoice()
                messages.success(request, "تم الحفظ والترحيل ✅")
            except Exception as e:
                messages.error(request, f"تم الحفظ لكن فشل الترحيل: {e}")
        else:
            messages.success(request, "تم حفظ التعديل ✅")

        return redirect("app_purchase_invoice_list")

    locked = bool(invoice and getattr(invoice, "is_posted", False))

    return render(request, "portal/purchase_invoice_form.html", {
        "invoice": invoice,
        "items": invoice.items.select_related("product").all(),
        "suppliers": suppliers,
        "warehouses": warehouses,
        "products": products,
        "reps": reps,
        "locked": locked,
    })



from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def app_sales_reports(request):
    from sales.models import (
        Customer,
        SalesInvoice,
        SalesRepresentative,
        CustomerPayment,
        SalesReturn,
    )

    report = request.GET.get("report", "")
    export = request.GET.get("export") == "1"

    # تواريخ افتراضية
    from_date = request.GET.get("from_date") or "2026-01-01"
    to_date   = request.GET.get("to_date")   or "2026-12-31"

    ctx = {
        "selected_report": report,
        "from_date": from_date,
        "to_date": to_date,
    }

    # ========= 1) تقرير المبيعات =========
    if report == "sales":
        qs = SalesInvoice.objects.select_related("customer").filter(
            date__gte=from_date,
            date__lte=to_date,
        )
        invoices = []
        total_amount = Decimal("0")
        for inv in qs:
            amount = getattr(inv, "total_with_tax_value", None) or Decimal("0")
            invoices.append({
                "number": inv.number,
                "date": inv.date,
                "customer": inv.customer,
                "amount": amount,
            })
            total_amount += Decimal(str(amount or 0))

        ctx.update({"invoices": invoices, "total_amount": total_amount})

    # ========= 2) تقرير المبيعات بالعميل =========
    elif report == "by_customer":
        customers = Customer.objects.all().order_by("name")
        customer_id = (request.GET.get("customer") or "").strip()

        qs = SalesInvoice.objects.select_related("customer").filter(
            date__gte=from_date,
            date__lte=to_date,
        )
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        invoices = []
        total_amount = Decimal("0")
        for inv in qs:
            amount = getattr(inv, "total_with_tax_value", None) or Decimal("0")
            invoices.append({
                "number": inv.number,
                "date": inv.date,
                "customer": inv.customer,
                "amount": amount,
            })
            total_amount += Decimal(str(amount or 0))

        ctx.update({
            "customers": customers,
            "customer": customer_id,
            "invoices": invoices,
            "total_amount": total_amount
        })

    # ========= 3) كشف حساب عميل =========
    elif report == "ledger":
        customers = Customer.objects.all().order_by("name")
        customer_id = (request.GET.get("customer") or "").strip()

        invoices_qs = SalesInvoice.objects.select_related("customer").filter(
            date__gte=from_date,
            date__lte=to_date,
        )
        payments_qs = CustomerPayment.objects.select_related("customer").filter(
            date__gte=from_date,
            date__lte=to_date,
        )

        if customer_id:
            invoices_qs = invoices_qs.filter(customer_id=customer_id)
            payments_qs = payments_qs.filter(customer_id=customer_id)

        # حركات مبسطة: فواتير (+) وسداد (-)
        rows = []
        balance = Decimal("0")

        for inv in invoices_qs.order_by("date"):
            amount = getattr(inv, "total_with_tax_value", None) or Decimal("0")
            balance += Decimal(str(amount))
            rows.append({
                "date": inv.date,
                "ref": inv.number,
                "type": "فاتورة",
                "debit": amount,
                "credit": Decimal("0"),
                "balance": balance,
            })

        for pay in payments_qs.order_by("date"):
            amount = getattr(pay, "amount", None) or Decimal("0")
            balance -= Decimal(str(amount))
            rows.append({
                "date": pay.date,
                "ref": getattr(pay, "number", "") or f"PAY-{pay.id}",
                "type": "سداد",
                "debit": Decimal("0"),
                "credit": amount,
                "balance": balance,
            })

        rows = sorted(rows, key=lambda x: x["date"])

        ctx.update({
            "customers": customers,
            "customer": customer_id,
            "rows": rows,
            "ending_balance": balance,
        })

    # ========= 4) تقرير المندوبين (مبيعات + مشتريات) =========
    elif report == "rep":
        reps = SalesRepresentative.objects.all().order_by("name")
        rep_id = (request.GET.get("rep") or "").strip()

        sales_qs = SalesInvoice.objects.filter(date__gte=from_date, date__lte=to_date)
        if rep_id:
            sales_qs = sales_qs.filter(sales_rep_id=rep_id)

        # (مؤقت) المشتريات = 0 إذا لم تكن لديك موديلات مشتريات هنا
        results = []
        for r in (reps if not rep_id else reps.filter(id=rep_id)):
            sales_total = sales_qs.filter(sales_rep=r).aggregate(s=Sum("total_with_tax_value"))["s"] or Decimal("0")
            purchase_total = Decimal("0")
            results.append({
                "rep": r,
                "sales_total": sales_total,
                "purchase_total": purchase_total,
                "net": sales_total - purchase_total,
            })

        ctx.update({"reps": reps, "rep": rep_id, "results": results})

    # ========= 5) العمولات =========
    elif report == "commission":
        reps = SalesRepresentative.objects.all().order_by("name")
        rep_id = (request.GET.get("rep") or "").strip()

        qs = SalesInvoice.objects.filter(date__gte=from_date, date__lte=to_date)
        if rep_id:
            qs = qs.filter(sales_rep_id=rep_id)

        # هنا فقط نجمع مبيعات كل مندوب (العمولة نفسها أنت عندك منطقها)
        rows = []
        for r in (reps if not rep_id else reps.filter(id=rep_id)):
            total_sales = qs.filter(sales_rep=r).aggregate(s=Sum("total_before_tax_value"))["s"] or Decimal("0")
            rows.append({"rep": r, "total_sales": total_sales})

        ctx.update({"reps": reps, "rep": rep_id, "rows": rows})

    # ========= 6) أعمار الديون (Aging) =========
    elif report == "aging":
        # هذا نموذج بسيط: إجمالي رصيد كل عميل = فواتير - سداد
        customers = Customer.objects.all().order_by("name")

        invoices_sum = SalesInvoice.objects.values("customer_id").annotate(
            total=Sum("total_with_tax_value")
        )
        payments_sum = CustomerPayment.objects.values("customer_id").annotate(
            total=Sum("amount")
        )

        inv_map = {x["customer_id"]: (x["total"] or Decimal("0")) for x in invoices_sum}
        pay_map = {x["customer_id"]: (x["total"] or Decimal("0")) for x in payments_sum}

        rows = []
        for c in customers:
            bal = (inv_map.get(c.id, Decimal("0")) - pay_map.get(c.id, Decimal("0")))
            rows.append({"customer": c, "balance": bal})

        ctx.update({"rows": rows})

    return render(request, "sales/reports/reports_home.html", ctx)




from decimal import Decimal
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

@staff_member_required
def app_purchase_reports(request):
    from purchases.models import PurchaseInvoice, Supplier  # عدل حسب مشروعك

    report = request.GET.get("report", "")
    from_date = request.GET.get("from_date") or "2026-01-01"
    to_date   = request.GET.get("to_date")   or "2026-12-31"

    ctx = {
        "selected_report": report,
        "from_date": from_date,
        "to_date": to_date,
    }

    # ========= 1) تقرير المشتريات =========
    if report == "purchases":
        qs = PurchaseInvoice.objects.select_related("supplier").filter(
            date__gte=from_date,
            date__lte=to_date,
        )

        invoices = []
        total_amount = Decimal("0")

        for inv in qs:
            amount = getattr(inv, "total_with_tax_value", None) or Decimal("0")
            invoices.append({
                "number": inv.number,
                "date": inv.date,
                "supplier": inv.supplier,
                "amount": amount,
            })
            total_amount += Decimal(str(amount or 0))

        ctx.update({
            "invoices": invoices,
            "total_amount": total_amount
        })

    # ========= 2) المشتريات حسب المورد =========
    elif report == "by_supplier":
        suppliers = Supplier.objects.all().order_by("name")
        supplier_id = (request.GET.get("supplier") or "").strip()

        qs = PurchaseInvoice.objects.select_related("supplier").filter(
            date__gte=from_date,
            date__lte=to_date,
        )

        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)

        invoices = []
        total_amount = Decimal("0")

        for inv in qs:
            amount = getattr(inv, "total_with_tax_value", None) or Decimal("0")
            invoices.append({
                "number": inv.number,
                "date": inv.date,
                "supplier": inv.supplier,
                "amount": amount,
            })
            total_amount += Decimal(str(amount or 0))

        ctx.update({
            "suppliers": suppliers,
            "supplier": supplier_id,
            "invoices": invoices,
            "total_amount": total_amount
        })

    # ========= 3) كشف حساب مورد =========
    elif report == "supplier_ledger":
        suppliers = Supplier.objects.all().order_by("name")
        supplier_id = (request.GET.get("supplier") or "").strip()

        qs = PurchaseInvoice.objects.filter(
            date__gte=from_date,
            date__lte=to_date,
        )

        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)

        rows = []
        balance = Decimal("0")

        for inv in qs.order_by("date"):
            amount = getattr(inv, "total_with_tax_value", None) or Decimal("0")
            balance += Decimal(str(amount))
            rows.append({
                "date": inv.date,
                "ref": inv.number,
                "type": "فاتورة مشتريات",
                "debit": amount,
                "credit": Decimal("0"),
                "balance": balance,
            })

        ctx.update({
            "suppliers": suppliers,
            "supplier": supplier_id,
            "rows": rows,
            "ending_balance": balance
        })

    return render(request, "purchases/reports/reports_home.html", ctx)    


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum
from decimal import Decimal

from inventory.models import (
    Warehouse, Product, Unit,
    OpeningStockBalance, OpeningStockItem,
    StockTransaction, StockTransactionItem
)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum
from decimal import Decimal

from inventory.models import (
    Warehouse, Product, Unit,
    OpeningStockBalance, OpeningStockItem,
    StockTransaction, StockTransactionItem,
    get_product_balance
)


# =========================
# Opening Balances
# =========================

@login_required
def app_opening_balance_list(request):
    q = (request.GET.get("q") or "").strip()
    rows = OpeningStockBalance.objects.select_related("warehouse").order_by("-date", "-id")
    if q:
        rows = rows.filter(Q(warehouse__name__icontains=q) | Q(warehouse__code__icontains=q))
    return render(request, "inventory/reports/opening_balance_list.html", {"rows": rows, "q": q})


@login_required
def app_opening_balance_create(request):
    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    units = Unit.objects.all().order_by("name")

    if request.method == "POST":
        balance = OpeningStockBalance.objects.create(
            warehouse_id=request.POST.get("warehouse"),
            date=request.POST.get("date"),
            is_posted=False
        )

        product_ids = request.POST.getlist("product[]")
        unit_ids = request.POST.getlist("unit[]")
        qtys = request.POST.getlist("qty[]")
        costs = request.POST.getlist("cost[]")

        for pid, uid, qv, cv in zip(product_ids, unit_ids, qtys, costs):
            if not pid:
                continue
            OpeningStockItem.objects.create(
                balance=balance,
                product_id=pid,
                unit_id=uid,
                quantity=Decimal(qv or "0"),
                unit_cost=Decimal(cv or "0"),
            )

        messages.success(request, "✅ تم إنشاء رصيد افتتاحي.")
        return redirect("app_opening_balance_edit", pk=balance.id)

    return render(request, "inventory/reports/opening_balance_form.html", {
        "balance": None,
        "locked": False,
        "warehouses": warehouses,
        "products": products,
        "units": units,
        "items": [],
    })


@login_required
def app_opening_balance_edit(request, pk):
    balance = get_object_or_404(OpeningStockBalance.objects.select_related("warehouse"), pk=pk)
    locked = balance.is_posted

    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    units = Unit.objects.all().order_by("name")
    items = balance.items.select_related("product", "unit").all()

    if request.method == "POST":
        if locked:
            messages.error(request, "🔒 الرصيد مرحّل ولا يمكن تعديله.")
            return redirect("app_opening_balance_edit", pk=pk)

        balance.warehouse_id = request.POST.get("warehouse")
        balance.date = request.POST.get("date")
        balance.save()

        balance.items.all().delete()

        product_ids = request.POST.getlist("product[]")
        unit_ids = request.POST.getlist("unit[]")
        qtys = request.POST.getlist("qty[]")
        costs = request.POST.getlist("cost[]")

        for pid, uid, qv, cv in zip(product_ids, unit_ids, qtys, costs):
            if not pid:
                continue
            OpeningStockItem.objects.create(
                balance=balance,
                product_id=pid,
                unit_id=uid,
                quantity=Decimal(qv or "0"),
                unit_cost=Decimal(cv or "0"),
            )

        messages.success(request, "✅ تم حفظ التعديلات.")
        return redirect("app_opening_balance_edit", pk=pk)

    return render(request, "inventory/reports/opening_balance_form.html", {
        "balance": balance,
        "locked": locked,
        "warehouses": warehouses,
        "products": products,
        "units": units,
        "items": items,
    })


@login_required
def app_opening_balance_post(request, pk):
    balance = get_object_or_404(OpeningStockBalance, pk=pk)
    try:
        balance.post_balance()
        messages.success(request, "✅ تم ترحيل الرصيد الافتتاحي.")
    except Exception as e:
        messages.error(request, f"❌ {e}")
    return redirect("app_opening_balance_edit", pk=pk)


@login_required
def app_opening_balance_unpost(request, pk):
    balance = get_object_or_404(OpeningStockBalance, pk=pk)
    try:
        balance.unpost_balance()
        messages.success(request, "✅ تم إلغاء ترحيل الرصيد.")
    except Exception as e:
        messages.error(request, f"❌ {e}")
    return redirect("app_opening_balance_edit", pk=pk)


# =========================
# Stock Transactions
# =========================

@login_required
def app_stock_tx_list(request):
    q = (request.GET.get("q") or "").strip()
    rows = StockTransaction.objects.select_related("warehouse").order_by("-date", "-id")
    if q:
        rows = rows.filter(Q(notes__icontains=q) | Q(warehouse__name__icontains=q) | Q(code__icontains=q))
    return render(request, "inventory/reports/stock_tx_list.html", {"rows": rows, "q": q})


@login_required
def app_stock_tx_create(request):
    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    units = Unit.objects.all().order_by("name")

    if request.method == "POST":
        tx = StockTransaction.objects.create(
            date=request.POST.get("date"),
            warehouse_id=request.POST.get("warehouse"),
            transaction_type=request.POST.get("transaction_type"),
            notes=request.POST.get("notes") or "",
            is_posted=False
        )

        product_ids = request.POST.getlist("product[]")
        unit_ids = request.POST.getlist("unit[]")
        qtys = request.POST.getlist("qty[]")
        costs = request.POST.getlist("cost[]")

        for pid, uid, qv, cv in zip(product_ids, unit_ids, qtys, costs):
            if not pid:
                continue
            StockTransactionItem.objects.create(
                transaction=tx,
                product_id=pid,
                unit_id=uid or None,
                quantity=Decimal(qv or "0"),
                cost=Decimal(cv or "0"),
            )

        messages.success(request, "✅ تم إنشاء حركة مخزون.")
        return redirect("app_stock_tx_edit", pk=tx.id)

    return render(request, "inventory/reports/stock_tx_form.html", {
        "tx": None,
        "locked": False,
        "warehouses": warehouses,
        "products": products,
        "units": units,
        "items": [],
        "tx_types": StockTransaction.TRANSACTION_TYPES,
    })


@login_required
def app_stock_tx_edit(request, pk):
    tx = get_object_or_404(StockTransaction.objects.select_related("warehouse"), pk=pk)
    locked = tx.is_posted

    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    units = Unit.objects.all().order_by("name")
    items = tx.items.select_related("product", "unit").all()

    if request.method == "POST":
        if locked:
            messages.error(request, "🔒 الحركة مرحّلة ولا يمكن تعديلها.")
            return redirect("app_stock_tx_edit", pk=pk)

        tx.date = request.POST.get("date")
        tx.warehouse_id = request.POST.get("warehouse")
        tx.transaction_type = request.POST.get("transaction_type")
        tx.notes = request.POST.get("notes") or ""
        tx.save()

        tx.items.all().delete()

        product_ids = request.POST.getlist("product[]")
        unit_ids = request.POST.getlist("unit[]")
        qtys = request.POST.getlist("qty[]")
        costs = request.POST.getlist("cost[]")

        for pid, uid, qv, cv in zip(product_ids, unit_ids, qtys, costs):
            if not pid:
                continue
            StockTransactionItem.objects.create(
                transaction=tx,
                product_id=pid,
                unit_id=uid or None,
                quantity=Decimal(qv or "0"),
                cost=Decimal(cv or "0"),
            )

        messages.success(request, "✅ تم حفظ التعديلات.")
        return redirect("app_stock_tx_edit", pk=pk)

    return render(request, "inventory/reports/stock_tx_form.html", {
        "tx": tx,
        "locked": locked,
        "warehouses": warehouses,
        "products": products,
        "units": units,
        "items": items,
        "tx_types": StockTransaction.TRANSACTION_TYPES,
    })


@login_required
def app_stock_tx_post(request, pk):
    tx = get_object_or_404(StockTransaction, pk=pk)
    try:
        tx.post_transaction()
        messages.success(request, "✅ تم ترحيل حركة المخزون.")
    except Exception as e:
        messages.error(request, f"❌ {e}")
    return redirect("app_stock_tx_edit", pk=pk)


@login_required
def app_stock_tx_unpost(request, pk):
    tx = get_object_or_404(StockTransaction, pk=pk)
    try:
        tx.unpost_transaction()
        messages.success(request, "✅ تم إلغاء الترحيل.")
    except Exception as e:
        messages.error(request, f"❌ {e}")
    return redirect("app_stock_tx_edit", pk=pk)


# =========================
# Inventory Reports (داخل البورتال بدون iframe)
# =========================

@login_required
def app_inventory_reports(request):
    selected_report = request.GET.get("report", "")
    from_date = request.GET.get("from_date") or "2025-01-01"
    to_date = request.GET.get("to_date") or "2025-12-31"
    warehouse = request.GET.get("warehouse") or ""
    product = request.GET.get("product") or ""

    warehouses = Warehouse.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")

    ctx = {
        "selected_report": selected_report,
        "from_date": from_date,
        "to_date": to_date,
        "warehouse": warehouse,
        "product": product,
        "warehouses": warehouses,
        "products": products,
    }

    if selected_report == "movement":
        qs = StockTransactionItem.objects.select_related(
            "transaction", "transaction__warehouse", "product", "unit"
        ).filter(
            transaction__date__gte=from_date,
            transaction__date__lte=to_date
        ).order_by("transaction__date", "id")

        if warehouse:
            qs = qs.filter(transaction__warehouse_id=warehouse)
        if product:
            qs = qs.filter(product_id=product)

        ctx["rows"] = qs

    elif selected_report == "balances":
        # رصيد حتى تاريخ (to_date)
        rows = []
        for p in products:
            bal = get_product_balance(p.id, warehouse_id=warehouse or None)
            if bal != 0:
                rows.append({"product": p, "balance": bal})
        ctx["rows"] = rows
        ctx["as_of"] = to_date

    return render(request, "inventory/reports/reports_home.html", ctx)