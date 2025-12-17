from apps.events.dal.invite_link_event_dal import InviteLinkEventDAL
from apps.events.services.event_service import EventService


class InviteLinkService:
    def __init__(self, dal=None, event_service=None):
        self.dal = dal or InviteLinkEventDAL()
        self.event_service = event_service or EventService()

    def create_event_invite_link(self, event_uuid):
        pass
