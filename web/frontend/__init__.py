from core.transition import httpstatus


class Content:

    def feedback(self, req):
        pass

    def html(self, req):
        return ""

    def status(self):
        return httpstatus.HTTP_OK

    def select_style_link(self, style):
        """Link for changing the current style without changing anything else"""
        return "#"