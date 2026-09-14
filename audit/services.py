"""
Service helper for logging audit events.
"""

import logging
from .models import AuditLog

logger = logging.getLogger("audit")


def log_audit(
    action: str,
    description: str = "",
    user=None,
    admin_user=None,
    entity_type: str = "",
    entity_id: str = "",
    request=None,
    actor=None,
    resource_type: str = "",
    resource_id: str = "",
    details=None,
) -> AuditLog:
    """
    Creates an AuditLog record. Supports both (user, entity_type) and (actor, resource_type, details).
    """
    if actor:
        if getattr(actor, 'is_staff', False):
            admin_user = admin_user or actor
        else:
            user = user or actor

    entity_type = entity_type or resource_type or ""
    entity_id = entity_id or resource_id or ""
    
    if details and not description:
        description = str(details)
    elif not description:
        description = f"Action {action} performed on {entity_type} #{entity_id}"

    ip_address = None
    user_agent = ""

    if request:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR")

        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    log_entry = AuditLog.objects.create(
        user=user,
        admin_user=admin_user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    logger.info("AUDIT [%s]: %s (Entity: %s #%s)", action, description, entity_type, entity_id)
    return log_entry
