class BankError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class AuthenticationError(BankError):
    status_code = 401


class NotFoundError(BankError):
    status_code = 404


class ConflictError(BankError):
    status_code = 409