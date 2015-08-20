from core.transition import httpstatus


class Content:

    def feedback(self, req):
        pass

    def html(self, req):
        return ""

    def status(self):
        return httpstatus.HTTP_OK
