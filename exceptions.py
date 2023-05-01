class ErorSendMessage(Exception):
    pass


class StatusNotCode(Exception):
    pass


class ApiStatus(Exception):
    pass


class ResponseAnswerEmpty(Exception):
    pass


class ResponseAnswerNotDict(TypeError):
    pass


class HomeworksNotKeys(Exception):
    pass


class HomeworksNotKeysData(Exception):
    pass


class ResponseAnswerNlist(TypeError):
    pass


class CheckApiResponseStat(Exception):
    pass


class CheckApiResponseKey(Exception):
    pass


class CheckApiResponse(Exception):
    pass


class InvalidJSONError(TypeError):
    pass
