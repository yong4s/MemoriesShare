from ..models.invite_link_event import InviteEventLink


class InviteLinkEventDAL:

    def create_event_invite_link(self, event):
        return InviteEventLink.objects.create(event=event)
