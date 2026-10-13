CLEAN_SQL = [
    "TRUNCATE TABLE role_permissions",
    "TRUNCATE TABLE user_roles",
    "TRUNCATE TABLE permissions",
    "TRUNCATE TABLE roles",
    "TRUNCATE TABLE dept",
    "TRUNCATE TABLE admin_login_logs",
    "TRUNCATE TABLE admin_logs",
    "TRUNCATE TABLE admin_users",
    "TRUNCATE TABLE express_companies",
    "TRUNCATE TABLE member_level",
]

DEPTS = [
    (1, 0, "总部", 0),
    (2, 1, "运营部", 1),
    (3, 1, "技术部", 2),
]

ROLES = [
    ("admin", "超级管理员", "拥有系统全部权限", 3),
    ("operator", "运营专员", "商品/订单/用户模块权限", 2),
]

EXPRESS = [
    ("速达速运", "SD"),
    ("远通速递", "YT"),
    ("众通快递", "ZT"),
    ("迅达快递", "XD"),
    ("迅捷物流", "XJ"),
    ("环球邮政", "EM"),
]

MEMBER_LEVELS = [
    ("普通会员", 0.00, 0, 10.00, "基础会员权益"),
    ("黄金会员", 1000.00, 1000, 9.50, "95折购物"),
    ("钻石会员", 5000.00, 5000, 9.00, "9折购物+专属客服"),
]

MODULES = [
    {
        "key": "dashboard",
        "name": "仪表盘",
        "path": "/dashboard",
        "icon": "dashboard",
        "sort": 1,
        "pages": [],
        "buttons": [("查看仪表盘", "dashboard:view", 1)],
    },
    {
        "key": "goods",
        "name": "商品管理",
        "path": "/goods",
        "icon": "goods",
        "sort": 2,
        "pages": [
            ("商品列表", "/goods/list", 1),
            ("商品分类", "/goods/category", 2),
            ("品牌管理", "/goods/brand", 3),
            ("规格属性", "/goods/spec-attr", 4),
            ("评论管理", "/goods/comment", 5),
        ],
        "buttons": [
            ("查看商品", "goods:list", 1),
            ("新增商品", "goods:add", 2),
            ("编辑商品", "goods:edit", 3),
            ("删除商品", "goods:delete", 4),
            ("导出商品", "goods:export", 5),
            ("商品/评论审核", "goods:audit", 6),
        ],
    },
    {
        "key": "order",
        "name": "订单管理",
        "path": "/order",
        "icon": "order",
        "sort": 3,
        "pages": [
            ("订单列表", "/order/list", 1),
            ("售后管理", "/order/after-sale", 2),
            ("物流公司", "/order/logistics", 3),
        ],
        "buttons": [
            ("查看订单", "order:list", 1),
            ("新增物流", "order:add", 2),
            ("修改价格", "order:edit", 3),
            ("订单发货", "order:ship", 4),
            ("取消订单", "order:cancel", 5),
            ("导出订单", "order:export", 6),
            ("售后审核", "order:audit", 7),
        ],
    },
    {
        "key": "member",
        "name": "用户管理",
        "path": "/member",
        "icon": "member",
        "sort": 4,
        "pages": [
            ("会员列表", "/member/list", 1),
            ("会员等级", "/member/level", 2),
            ("积分管理", "/member/points", 3),
        ],
        "buttons": [
            ("查看会员", "member:list", 1),
            ("新增等级", "member:add", 2),
            ("编辑会员", "member:edit", 3),
        ],
    },
    {
        "key": "marketing",
        "name": "营销管理",
        "path": "/marketing",
        "icon": "marketing",
        "sort": 5,
        "pages": [
            ("优惠券", "/marketing/coupon", 1),
            ("秒杀活动", "/marketing/seckill", 2),
            ("满减满折", "/marketing/full-discount", 3),
            ("拼团活动", "/marketing/group-buy", 4),
            ("分销管理", "/marketing/distributor", 5),
        ],
        "buttons": [
            ("查看营销", "marketing:list", 1),
            ("新增营销", "marketing:add", 2),
            ("编辑营销", "marketing:edit", 3),
            ("删除营销", "marketing:delete", 4),
        ],
    },
    {
        "key": "content",
        "name": "内容管理",
        "path": "/content",
        "icon": "content",
        "sort": 6,
        "pages": [
            ("文章管理", "/content/article", 1),
            ("广告管理", "/content/ad", 2),
            ("公告通知", "/content/notice", 3),
        ],
        "buttons": [
            ("查看内容", "content:list", 1),
            ("新增内容", "content:add", 2),
            ("编辑内容", "content:edit", 3),
            ("删除内容", "content:delete", 4),
        ],
    },
    {
        "key": "settings",
        "name": "系统设置",
        "path": "/settings",
        "icon": "settings",
        "sort": 7,
        "pages": [
            ("基本设置", "/settings/basic", 1),
            ("运费模板", "/settings/freight", 2),
        ],
        "buttons": [
            ("查看设置", "settings:list", 1),
            ("新增模板", "settings:add", 2),
            ("修改设置", "settings:edit", 3),
            ("删除模板", "settings:delete", 4),
        ],
    },
    {
        "key": "permission",
        "name": "权限管理",
        "path": "/permission",
        "icon": "permission",
        "sort": 8,
        "pages": [
            ("管理员", "/permission/admin", 1),
            ("角色管理", "/permission/role", 2),
            ("权限资源", "/permission/resource", 3),
            ("部门管理", "/permission/dept", 4),
            ("登录日志", "/permission/login-log", 5),
        ],
        "buttons": [
            ("查看权限", "permission:list", 1),
            ("新增权限", "permission:add", 2),
            ("编辑权限", "permission:edit", 3),
            ("删除权限", "permission:delete", 4),
        ],
    },
    {
        "key": "logs",
        "name": "操作日志",
        "path": "/logs",
        "icon": "logs",
        "sort": 9,
        "pages": [],
        "buttons": [
            ("查看日志", "logs:list", 1),
            ("导出日志", "logs:export", 2),
        ],
    },
    {
        "key": "common",
        "name": "公共能力",
        "path": "/common",
        "icon": "common",
        "sort": 10,
        "pages": [],
        "buttons": [
            ("上传图片", "upload:add", 1),
        ],
    },
]


def build_perm_tree() -> list[dict]:
    tree = []
    for mod in MODULES:
        node: dict = {
            "name": mod["name"],
            "type": "menu",
            "path": mod["path"],
            "icon": mod.get("icon", ""),
            "sort": mod["sort"],
            "children": [],
        }
        for pname, ppath, psort in mod["pages"]:
            node["children"].append({"name": pname, "type": "menu", "path": ppath, "sort": 100 + psort})
        for bname, bcode, bsort in mod["buttons"]:
            node["children"].append({"name": bname, "type": "button", "code": bcode, "sort": 200 + bsort})
        tree.append(node)
    return tree


PERM_TREE = build_perm_tree()

SYSTEM_CONFIGS = [
    ("basic.site_name", "随心商城", "站点名称", "basic"),
    ("basic.site_logo", "/manager/images/logo.png", "站点Logo", "basic"),
    ("basic.site_url", "http://127.0.0.1:8000", "站点地址", "basic"),
    ("basic.service_phone", "400-000-0000", "客服电话", "basic"),
    ("basic.service_email", "service@example.com", "客服邮箱", "basic"),
    ("basic.site_description", "随心商城致力于为用户提供优质、实惠的商品和贴心的服务。", "商城简介", "basic"),
    ("basic.record_no", "", "备案号", "basic"),
    ("basic.copyright", "© 2026 shop-open · 开源演示项目，非真实商户", "版权信息", "basic"),
    ("basic.comment_audit_enabled", "0", "评价审核开关", "basic"),
    ("basic.stock_warn_enabled", "0", "库存预警开关", "basic"),
    ("goods.audit_enabled", "0", "新商品审核开关", "goods"),
    ("payment.pay_timeout", "120", "支付超时(分钟)", "payment"),
    ("payment.is_cod", "0", "是否支持货到付款", "payment"),
    ("payment.wechat_enabled", "1", "扫码支付开关", "payment"),
    ("payment.wechat_appid", "", "扫码支付 AppID", "payment"),
    ("payment.wechat_mch_id", "", "扫码支付商户号", "payment"),
    ("payment.wechat_api_key", "", "扫码支付 API 密钥", "payment"),
    ("payment.alipay_enabled", "1", "快捷支付开关", "payment"),
    ("payment.alipay_app_id", "", "快捷支付应用ID", "payment"),
    ("payment.alipay_private_key", "", "快捷支付应用私钥", "payment"),
    ("logistics.track_key", "", "物流查询授权key", "logistics"),
    ("logistics.ship_address", "", "发货地址", "logistics"),
    ("logistics.ship_contact", "", "发货人", "logistics"),
    ("logistics.ship_phone", "", "发货电话", "logistics"),
    ("logistics.ship_time", "24", "默认发货时间(小时)", "logistics"),
    ("logistics.track_provider", "", "物流查询接口", "logistics"),
    ("notify.sms_enabled", "0", "短信开关", "notify"),
    ("notify.sms_provider", "", "短信服务商", "notify"),
    ("notify.sms_access_key_id", "", "短信 AccessKey ID", "notify"),
    ("notify.sms_access_key_secret", "", "短信 AccessKey Secret", "notify"),
    ("notify.sms_sign", "", "短信签名", "notify"),
    ("notify.sms_verify_template", "", "验证码模板ID", "notify"),
    ("notify.email_enabled", "0", "邮件开关", "notify"),
    ("notify.smtp_host", "", "SMTP 服务器", "notify"),
    ("notify.smtp_port", "465", "SMTP 端口", "notify"),
    ("notify.smtp_from", "", "发件邮箱", "notify"),
    ("notify.smtp_auth_code", "", "邮箱授权码", "notify"),
]

# code, name, parent_code, level, sort（演示省市区子集，按 code 幂等 upsert）
REGIONS = [
    ("110000", "北京市", "", 1, 1),
    ("110100", "北京市", "110000", 2, 1),
    ("110105", "朝阳区", "110100", 3, 1),
    ("110108", "海淀区", "110100", 3, 2),
    ("310000", "上海市", "", 1, 2),
    ("310100", "上海市", "310000", 2, 1),
    ("310115", "浦东新区", "310100", 3, 1),
    ("310101", "黄浦区", "310100", 3, 2),
    ("440000", "广东省", "", 1, 3),
    ("440100", "广州市", "440000", 2, 1),
    ("440106", "天河区", "440100", 3, 1),
    ("440104", "越秀区", "440100", 3, 2),
    ("440300", "深圳市", "440000", 2, 2),
    ("440305", "南山区", "440300", 3, 1),
    ("440304", "福田区", "440300", 3, 2),
]


async def insert_perm_tree(exec, fetch):
    """幂等建权限树：已存在（按 code，其次按 path+type 匹配）的节点跳过，只补缺失项。
    这样开源后新增模块/权限码，重跑 seed base 即可生效，无需清库重来。"""

    async def walk(nodes, parent_id):
        for node in sorted(nodes, key=lambda x: x.get("sort", 0)):
            rid = None
            if node.get("code"):
                r = await fetch("SELECT id FROM permissions WHERE code=%s LIMIT 1", (node["code"],))
                rid = r[0]["id"] if r else None
            if rid is None and node.get("path"):
                r = await fetch(
                    "SELECT id FROM permissions WHERE path=%s AND permission_type=%s LIMIT 1",
                    (node["path"], node["type"]),
                )
                rid = r[0]["id"] if r else None
            if rid is None:
                rid = await exec(
                    "INSERT INTO permissions (parent_id, permission_type, name, code, path, icon, sort, status) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,1)",
                    (parent_id, node["type"], node["name"], node.get("code"), node.get("path"), node.get("icon"), node.get("sort", 0)),
                )
            children = node.get("children")
            if children:
                await walk(children, rid)

    await walk(PERM_TREE, 0)


async def seed_dict(exec):
    """字典类基础数据：快递/会员等级/系统配置。全部 INSERT IGNORE，可反复执行补齐。"""
    for name, code in EXPRESS:
        await exec("INSERT IGNORE INTO express_companies (name, code, status) VALUES (%s,%s,1)", (name, code))
    for name, amount, points, rate, benefits in MEMBER_LEVELS:
        await exec(
            "INSERT IGNORE INTO member_level (level_name, upgrade_amount, upgrade_points, discount_rate, benefits, status) "
            "VALUES (%s,%s,%s,%s,%s,1)",
            (name, amount, points, rate, benefits),
        )
    for key, value, remark, group in SYSTEM_CONFIGS:
        await exec(
            "INSERT IGNORE INTO system_configs (config_key, config_value, remark, config_group) VALUES (%s,%s,%s,%s)",
            (key, value, remark, group),
        )


async def seed(exec, fetch):
    for code, name, parent_code, level, sort in REGIONS:
        await exec(
            "INSERT INTO region (code,name,parent_code,level,sort,status) VALUES (%s,%s,%s,%s,%s,1) "
            "ON DUPLICATE KEY UPDATE name=VALUES(name),parent_code=VALUES(parent_code),"
            "level=VALUES(level),sort=VALUES(sort),status=1",
            (code, name, parent_code, level, sort),
        )
    existed = await fetch("SELECT COUNT(*) AS c FROM roles WHERE role_key='admin'")
    if existed and existed[0]["c"]:
        # 已初始化：不再重建角色与管理员，但仍幂等补齐权限树、超管授权与字典数据，
        # 否则开源后新增权限码/配置项在已有库上永远不生效
        await insert_perm_tree(exec, fetch)
        perms = await fetch("SELECT id, code FROM permissions")
        role_row = await fetch("SELECT id FROM roles WHERE role_key='admin' LIMIT 1")
        if role_row:
            for p in perms:
                await exec(
                    "INSERT IGNORE INTO role_permissions (role_id, permission_id) VALUES (%s,%s)",
                    (role_row[0]["id"], p["id"]),
                )
        await seed_dict(exec)
        return
    for did, parent_id, name, sort in DEPTS:
        await exec(
            "INSERT IGNORE INTO dept (id, parent_id, dept_name, sort, status) VALUES (%s,%s,%s,%s,1)",
            (did, parent_id, name, sort),
        )
    dept_row = await fetch("SELECT id FROM dept WHERE dept_name='总部' LIMIT 1")
    hq_id = dept_row[0]["id"] if dept_row else None

    admin_role_id = None
    for key, name, desc, scope in ROLES:
        rid = await exec(
            "INSERT INTO roles (role_name, role_key, description, data_scope, status) VALUES (%s,%s,%s,%s,1)",
            (name, key, desc, scope),
        )
        if key == "admin":
            admin_role_id = rid

    await insert_perm_tree(exec, fetch)
    perms = await fetch("SELECT id, code FROM permissions")
    perm_ids = [p["id"] for p in perms]
    if admin_role_id:
        for pid in perm_ids:
            await exec("INSERT IGNORE INTO role_permissions (role_id, permission_id) VALUES (%s,%s)", (admin_role_id, pid))

    operator_code_grants = [
        "goods:list",
        "goods:add",
        "goods:edit",
        "goods:delete",
        "goods:export",
        "order:list",
        "order:edit",
        "order:ship",
        "order:cancel",
        "order:export",
        "member:list",
        "member:edit",
    ]
    operator_role = await fetch("SELECT id FROM roles WHERE role_key='operator' LIMIT 1")
    if operator_role:
        operator_id = operator_role[0]["id"]
        granted = {p["id"] for p in perms if p["code"] in operator_code_grants}
        for pid in granted:
            await exec("INSERT IGNORE INTO role_permissions (role_id, permission_id) VALUES (%s,%s)", (operator_id, pid))

    import os
    import secrets

    import bcrypt

    exists = await fetch("SELECT id FROM admin_users WHERE username='admin' LIMIT 1")
    if exists:
        admin_id = exists[0]["id"]
        # 幂等同步口令：ADMIN_INIT_PASSWORD 对已存在的账号同样生效。
        # 旧实现只在首次创建时使用它，导致「先建号、后设口令」的人按 README 重跑 base
        # 却怎么也对不上 —— 测试随即整片失败且看不出原因。
        init_pwd = os.getenv("ADMIN_INIT_PASSWORD")
        if init_pwd:
            pwd_hash = bcrypt.hashpw(init_pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            await exec(
                "UPDATE admin_users SET password_hash=%s, login_fail_count=0, locked_until=NULL WHERE id=%s",
                (pwd_hash, admin_id),
            )
            print("[seed] 已按 ADMIN_INIT_PASSWORD 同步 admin 口令")
    else:
        init_pwd = os.getenv("ADMIN_INIT_PASSWORD") or secrets.token_urlsafe(10)
        pwd_hash = bcrypt.hashpw(init_pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        admin_id = await exec(
            "INSERT INTO admin_users (username, password_hash, real_name, phone, email, dept_id, status) "
            "VALUES ('admin', %s, '超级管理员', '10000000000', 'admin@example.com', %s, 1)",
            (pwd_hash, hq_id),
        )
        print(f"[seed] 已创建默认管理员 admin，初始密码：{init_pwd}（请登录后立即修改）")
    if admin_role_id:
        await exec("INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (%s,%s)", (admin_id, admin_role_id))

    await seed_dict(exec)
