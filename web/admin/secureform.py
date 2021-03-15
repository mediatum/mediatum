from __future__ import division

import flask as _flask
from flask_admin.form import SecureForm
from datetime import timedelta
from core import config
from wtforms.validators import ValidationError

class MediatumSecureForm(SecureForm):
    class Meta(SecureForm.Meta):
        csrf_time_limit = timedelta(seconds=int(config.get('csrf.timeout', "7200")))

    @property
    def csrf_context(self):
        return _flask.session

    def validate_csrf_token(self, field):
        try:
            self._csrf.validate_csrf_token(self._csrf, field)
        except ValidationError as e:
            if (e.message == "CSRF token expired"):
                self.csrf_token.current_token = self._csrf.generate_csrf_token(field)
                csrf_errors = self.errors['csrf_token']
                csrf_errors.remove("CSRF token expired")
                if not any(csrf_errors):
                    self.errors.pop("csrf_token")
