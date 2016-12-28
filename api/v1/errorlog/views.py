import logging

from rest_framework.generics import CreateAPIView

from api.v1.errorlog.serializers import ErrorLogSerializer
from errorlog.models import ErrorLog

logger = logging.getLogger(__name__)


class LogErrorView(CreateAPIView):
    serializer_class = ErrorLogSerializer

    def perform_create(self, serializer):
        kwargs = {
            'source': ErrorLog.ErrorSource.WebApp.value,
            'version':self.get_version(),
        }
        if self.request.user.is_authenticated():
            kwargs['user']=self.request.user

        try:
            kwargs['url'] = self.request.META['HTTP_REFERER']
        except KeyError:
            pass

        try:
            kwargs['details'] = {
                'UserAgent': self.request.META['HTTP_USER_AGENT'],
            }
        except KeyError:
            pass

        return serializer.save(**kwargs)

    def get_version(self):
        from subprocess import Popen, PIPE

        try:
            stdout, _ = Popen(['git', 'rev-parse', 'HEAD'],
                              stdout=PIPE).communicate()
            return stdout.strip()
        except FileNotFoundError:
            logger.error('Git not accessible.')