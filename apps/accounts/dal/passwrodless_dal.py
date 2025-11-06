from ..models.magic_link_token import MagicLinkModel


class PasswordlessDAL:
    def create_magic_link_token(self, email: str):
        return MagicLinkModel.objects.create(email=email)
