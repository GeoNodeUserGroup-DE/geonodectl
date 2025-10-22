class GeonodeCmdOutObjectKey:
    def __str__(self):
        return getattr(self, "key", "")
    def get_key(self, obj):
        return obj.get(getattr(self, "key", ""), "")

class GeonodeCmdOutListKey(GeonodeCmdOutObjectKey):
    def __init__(self, type=list, key="pk"):
        self.type = type
        self.key = key

# Supports nested key extraction using dot notation
class GeonodeCmdOutNestedKey(GeonodeCmdOutObjectKey):
    def __init__(self, key: str):
        self.key = key

    def get_key(self, obj):
        keys = self.key.split('.')
        value = obj
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, "")
            else:
                return ""
        return value if value is not None else ""
