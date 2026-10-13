def ok(data=None, message: str = "success"):
    return {"code": 0, "message": message, "data": data}


def page_data(rows, total: int, page: int, page_size: int):
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


def error_body(code: int, message: str, http_status: int = 200):
    return {"code": code, "message": message, "data": None}
