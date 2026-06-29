from django.views.generic import TemplateView


class FrontendAppView(TemplateView):
    template_name = 'frontend/index.html'

