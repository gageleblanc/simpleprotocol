import json
import re


class GenericTxParser:
    default_headers = []

    def __init__(self, raw: str, requester: dict = None, headers: list = None, strict: bool = False):
        if headers is None:
            headers = self.default_headers
        else:
            headers += self.default_headers
        self.requester = requester
        self._headers = headers
        self._strict = strict
        attrs = self._parse_response(raw)
        self._parsed_response = attrs
        if "type" in attrs and "response" in attrs:
            if attrs["type"] == "json":
                attrs["response"] = json.loads(attrs["response"])
        for k, v in attrs.items():
            if strict:
                if k in headers:
                    setattr(self, k.lower(), v)
            else:
                setattr(self, k.lower(), v)

    def __str__(self):
        final = ""
        for key, value in self._parsed_response.items():
            if not re.match(r"\A[a-zA-Z]", key):
                continue
            if not value:
                continue
            final += "%s:%s\n" % (key, value)
        return final + "\n\n"

    def _parse_response(self, response: str):
        res_dict = {}
        lines = response.split("\n")
        for line in lines:
            parts = line.split(":", 1)
            if len(parts) > 1:
                key = parts[0].strip().lower()
                val = parts[1].strip()
                # Make sure key starts with alpha
                if not re.match(r"\A[a-zA-Z]", key):
                    continue
                if self._strict:
                    # If strict, don't include headers that aren't in _headers
                    if key not in self._headers:
                        continue
                res_dict[key] = val
        if self._strict:
            for header in self._headers:
                if header not in res_dict:
                    # If strict, make sure payload contains required headers
                    raise ValueError("Required header %s not in payload.")
        return res_dict

class GenericRequestParser(GenericTxParser):
    default_headers = ["method"]

class GenericResponseParser(GenericTxParser):
    status = 0
    default_headers = ["status"]

class GenericTxBuilder:
    method = None

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if not re.match(r"\A[a-zA-Z]", key):
                continue
            if type(value) == str:
                value.replace("\n", " ")
            setattr(self, key.lower(), value)

    def get_parsed(self):
        return GenericRequestParser(self.__str__())

    def __str__(self):
        final = ""
        for key, value in self.__dict__.items():
            if not re.match(r"\A[a-zA-Z]", key):
                continue
            if not value:
                continue
            final += "%s:%s\n" % (key, value)
        return final + "\n\n"
