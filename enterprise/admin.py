# enterprise/admin.py
from django.contrib import admin

from enterprise.models import (
    Bill,
    Cashier,
    Enterprise,
    Installments,
    NFSe,
    PaymentMethod,
    Plan,
    Service,
    StatusBill,
    TypeBill,
)


@admin.register(Enterprise)
class EnterpriseAdmin(admin.ModelAdmin):
    list_display = ()
    search_fields = ("id", "name")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at")
    search_fields = ("id",)
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("id",)
    search_fields = ("id",)
    list_filter = ()


@admin.register(StatusBill)
class StatusBillAdmin(admin.ModelAdmin):
    list_display = ("id",)
    search_fields = ("id",)


@admin.register(TypeBill)
class TypeBillAdmin(admin.ModelAdmin):
    list_display = ("id",)
    search_fields = ("id",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at")
    search_fields = ("id",)
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    search_fields = (
        "id",
        "description",
        "due_date",
    )

    list_select_related = (
        "status",
        "payment_method",
    )

    list_filter = ["payment_method__method"]

    ordering = ("-created_at",)

    # (Opcional) Se quiser busca mais “inteligente” por id digitado como texto
    def get_search_results(self, request, queryset, search_term):
        qs, use_distinct = super().get_search_results(request, queryset, search_term)
        term = search_term.strip()

        if term.isdigit():
            qs = qs | queryset.filter(id=int(term))

        return qs, use_distinct


@admin.register(Installments)
class InstallmentsAdmin(admin.ModelAdmin):
    list_display = ("id",)
    search_fields = ("id",)


@admin.register(NFSe)
class NFSeAdmin(admin.ModelAdmin):
    list_display = ("id", "student__name", "link_pdf", "reference_month")
    search_fields = ("id", "student__name", "reference_month")


@admin.register(Cashier)
class CashierAdmin(admin.ModelAdmin):
    list_display = ("id",)
