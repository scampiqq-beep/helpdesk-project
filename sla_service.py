
class SLAService:
    @staticmethod
    def build_ticket_view(ticket):
        return {
            "first_response": {"label": "First response"},
            "resolve": {"label": "Resolve"},
            "summary": "OK",
            "summary_status": "ok",
            "paused": False,
            "breached": False,
        }
