from ..dal.passwrodless_dal import MagicLinkModel


class PasswordlessService:

    def __init__(self, dal=None):
        self.dal = dal or MagicLinkModel()

    def create_inv=

