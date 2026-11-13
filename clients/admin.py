from django.contrib import admin
from .models import ClientProfile, Rating, Favorite, ClientRefund


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'city', 'total_jobs_posted', 'total_spent', 'created_at']
    list_filter = ['city', 'created_at']
    search_fields = ['user__username', 'user__email', 'company_name', 'city']


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['client', 'worker', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['client__username', 'worker__user__username']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['client', 'worker', 'created_at']
    list_filter = ['created_at']
    search_fields = ['client__username', 'worker__user__username']


@admin.register(ClientRefund)
class ClientRefundAdmin(admin.ModelAdmin):
    """Money sent back to clients' Mixx by Yas wallets.

    Held refunds are why this screen exists. A held row means YAS could
    not tell us whether the money went back, so nothing automatic will
    touch it and somebody has to compare it against the Mixx statement.
    """

    list_display = ['reference', 'client', 'amount', 'phone_number',
                    'state', 'yas_code', 'created_at', 'settled_at']
    list_filter = ['state', 'created_at']
    search_fields = ['reference', 'yas_reference', 'phone_number',
                     'purchase_reference', 'mfs_transaction_id',
                     'client__first_name', 'client__last_name',
                     'client__email']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    # A record of what was sent and what came back. Editing it by hand
    # would make it disagree with the statement it exists to be compared
    # against; resolving a held refund goes through the resolve
    # endpoint, which records who decided and on what evidence.
    readonly_fields = ['service_request', 'client', 'amount', 'phone_number',
                       'reference', 'mfs_transaction_id',
                       'purchase_reference', 'state', 'reason',
                       'yas_reference', 'yas_code', 'yas_message',
                       'created_by', 'created_at', 'sent_at', 'settled_at']

    def has_add_permission(self, request):
        # A refund is approved through the API, which mints the
        # reference and copies the client's number. One typed in here
        # would have neither.
        return False

    def has_delete_permission(self, request, obj=None):
        # Deleting the record of money that may have moved is never the
        # right answer.
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'client', 'created_by', 'service_request')
