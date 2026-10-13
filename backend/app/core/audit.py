from core import database

ACTION_LOGIN = 1
ACTION_ADD = 2
ACTION_EDIT = 3
ACTION_DELETE = 4
ACTION_EXPORT = 5
ACTION_LOGOUT = 6
ACTION_AUDIT = 7


async def log_action(admin_id: int, module: str, action_type: int, target: str = "", summary: str = "", ip: str = ""):
    await database.execute(
        "INSERT INTO admin_logs (admin_id, module, action_type, target, ip, params_summary) VALUES (%s,%s,%s,%s,%s,%s)",
        (admin_id, module, action_type, target, ip, summary),
    )


async def log_login(admin_id: int, ip: str, user_agent: str, success: int, username: str = ""):
    await database.execute(
        "INSERT INTO admin_login_logs (admin_id, username, ip, user_agent, success) VALUES (%s,%s,%s,%s,%s)",
        (admin_id, username, ip, user_agent, success),
    )
