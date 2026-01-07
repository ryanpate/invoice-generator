"""
Invoice signals for automated email notifications.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Invoice
from .services.email_sender import InvoiceEmailService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Invoice)
def send_payment_receipt_on_paid(sender, instance, **kwargs):
    """
    Send payment receipt email when invoice status changes to 'paid'.

    This signal checks if the status has changed from any other status to 'paid'
    and automatically sends a payment receipt to both the client and business owner.
    """
    # Check if status changed to 'paid'
    if instance.status == 'paid' and instance._original_status != 'paid':
        try:
            service = InvoiceEmailService(instance)
            result = service.send_payment_receipt()

            if result['success']:
                logger.info(
                    f"Payment receipt sent for invoice {instance.invoice_number} "
                    f"to {result.get('recipients', [])}"
                )
            else:
                logger.error(
                    f"Failed to send payment receipt for invoice {instance.invoice_number}: "
                    f"{result.get('error', 'Unknown error')}"
                )
        except Exception as e:
            logger.error(
                f"Exception sending payment receipt for invoice {instance.invoice_number}: {e}"
            )

        # Update the original status after processing
        instance._original_status = instance.status
