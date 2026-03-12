
from datetime import timedelta

def first_response_deadline(ticket, policy_minutes):
    if not ticket or not ticket.created_at:
        return None
    return ticket.created_at + timedelta(minutes=policy_minutes)

def resolve_deadline(ticket, policy_minutes):
    if not ticket or not ticket.created_at:
        return None
    return ticket.created_at + timedelta(minutes=policy_minutes)
