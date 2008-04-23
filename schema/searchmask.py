class SearchMaskItem:
    def getFirstField(self):
        if self.getNumChildren():
            return self.getChildren()[0]
        return None
