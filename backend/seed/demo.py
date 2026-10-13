"""demo 演示数据（可整删）。

执行：python -m seed.runner <demo|clean-demo>
约定：
1. 与业务代码零耦合，仅用于本地演示/测试；
2. 全部按业务键幂等（商品/SKU/图片按 id，订单按 order_no，会员按 id+phone，
   流水类按“成员+事由/订单+动作”哨兵），重复执行只补齐缺失数据、不翻倍；
3. 图片使用项目内真实素材：front/images/* → 同步到 uploads/seed/，
   数据内 url 为可访问绝对地址（默认 http://127.0.0.1:8001/uploads/seed/xxx.svg）。
"""

import shutil
from pathlib import Path

CLEAN_SQL = [
    "TRUNCATE TABLE order_logs",
    "TRUNCATE TABLE order_items",
    "TRUNCATE TABLE orders",
    "TRUNCATE TABLE goods_sku_spec_values",
    "TRUNCATE TABLE goods_sku",
    "TRUNCATE TABLE goods_images",
    "TRUNCATE TABLE goods_comments",
    "TRUNCATE TABLE goods",
    "TRUNCATE TABLE goods_category",
    "TRUNCATE TABLE brands",
    "TRUNCATE TABLE specification_values",
    "TRUNCATE TABLE specifications",
    "TRUNCATE TABLE attribute_values",
    "TRUNCATE TABLE attributes",
    "TRUNCATE TABLE members",
    "TRUNCATE TABLE member_logs",
    "TRUNCATE TABLE points_logs",
    "TRUNCATE TABLE coupon_receive",
    "TRUNCATE TABLE coupons",
    "TRUNCATE TABLE after_sales",
    "TRUNCATE TABLE seckill_activities",
    "TRUNCATE TABLE full_discount_activities",
    "TRUNCATE TABLE group_buy_activities",
    "TRUNCATE TABLE commission_logs",
    "TRUNCATE TABLE distributor",
    "TRUNCATE TABLE articles",
    "TRUNCATE TABLE article_categories",
    "TRUNCATE TABLE ads",
    "TRUNCATE TABLE ad_positions",
    "TRUNCATE TABLE notices",
    "TRUNCATE TABLE freight_templates",
    "TRUNCATE TABLE member_cart",
    "TRUNCATE TABLE member_address",
    "TRUNCATE TABLE sms_codes",
]

CATEGORIES = [
    (1, 0, "手机数码"),
    (2, 1, "智能手机"),
    (3, 1, "笔记本电脑"),
    (4, 0, "家用电器"),
    (5, 4, "大家电"),
    (6, 1, "智能穿戴"),
    (7, 0, "电视"),
    (8, 7, "随心电视"),
    (9, 7, "随享电视"),
    (10, 0, "笔记本 平板"),
    (11, 10, "笔记本"),
    (12, 10, "平板"),
    (13, 0, "出行 穿戴"),
    (14, 13, "智能手表"),
    (15, 13, "平衡车"),
    (16, 0, "耳机 音箱"),
    (17, 16, "真无线耳机"),
    (18, 16, "智能音箱"),
    (19, 0, "健康 儿童"),
    (20, 19, "儿童手表"),
    (21, 0, "生活 箱包"),
    (22, 21, "箱包"),
    (23, 0, "智能 路由器"),
    (24, 23, "路由器"),
    (25, 0, "电源 配件"),
    (26, 25, "充电器"),
    (27, 0, "智能家居"),
    (28, 27, "扫地机器人"),
    (29, 27, "智能门锁"),
    (30, 4, "生活电器"),
    (31, 25, "数据线"),
]

BRANDS = [
    (1, "随心", "随心官方"),
    (2, "智选", "智选官方"),
    (3, "优拍", "优拍官方"),
    (4, "鲜语", "鲜语官方"),
]

SPECS = [
    (1, "颜色", 2),
    (2, "存储", 2),
    (3, "尺寸", 5),
]

SPEC_VALUES = [
    (1, 1, "黑色"),
    (2, 1, "白色"),
    (3, 1, "远山蓝"),
    (4, 2, "12GB+256GB"),
    (5, 2, "16GB+512GB"),
    (6, 3, "75英寸"),
]

ATTRS = [
    (1, "屏幕", 2),
    (2, "处理器", 2),
    (3, "能效等级", 5),
]

ATTR_VALUES = [
    (1, 1, "6.36英寸"),
    (2, 1, "6.67英寸"),
    (3, 2, "星核8 旗舰版"),
    (4, 2, "星核8 三代"),
    (5, 3, "一级能效"),
]

# id, name, subtitle, category_id, brand_id, spu_code, unit,
# market_price, price, cost_price, stock, warn_stock, status, sales, is_recommend, is_hot, is_new
GOODS = [
    (1, "随心 X1 Pro", "旗舰影像 星核8 旗舰版", 2, 1, "SPU00001", "件", "5499.00", "4999.00", "4300.00", 300, 20, 1, 1280, 1, 1, 1),
    (2, "随享 K8", "2K直屏 性能旗舰", 2, 1, "SPU00002", "件", "2799.00", "2499.00", "2100.00", 500, 30, 1, 3460, 0, 1, 1),
    (3, "随心笔记本 Pro 16", "3.1K OLED 轻薄本", 3, 1, "SPU00003", "台", "7999.00", "6999.00", "6200.00", 120, 10, 1, 620, 1, 1, 0),
    (4, "随心电视 S Pro 75", "Mini LED 影院级体验", 5, 1, "SPU00004", "台", "5999.00", "4999.00", "4500.00", 200, 15, 1, 880, 0, 0, 1),
    (5, "鲜语冰箱 450L", "一级能效 风冷无霜", 5, 4, "SPU00005", "台", "3299.00", "2799.00", "2400.00", 150, 10, 1, 510, 0, 0, 1),
    (6, "随心耳机 A6", "深度降噪 长续航", 6, 1, "SPU00006", "副", "499.00", "399.00", "320.00", 800, 50, 1, 2350, 1, 1, 0),
    (7, "随心平板 P5 Pro", "2.8K 144Hz 影音平板", 12, 1, "SPU00007", "台", "2599.00", "2299.00", "1900.00", 260, 20, 1, 730, 1, 1, 1),
    (8, "智能手表 S3", "蓝牙通话 血氧监测", 14, 1, "SPU00008", "块", "899.00", "699.00", "520.00", 400, 30, 1, 1120, 1, 0, 1),
    (9, "扫地机器人", "自动集尘 激光导航", 28, 1, "SPU00009", "台", "1999.00", "1699.00", "1300.00", 180, 15, 1, 640, 1, 1, 0),
    (10, "智能门锁 M20", "3D人脸识别 指纹锁", 29, 1, "SPU00010", "台", "1699.00", "1499.00", "1100.00", 220, 15, 1, 480, 0, 1, 1),
    (11, "空调 1.5匹", "新一级能效 变频冷暖", 5, 1, "SPU00011", "台", "2699.00", "2199.00", "1750.00", 200, 20, 1, 560, 1, 0, 0),
    (12, "洗衣机 10kg", "洗烘一体 高温除菌", 5, 1, "SPU00012", "台", "2299.00", "1899.00", "1500.00", 160, 15, 1, 420, 0, 1, 0),
    (13, "循环风扇", "静音落地扇 遥控款", 30, 1, "SPU00013", "台", "399.00", "299.00", "210.00", 600, 40, 1, 1580, 0, 1, 1),
    (14, "智能音箱 Sound", "智能家居中控 360°音效", 18, 1, "SPU00014", "台", "799.00", "599.00", "430.00", 350, 25, 1, 690, 1, 1, 0),
    (15, "随享 N13", "一亿像素 长续航", 2, 1, "SPU00015", "件", "1599.00", "1299.00", "1000.00", 700, 40, 1, 2890, 0, 1, 1),
    (16, "随心 X7", "旗舰四摄 旗舰影像", 2, 1, "SPU00016", "件", "6299.00", "5799.00", "4900.00", 150, 15, 1, 320, 1, 1, 1),
    (17, "鲜语冰箱 508L", "十字对开门 母婴级", 5, 4, "SPU00017", "台", "4599.00", "3999.00", "3300.00", 100, 10, 1, 260, 0, 0, 1),
    (18, "随心轻薄本 Air 14", "轻薄办公 长续航", 11, 1, "SPU00018", "台", "5499.00", "4999.00", "4200.00", 140, 10, 1, 380, 1, 0, 1),
    (19, "随心电视 S Pro 65", "Mini LED 高刷屏", 8, 1, "SPU00019", "台", "4299.00", "3699.00", "3100.00", 180, 15, 1, 540, 1, 1, 1),
    (20, "随心耳机 A8", "主动降噪 空间音频", 17, 1, "SPU00020", "副", "799.00", "649.00", "500.00", 500, 30, 1, 960, 1, 1, 1),
]

# goods_id, image_id, 图片文件名（源 front/images）, sort, type
GOODS_IMAGES = [
    (1, 1, "phone-x1-1.svg", 1, 1),
    (1, 2, "phone-x1-2.svg", 2, 1),
    (1, 3, "phone-x1-back.svg", 3, 1),
    (2, 4, "phone-k8.svg", 1, 1),
    (2, 5, "phone-n13.svg", 2, 1),
    (3, 6, "laptop-slim16.svg", 1, 1),
    (3, 7, "laptop-slim.svg", 2, 1),
    (4, 8, "tv-s-1.svg", 1, 1),
    (4, 9, "tv-s-2.svg", 2, 1),
    (4, 10, "tv-s-3.svg", 3, 1),
    (5, 11, "fridge-450.svg", 1, 1),
    (5, 12, "fridge-256.svg", 2, 1),
    (6, 13, "earphone-a6.svg", 1, 1),
    (6, 14, "earphone-a6-black.svg", 2, 1),
    (7, 15, "pad-p5.svg", 1, 1),
    (8, 16, "band-s3-1.svg", 1, 1),
    (8, 17, "band-s3-2.svg", 2, 1),
    (8, 18, "band-s3-3.svg", 3, 1),
    (9, 19, "robot-1.svg", 1, 1),
    (9, 20, "robot-2.svg", 2, 1),
    (10, 21, "lock-1.svg", 1, 1),
    (10, 22, "lock-2.svg", 2, 1),
    (11, 23, "ac-1.svg", 1, 1),
    (11, 24, "ac-2.svg", 2, 1),
    (12, 25, "washer-1.svg", 1, 1),
    (12, 26, "washer-2.svg", 2, 1),
    (12, 27, "washer-3.svg", 3, 1),
    (13, 28, "fan-1.svg", 1, 1),
    (13, 29, "fan-2.svg", 2, 1),
    (13, 30, "fan-3.svg", 3, 1),
    (14, 31, "speaker-sound-1.svg", 1, 1),
    (14, 32, "speaker-sound-2.svg", 2, 1),
    (15, 33, "phone-n13.svg", 1, 1),
    (15, 34, "phone-s2-12.svg", 2, 1),
    (16, 35, "phone-x1-2.svg", 1, 1),
    (16, 36, "phone-x1-back.svg", 2, 1),
    (17, 37, "fridge-508.svg", 1, 1),
    (18, 38, "laptop-slim.svg", 1, 1),
    (19, 39, "tv-s-2.svg", 1, 1),
    (19, 40, "tv-s-3.svg", 2, 1),
    (20, 41, "earphone-a8.svg", 1, 1),
    (20, 42, "earphone-a3.svg", 2, 1),
]

# sku_id, goods_id, sku_code, price, stock, 主图文件名
SKUS = [
    (1, 1, "SKU-X1PRO-BLK-256", "4999.00", 180, "phone-x1-1.svg"),
    (2, 1, "SKU-X1PRO-WHT-512", "5499.00", 120, "phone-x1-2.svg"),
    (3, 2, "SKU-K8-12-256", "2499.00", 500, "phone-k8.svg"),
    (4, 3, "SKU-N16-32-1T", "6999.00", 120, "laptop-slim16.svg"),
    (5, 4, "SKU-TV75-STD", "4999.00", 200, "tv-s-1.svg"),
    (6, 5, "SKU-FRIDGE450", "2799.00", 150, "fridge-450.svg"),
    (7, 6, "SKU-A6-BLK", "399.00", 800, "earphone-a6.svg"),
    (8, 7, "SKU-PADP5-256", "2299.00", 260, "pad-p5.svg"),
    (9, 8, "SKU-WATCHS3-BLK", "699.00", 400, "band-s3-1.svg"),
    (10, 9, "SKU-ROBOT-STD", "1699.00", 180, "robot-1.svg"),
    (11, 10, "SKU-LOCK-M20", "1499.00", 220, "lock-1.svg"),
    (12, 11, "SKU-AC-15", "2199.00", 200, "ac-1.svg"),
    (13, 12, "SKU-WASHER-10KG", "1899.00", 160, "washer-1.svg"),
    (14, 13, "SKU-FAN-STD", "299.00", 600, "fan-1.svg"),
    (15, 14, "SKU-SOUND-STD", "599.00", 350, "speaker-sound-1.svg"),
    (16, 15, "SKU-N13-256", "1299.00", 700, "phone-n13.svg"),
    (17, 16, "SKU-X7-512", "5799.00", 150, "phone-x1-2.svg"),
    (18, 17, "SKU-FRIDGE508", "3999.00", 100, "fridge-508.svg"),
    (19, 18, "SKU-SLIM14", "4999.00", 140, "laptop-slim.svg"),
    (20, 19, "SKU-TV65-STD", "3699.00", 180, "tv-s-2.svg"),
    (21, 20, "SKU-A8-BLK", "649.00", 500, "earphone-a8.svg"),
    (22, 7, "SKU-PADP5-512", "2599.00", 120, "pad-p5.svg"),
    (23, 8, "SKU-WATCHS3-WHT", "749.00", 200, "band-s3-2.svg"),
    (24, 15, "SKU-N13-512", "1499.00", 300, "phone-s2-12.svg"),
]

SKU_SPEC_VALUES = [
    (1, 1, 1),
    (1, 2, 4),
    (2, 1, 3),
    (2, 2, 5),
    (3, 2, 4),
    (4, 2, 5),
    (5, 3, 6),
    (22, 2, 5),
    (23, 1, 2),
    (24, 2, 5),
]

# id, nickname, phone, points, total_consume, 等级名, status
MEMBERS = [
    (1, "张小明", "10000000001", 500, "5000.00", "黄金会员", 1),
    (2, "李小红", "10000000002", 1200, "12000.00", "钻石会员", 1),
    (3, "王大力", "10000000003", 80, "800.00", "普通会员", 1),
    (4, "刘晓芳", "10000000004", 300, "3000.00", "黄金会员", 1),
    (5, "陈大鹏", "10000000005", 6000, "60000.00", "钻石会员", 1),
    (6, "杨晓梅", "10000000006", 0, "0.00", "普通会员", 0),
]

# member_id, change_value, reason, type
POINTS_LOGS = [
    (1, 500, "注册赠送积分", 1),
    (2, 1200, "注册赠送积分", 1),
    (3, 80, "注册赠送积分", 1),
    (1, -50, "积分兑换优惠券", 3),
    (2, -200, "积分兑换优惠券", 3),
    (4, 300, "注册赠送积分", 1),
    (5, 5000, "注册赠送积分", 1),
    (5, 1000, "会员生日双倍积分", 1),
    (4, -100, "积分抵扣订单", 2),
    (1, 120, "订单完成返还积分", 1),
    (2, 260, "订单完成返还积分", 1),
]

# member_id, action_type, action
MEMBER_LOGS = [
    (1, "login", "用户登录成功"),
    (1, "order", "提交订单 202609031001"),
    (2, "login", "用户登录成功"),
    (2, "after_sale", "发起退货退款申请 202608151007"),
    (3, "register", "注册账号"),
    (4, "login", "用户登录成功"),
    (4, "order", "提交订单 202610021011"),
    (5, "login", "用户登录成功"),
    (5, "coupon", "领取优惠券「会员专享券」"),
    (6, "register", "注册账号"),
]

# order_no, member_id, total, freight, coupon, points_amt, pay_amt, pay_type, pay_status,
# order_status, receiver, phone, address, logistics_company, logistics_no, buyer_msg,
# source, paid_at, shipped_at, completed_at, created_at
ORDERS = [
    ("202609031001", 1, "4999.00", "0.00", "0.00", "0.00", "4999.00", 1, 1, 2, "张小明", "10000000001", "示例市示例区示例街道1号", None, None, None, "h5", "2026-09-03 10:00:00", None, None, "2026-09-03 10:00:00"),
    ("202609021002", 1, "2499.00", "0.00", "0.00", "0.00", "2499.00", 1, 1, 3, "张小明", "10000000001", "示例市示例区示例街道1号", "速达速运", "EX1234567890", None, "app", "2026-09-02 14:30:00", "2026-09-02 14:40:00", None, "2026-09-02 14:30:00"),
    ("202609021003", 2, "6999.00", "0.00", "100.00", "0.00", "6899.00", 2, 1, 2, "李小红", "10000000002", "示例市示例区示例路88号", None, None, None, "h5", "2026-09-02 09:12:00", None, None, "2026-09-02 09:12:00"),
    ("202608301004", 2, "399.00", "0.00", "0.00", "0.00", "399.00", 1, 1, 4, "李小红", "10000000002", "示例市示例区示例路88号", "迅捷物流", "EX99887766", None, "h5", "2026-08-30 16:20:00", "2026-08-30 16:25:00", "2026-09-01 12:00:00", "2026-08-30 16:20:00"),
    ("202608251005", 3, "4999.00", "0.00", "0.00", "0.00", "4999.00", 2, 1, 4, "王大力", "10000000003", "示例市示例区示例路6号", "众通快递", "EX55667788", None, "h5", "2026-08-25 11:00:00", "2026-08-25 11:06:00", "2026-08-27 18:00:00", "2026-08-25 11:00:00"),
    ("202608201006", 3, "2499.00", "0.00", "0.00", "0.00", "0.00", None, 0, 1, "王大力", "10000000003", "示例市示例区示例路6号", None, None, None, "h5", None, None, None, None),
    ("202608151007", 2, "2799.00", "0.00", "0.00", "0.00", "2799.00", 1, 1, 6, "李小红", "10000000002", "示例市示例区示例路88号", None, None, "外包装破损，申请退货", "h5", "2026-08-15 15:00:00", None, None, "2026-08-15 15:00:00"),
    ("202610011008", 1, "2299.00", "0.00", "0.00", "0.00", "2299.00", None, 0, 1, "张小明", "10000000001", "示例市示例区示例街道1号", None, None, "尽快发货", "h5", None, None, None, None),
    ("202610021009", 4, "1499.00", "0.00", "0.00", "0.00", "1499.00", None, 0, 1, "刘晓芳", "10000000004", "示例省示例市示例区示例园3号", None, None, None, "app", None, None, None, None),
    ("202610011010", 2, "599.00", "0.00", "0.00", "0.00", "599.00", 1, 1, 2, "李小红", "10000000002", "示例市示例区示例路88号", None, None, None, "h5", "2026-10-01 09:20:00", None, None, "2026-10-01 09:20:00"),
    ("202610021011", 4, "699.00", "0.00", "0.00", "1.00", "698.00", 1, 1, 2, "刘晓芳", "10000000004", "示例省示例市示例区示例园3号", None, None, "工作日送达", "h5", "2026-10-02 10:05:00", None, None, "2026-10-02 10:05:00"),
    ("202609281012", 1, "3498.00", "0.00", "0.00", "0.00", "3498.00", 1, 1, 3, "张小明", "10000000001", "示例市示例区示例街道1号", "远通速递", "EX1122334455", None, "h5", "2026-09-28 11:30:00", "2026-09-28 18:00:00", None, "2026-09-28 11:30:00"),
    ("202609291013", 4, "1699.00", "0.00", "0.00", "0.00", "1699.00", 2, 1, 3, "刘晓芳", "10000000004", "示例省示例市示例区示例园3号", "迅达快递", "EX5566778899", None, "app", "2026-09-29 15:10:00", "2026-09-29 20:30:00", None, "2026-09-29 15:10:00"),
    ("202609201014", 2, "2798.00", "0.00", "0.00", "0.00", "2798.00", 1, 1, 4, "李小红", "10000000002", "示例市示例区示例路88号", "速达速运", "EX9876543210", None, "h5", "2026-09-20 13:00:00", "2026-09-20 19:00:00", "2026-09-22 10:00:00", "2026-09-20 13:00:00"),
    ("202609181015", 5, "5799.00", "0.00", "100.00", "0.00", "5699.00", 1, 1, 4, "陈大鹏", "10000000005", "示例市示例区示例大街12号", "迅捷物流", "EX1122334455", None, "app", "2026-09-18 09:40:00", "2026-09-18 16:20:00", "2026-09-20 11:00:00", "2026-09-18 09:40:00"),
    ("202609101016", 5, "3999.00", "0.00", "0.00", "0.00", "3999.00", 2, 1, 4, "陈大鹏", "10000000005", "示例市示例区示例大街12号", "众通快递", "EX9988776655", None, "h5", "2026-09-10 10:15:00", "2026-09-10 17:40:00", "2026-09-13 09:00:00", "2026-09-10 10:15:00"),
    ("202609051017", 3, "299.00", "0.00", "0.00", "0.00", "299.00", None, 0, 5, "王大力", "10000000003", "示例市示例区示例路6号", None, None, None, "h5", None, None, None, "2026-09-05 08:30:00"),
    ("202609011018", 6, "1299.00", "0.00", "0.00", "0.00", "1299.00", None, 0, 5, "杨晓梅", "10000000006", "示例省示例市示例区示例路8号", None, None, None, "h5", None, None, None, "2026-09-01 20:10:00"),
]

# order_no, goods_id, sku_id, goods_name, price, quantity, subtotal
ORDER_ITEMS = [
    ("202609031001", 1, 1, "随心 X1 Pro", "4999.00", 1, "4999.00"),
    ("202609021002", 2, 3, "随享 K8", "2499.00", 1, "2499.00"),
    ("202609021003", 3, 4, "随心笔记本 Pro 16", "6999.00", 1, "6999.00"),
    ("202608301004", 6, 7, "随心耳机 A6", "399.00", 1, "399.00"),
    ("202608251005", 1, 1, "随心 X1 Pro", "4999.00", 1, "4999.00"),
    ("202608201006", 2, 3, "随享 K8", "2499.00", 1, "2499.00"),
    ("202608151007", 5, 6, "鲜语冰箱 450L", "2799.00", 1, "2799.00"),
    ("202610011008", 7, 8, "随心平板 P5 Pro", "2299.00", 1, "2299.00"),
    ("202610021009", 10, 11, "智能门锁 M20", "1499.00", 1, "1499.00"),
    ("202610011010", 14, 15, "智能音箱 Sound", "599.00", 1, "599.00"),
    ("202610021011", 8, 9, "智能手表 S3", "699.00", 1, "699.00"),
    ("202609281012", 6, 7, "随心耳机 A6", "399.00", 2, "798.00"),
    ("202609281012", 13, 14, "循环风扇", "299.00", 1, "299.00"),
    ("202609281012", 1, 2, "随心 X1 Pro", "5499.00", 1, "5499.00"),
    ("202609291013", 9, 10, "扫地机器人", "1699.00", 1, "1699.00"),
    ("202609201014", 12, 13, "洗衣机 10kg", "1899.00", 1, "1899.00"),
    ("202609201014", 5, 6, "鲜语冰箱 450L", "2799.00", 1, "2799.00"),
    ("202609181015", 16, 17, "随心 X7", "5799.00", 1, "5799.00"),
    ("202609101016", 17, 18, "鲜语冰箱 508L", "3999.00", 1, "3999.00"),
    ("202609051017", 13, 14, "循环风扇", "299.00", 1, "299.00"),
    ("202609011018", 15, 16, "随享 N13", "1299.00", 1, "1299.00"),
]

# order_no, operator_type, action, content
ORDER_LOGS = [
    ("202609031001", 1, "下单", "用户提交订单"),
    ("202609031001", 2, "付款", "扫码支付成功 4999.00 元"),
    ("202609021002", 1, "下单", "用户提交订单"),
    ("202609021002", 2, "付款", "扫码支付成功 2499.00 元"),
    ("202609021002", 2, "发货", "速达速运 EX1234567890"),
    ("202609021003", 1, "下单", "用户提交订单"),
    ("202609021003", 2, "付款", "快捷支付成功 6899.00 元"),
    ("202608301004", 1, "下单", "用户提交订单"),
    ("202608301004", 2, "付款", "扫码支付成功 399.00 元"),
    ("202608301004", 2, "发货", "迅捷物流 EX99887766"),
    ("202608301004", 2, "完成", "订单交易完成"),
    ("202608251005", 1, "下单", "用户提交订单"),
    ("202608251005", 2, "付款", "快捷支付成功 4999.00 元"),
    ("202608251005", 2, "发货", "众通快递 EX55667788"),
    ("202608251005", 2, "完成", "订单交易完成"),
    ("202608201006", 1, "下单", "用户提交订单"),
    ("202608151007", 1, "下单", "用户提交订单"),
    ("202608151007", 2, "付款", "扫码支付成功 2799.00 元"),
    ("202608151007", 2, "申请售后", "会员发起退货退款申请"),
    ("202610011008", 1, "下单", "用户提交订单"),
    ("202610021009", 1, "下单", "用户提交订单"),
    ("202610011010", 1, "下单", "用户提交订单"),
    ("202610011010", 2, "付款", "扫码支付成功 599.00 元"),
    ("202610021011", 1, "下单", "用户提交订单"),
    ("202610021011", 2, "付款", "扫码支付成功 698.00 元"),
    ("202609281012", 1, "下单", "用户提交订单"),
    ("202609281012", 2, "付款", "扫码支付成功 3498.00 元"),
    ("202609281012", 2, "发货", "远通速递 EX1122334455"),
    ("202609291013", 1, "下单", "用户提交订单"),
    ("202609291013", 2, "付款", "快捷支付成功 1699.00 元"),
    ("202609291013", 2, "发货", "迅达快递 EX5566778899"),
    ("202609201014", 1, "下单", "用户提交订单"),
    ("202609201014", 2, "付款", "扫码支付成功 2798.00 元"),
    ("202609201014", 2, "发货", "速达速运 EX9876543210"),
    ("202609201014", 2, "完成", "订单交易完成"),
    ("202609181015", 1, "下单", "用户提交订单"),
    ("202609181015", 2, "付款", "扫码支付成功 5699.00 元"),
    ("202609181015", 2, "发货", "迅捷物流 EX1122334455"),
    ("202609181015", 2, "完成", "订单交易完成"),
    ("202609101016", 1, "下单", "用户提交订单"),
    ("202609101016", 2, "付款", "快捷支付成功 3999.00 元"),
    ("202609101016", 2, "发货", "众通快递 EX9988776655"),
    ("202609101016", 2, "完成", "订单交易完成"),
    ("202609051017", 1, "下单", "用户提交订单"),
    ("202609051017", 1, "取消", "用户主动取消订单"),
    ("202609011018", 1, "下单", "用户提交订单"),
    ("202609011018", 1, "取消", "超时未支付自动取消"),
]

# after_sale_no, order_no, member_id, type, reason, amount, status
AFTER_SALES = [
    ("AS202608151001", "202608151007", 2, 2, "外包装破损，申请退货退款", "2799.00", 1),
    ("AS202609050002", "202609281012", 1, 2, "耳机杂音明显，申请退货退款", "798.00", 2),
    ("AS202608200003", "202608251005", 3, 1, "下单重复，仅退款", "4999.00", 3),
    ("AS202608180004", "202608301004", 2, 1, "商品已签收未收到赠品", "399.00", 4),
    ("AS202610010005", "202609201014", 2, 1, "洗衣机到货外箱破损", "100.00", 1),
    ("AS202610020006", "202609101016", 5, 2, "冰箱门体变形，申请退货", "3999.00", 1),
]

# id, name, type, amount, rate, min_amount, scope, scope_ids, total, per_limit, received, used, start, end
COUPONS = [
    (1, "新人立减券", 1, "50.00", None, "199.00", 1, None, 1000, 1, 0, 0, "2026-09-01 00:00:00", "2026-12-31 23:59:59"),
    (2, "满1000减100券", 1, "100.00", None, "1000.00", 1, None, 500, 2, 0, 0, "2026-09-01 00:00:00", "2026-12-31 23:59:59"),
    (3, "会员专享9折券", 2, "0.00", "9.00", "500.00", 1, None, 300, 1, 0, 0, "2026-09-01 00:00:00", "2026-12-31 23:59:59"),
    (4, "夏季清凉券", 1, "30.00", None, "299.00", 1, None, 200, 1, 0, 0, "2026-06-01 00:00:00", "2026-08-31 23:59:59"),
    (5, "家电品类券", 1, "200.00", None, "2000.00", 3, "5", 100, 1, 0, 0, "2026-09-01 00:00:00", "2026-12-31 23:59:59"),
]

# coupon_id, member_id, status(1未使用/2已使用/3已过期), order_no
COUPON_RECEIVE = [
    (1, 1, 1, None),
    (2, 1, 1, None),
    (2, 2, 1, None),
    (3, 2, 1, None),
    (3, 5, 1, None),
    (4, 1, 3, None),
    (5, 5, 1, None),
    (2, 5, 2, "202609181015"),
]

SECKILL = [
    ("随心耳机 A6 限时秒杀", 6, "299.00", 50, 1, "2026-09-01 00:00:00", "2026-09-30 23:59:59"),
    ("循环风扇 1 元秒杀", 13, "199.00", 100, 2, "2026-09-15 00:00:00", "2026-10-31 23:59:59"),
]

FULL_DISCOUNTS = [
    (1, "全场满200减30", 1, "200.00", "30.00", 1, None, "2026-09-01 00:00:00", "2026-12-31 23:59:59", 0),
    (2, "手机品类满3000减200", 1, "3000.00", "200.00", 2, "2", "2026-09-01 00:00:00", "2026-10-31 23:59:59", 0),
    (3, "家电满2000减150", 1, "2000.00", "150.00", 2, "5", "2026-09-10 00:00:00", "2026-12-31 23:59:59", 1),
]

GROUP_BUYS = [
    (1, "随心 X1 Pro 双人拼", 1, "4699.00", "4999.00", 2, 24, "2026-09-01 00:00:00", "2026-09-30 23:59:59"),
    (2, "随心耳机三人团购", 6, "299.00", "399.00", 3, 48, "2026-09-01 00:00:00", "2026-09-30 23:59:59"),
    (3, "扫地机器人拼团", 9, "1499.00", "1699.00", 2, 48, "2026-09-20 00:00:00", "2026-10-31 23:59:59"),
]

DISTRIBUTORS = [
    (2, 1, "10.00", 2, None),
    (3, 2, "8.00", 1, 2),
    (5, 1, "12.00", 2, None),
]

# order_no, 分销会员id, amount, status
COMMISSIONS = [
    ("202609021002", 2, "124.95", 1),
    ("202608301004", 2, "39.90", 2),
    ("202609181015", 5, "683.88", 1),
]

ARTICLE_CATEGORIES = [
    (1, "商城公告", 1),
    (2, "购物指南", 2),
    (3, "新闻资讯", 3),
]

# id, title, category_id, author, 封面文件名, summary, content, status, publish_time
ARTICLES = [
    (1, "随心商城上线公告", 1, "admin", "", "随心商城正式上线运营，海量好物等你来选。",
     "<h3>随心商城正式上线（演示数据）</h3><p>本站商品与文案均为演示占位数据，用于展示系统功能，不代表任何真实商家承诺。</p>",
     1, "2026-09-01 09:00:00"),
    (2, "会员等级权益说明", 2, "admin", "", "普通、黄金、钻石三级会员体系，消费越多权益越多。",
     "<h3>会员权益</h3><p>黄金会员享 95 折、钻石会员享 9 折并配备专属客服，生日双倍积分。</p>",
     1, "2026-09-01 10:00:00"),
    (3, "2026 中秋大促预热", 3, "editor01", "", "中秋团圆季，全场满减叠加优惠券。",
     "<h3>中秋大促</h3><p>9 月 15 日至 9 月 21 日，全场满 200 减 30，可叠加平台优惠券。</p>",
     0, None),
    (4, "选购指南：从参数到体验", 2, "admin", "phone-x1-1.svg", "处理器、屏幕、影像、续航四大维度教你选手机。",
     "<h3>如何挑选手机</h3><p>先定预算再看处理器与屏幕，影像看传感器尺寸，续航看电池与快充组合。</p>",
     1, "2026-09-12 15:00:00"),
    (5, "家电以旧换新补贴上线", 3, "admin", "washer-1.svg", "冰箱、洗衣机、空调参与以旧换新，最高补贴 500 元。",
     "<h3>以旧换新</h3><p>线上下单预约回收，旧机估价直抵新机款，最高补贴 500 元。</p>",
     1, "2026-09-25 11:00:00"),
]

AD_POSITIONS = [
    (1, "首页轮播图", "750x300", 1),
    (2, "首页中部横幅", "750x200", 1),
    (3, "分类页 Banner", "750x240", 1),
    (4, "首页右侧小图", "300x200", 1),
]

# id, position_id, type, 图片文件名, video, link, text, sort, start, end
ADS = [
    (1, 1, 1, "phone-x1-1.svg", None, "/pages/goods/list?cid=2", "随心新品上市", 1, "2026-09-01 00:00:00", "2026-09-30 23:59:59"),
    (2, 2, 1, "fridge-450.svg", None, "/pages/goods/detail?id=5", "鲜语冰箱狂欢周", 2, "2026-09-01 00:00:00", "2026-09-30 23:59:59"),
    (3, 3, 3, None, None, "/pages/activity/full-discount", "中秋满减会场", 1, "2026-09-10 00:00:00", "2026-09-25 23:59:59"),
    (4, 1, 1, "tv-s-1.svg", None, "/pages/goods/detail?id=19", "随心电视 S Pro 65 首发", 3, "2026-09-05 00:00:00", "2026-10-31 23:59:59"),
    (5, 4, 1, "robot-1.svg", None, "/pages/goods/detail?id=9", "扫地机器人直降 300", 1, "2026-09-20 00:00:00", "2026-10-31 23:59:59"),
]

# id, title, content, target, target_level_id, status, publish_time
NOTICES = [
    (1, "2026 年中秋国庆假期物流时效通知", "中秋国庆假期期间，部分偏远地区快递时效可能延长 1-2 天，请合理安排收货时间。",
     0, None, 1, "2026-09-02 14:00:00"),
    (2, "会员积分规则调整公告", "自 2026 年 10 月 1 日起，积分有效期调整为自获取之日起 24 个月。",
     0, None, 0, None),
    (3, "国庆大促：家电满 2000 减 150", "10 月 1 日至 10 月 7 日，大家电品类单笔满 2000 元立减 150 元，可叠加品类券。",
     1, None, 1, "2026-09-28 09:00:00"),
]

FREIGHT_TEMPLATES = [
    (1, "全国包邮模板", 1, 1, "[]"),
    (2, "按重量计费模板", 2, 0, '[{"region":"全国","first":1,"firstFee":"5.00","add":1,"addFee":"2.00"}]'),
]

# admin_id, module, action_type, target, summary, created_at（逐条按 summary 幂等）
ADMIN_LOGS = [
    (1, "goods", 3, "goods:1", "编辑商品「随心 X1 Pro」", "2026-09-03 10:30:00"),
    (1, "order", 3, "order:7", "订单发货：速达速运 EX1234567890", "2026-09-03 09:20:00"),
    (1, "member", 3, "member:2", "编辑会员「李小红」资料", "2026-09-02 16:45:00"),
    (1, "marketing", 2, "coupon:2", "新增优惠券「满1000减100券」", "2026-09-02 11:00:00"),
    (1, "content", 2, "article:2", "发布文章「会员等级权益说明」", "2026-09-01 15:30:00"),
    (1, "settings", 3, "settings/basic", "修改基本设置（商城名称、版权）", "2026-09-01 10:10:00"),
    (1, "permission", 3, "role:2", "修改角色「运营专员」权限分配", "2026-09-01 09:00:00"),
    (1, "goods", 2, "goods:19", "新增商品「随心电视 S Pro 65」", "2026-09-05 14:20:00"),
    (1, "order", 4, "order:15", "批量发货 2 单", "2026-09-28 18:10:00"),
    (1, "order", 7, "after_sale:2", "售后审核通过：AS202609050002", "2026-09-29 09:30:00"),
    (1, "member", 3, "member:6", "禁用会员「杨晓梅」", "2026-10-01 11:05:00"),
    (1, "marketing", 2, "coupon:5", "新增优惠券「家电品类券」", "2026-09-26 16:00:00"),
    (1, "content", 2, "notice:3", "发布公告「国庆大促」", "2026-09-28 09:05:00"),
    (1, "goods", 4, "goods:20", "下架商品「测试商品」", "2026-09-30 17:40:00"),
]

# member_id, receiver, phone, province, city, district, detail, tag, is_default
ADDRESSES = [
    (1, "张小明", "10000000001", "示例市", "示例市", "示例区", "示例街道1号", "公司", 1),
    (2, "李小红", "10000000002", "示例市", "示例市", "示例区", "示例路88号", "家", 1),
    (2, "李小红", "10000000002", "示例市", "示例市", "示例区", "示例路200号", "公司", 0),
    (3, "王大力", "10000000003", "示例省", "示例市", "示例区", "示例路6号", "家", 1),
    (4, "刘晓芳", "10000000004", "示例省", "示例市", "示例区", "示例园3号", "公司", 1),
    (4, "刘晓芳", "10000000004", "示例省", "示例市", "示例区", "示例街道9号", "家", 0),
    (5, "陈大鹏", "10000000005", "示例市", "示例市", "示例区", "示例大街12号", "家", 1),
    (6, "杨晓梅", "10000000006", "示例省", "示例市", "示例区", "示例路8号", "家", 1),
]

# goods_id, member_id, order_no, score, content, status, reply, 图片文件名(可空)
COMMENTS = [
    (1, 1, "202609031001", 5, "机身轻薄，屏幕显示效果很好，拍照清晰。", 1, None, "phone-x1-1.svg"),
    (1, 3, "202608251005", 5, "给家人买的，做工扎实，运行流畅。", 1, None, None),
    (6, 2, "202608301004", 4, "降噪效果不错，续航够用，性价比高。", 1, None, None),
    (5, 2, "202608151007", 4, "冰箱容量大，静音效果好，物流很快。", 1, None, None),
    (7, 1, "202610011008", 5, "平板屏幕细腻，追剧很爽，键盘也好用。", 1, None, "pad-p5.svg"),
    (8, 4, "202610021011", 4, "手表续航一周，通话清晰，就是表带偏硬。", 1, "感谢反馈，表带已升级软胶材质，可联系客服更换。", None),
    (9, 4, "202609291013", 5, "扫得干净，自动集尘很省心。", 1, None, "robot-1.svg"),
    (10, 4, "202610021009", 3, "人脸识别挺快，安装师傅很专业。", 1, None, None),
    (12, 2, "202609201014", 4, "洗烘一体很方便，噪音可接受。", 1, None, None),
    (14, 2, "202610011010", 5, "音质超出预期，智能家居控制很好用。", 1, None, None),
    (16, 5, "202609181015", 5, "影像旗舰名副其实，夜景提升明显。", 1, None, "phone-x1-2.svg"),
    (17, 5, "202609101016", 4, "容量够大，分区合理，制冷快。", 1, None, None),
    (19, 1, "202609281012", 5, "Mini LED 画质很棒，高刷玩游戏舒服。", 0, None, None),
    (13, 3, "202609051017", 3, "风力还行，就是遥控有点小。", 0, None, None),
    (20, 5, "202609101016", 5, "降噪强，空间音频惊喜。", 1, "感谢您的好评，祝您使用愉快！", None),
    (15, 6, "202609011018", 4, "千元机里性价比很高，续航久。", 1, None, None),
]

# member_id, goods_id, sku_id, quantity, selected（演示购物车）
CARTS = [
    (1, 7, 8, 1, 1),
    (1, 13, 14, 2, 1),
    (1, 20, 21, 1, 0),
    (2, 12, 13, 1, 1),
    (2, 19, 20, 1, 1),
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sync_images() -> str:
    """同步 front/images 演示图到 uploads/seed/，返回图片访问前缀。

    图片源随代码入库（front/images），uploads 属运行期产物（已 gitignore），
    每次 seed 自动同步，保证后台(8001)与前台(8000)都能显示真实图片。
    """
    from core.config import config

    src = _project_root() / "front" / "images"
    dst_root = Path(config.upload_dir)
    if not dst_root.is_absolute():
        dst_root = _project_root() / dst_root
    dst = dst_root / "seed"
    copied = 0
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted(src.iterdir()):
            # logo 属站点标识而非商品图，不参与演示图同步
            if not f.is_file() or f.name.lower() == "logo.png":
                continue
            if f.suffix.lower() in {".svg", ".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                target = dst / f.name
                if not target.exists() or target.stat().st_mtime < f.stat().st_mtime:
                    shutil.copy2(f, target)
                    copied += 1
    import os

    base = config.upload_public_base or f"http://127.0.0.1:{os.getenv('PORT', '8001')}"
    prefix = f"{base}/uploads/seed"
    print(f"演示图片同步：{copied} 张新增/更新 -> {prefix}")
    return prefix


def _img(prefix: str, name: str):
    return f"{prefix}/{name}" if name else None


async def _has(fetch, sql, params=None) -> bool:
    rows = await fetch(sql, params or ())
    return bool(rows and list(rows[0].values())[0])


async def seed(exec, fetch):
    prefix = _sync_images()

    # 分类 / 品牌 / 规格 / 属性：按 id 幂等补齐
    for cid, parent_id, name in CATEGORIES:
        await exec(
            "INSERT INTO goods_category (id, parent_id, name, sort, is_show) VALUES (%s,%s,%s,%s,1) "
            "ON DUPLICATE KEY UPDATE name=VALUES(name), parent_id=VALUES(parent_id), is_show=1",
            (cid, parent_id, name, cid),
        )
    for bid, name, desc in BRANDS:
        await exec(
            "INSERT IGNORE INTO brands (id, name, description, sort, status) VALUES (%s,%s,%s,%s,1)",
            (bid, name, desc, bid),
        )
    for sid, name, category_id in SPECS:
        await exec(
            "INSERT IGNORE INTO specifications (id, name, category_id, sort) VALUES (%s,%s,%s,%s)",
            (sid, name, category_id, sid),
        )
    for vid, spec_id, value in SPEC_VALUES:
        await exec(
            "INSERT IGNORE INTO specification_values (id, spec_id, value) VALUES (%s,%s,%s)",
            (vid, spec_id, value),
        )
    for aid, name, category_id in ATTRS:
        await exec(
            "INSERT IGNORE INTO attributes (id, name, category_id, sort) VALUES (%s,%s,%s,%s)",
            (aid, name, category_id, aid),
        )
    for avid, attr_id, value in ATTR_VALUES:
        await exec(
            "INSERT IGNORE INTO attribute_values (id, attr_id, value) VALUES (%s,%s,%s)",
            (avid, attr_id, value),
        )

    # 商品 / 图片 / SKU：按 id 幂等
    main_image = {}
    for gid, _image_id, file_name, sort, _img_type in GOODS_IMAGES:
        main_image.setdefault(gid, file_name)
    for g in GOODS:
        gid, name, subtitle, category_id, brand_id, spu_code, unit, market, price, cost, stock, warn, status, sales, rec, hot, new = g
        cover = _img(prefix, main_image.get(gid))
        detail_html = (
            f"<h2>{name}</h2><p>{subtitle}。本页为演示商品，服务与保障说明仅作示例文本，不代表真实商家承诺。</p>"
            + (f"<p><img src=\"{cover}\" style=\"max-width:100%;border-radius:8px;\" alt=\"{name}\"></p>" if cover else "")
            + "<h3>产品亮点（演示文案）</h3><ul><li>商品描述与实物一致</li><li>可在「申请售后」提交退换申请</li><li>运费按商品绑定的运费模板计算</li></ul>"
        )
        await exec(
            "INSERT INTO goods (id, name, subtitle, category_id, brand_id, spu_code, unit, market_price, price, "
            "cost_price, stock, warn_stock, status, sales, is_recommend, is_hot, is_new, detail_html, created_by) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0) "
            "ON DUPLICATE KEY UPDATE name=VALUES(name), subtitle=VALUES(subtitle), category_id=VALUES(category_id), "
            "brand_id=VALUES(brand_id), spu_code=VALUES(spu_code), unit=VALUES(unit), market_price=VALUES(market_price), "
            "price=VALUES(price), cost_price=VALUES(cost_price), stock=VALUES(stock), warn_stock=VALUES(warn_stock), "
            "status=VALUES(status), sales=VALUES(sales), is_recommend=VALUES(is_recommend), is_hot=VALUES(is_hot), "
            "is_new=VALUES(is_new), detail_html=VALUES(detail_html)",
            (
                gid, name, subtitle, category_id, brand_id, spu_code, unit, market, price, cost, stock, warn, status,
                sales, rec, hot, new, detail_html,
            ),
        )
        # 旧库补齐：仅当仍是 seed 生成的原文且无图时，补上带主图的详情
        await exec(
            "UPDATE goods SET detail_html=%s WHERE id=%s AND detail_html NOT LIKE '%%<img%%' "
            "AND (detail_html LIKE '%%品质保障，全国联保，支持七天无理由退货。%%' "
            "OR detail_html LIKE '%%服务与保障说明仅作示例文本%%')",
            (detail_html, gid),
        )
    for gid, image_id, file_name, sort, img_type in GOODS_IMAGES:
        await exec(
            "INSERT INTO goods_images (id, goods_id, url, sort, type) VALUES (%s,%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE url=VALUES(url), sort=VALUES(sort), type=VALUES(type)",
            (image_id, gid, _img(prefix, file_name), sort, img_type),
        )
    for sku_id, goods_id, sku_code, price, stock, file_name in SKUS:
        await exec(
            "INSERT INTO goods_sku (id, goods_id, sku_code, price, stock, image, status) "
            "VALUES (%s,%s,%s,%s,%s,%s,1) "
            "ON DUPLICATE KEY UPDATE goods_id=VALUES(goods_id), sku_code=VALUES(sku_code), price=VALUES(price), "
            "stock=VALUES(stock), image=VALUES(image), status=VALUES(status)",
            (sku_id, goods_id, sku_code, price, stock, _img(prefix, file_name)),
        )
    for sku_id, spec_id, spec_value_id in SKU_SPEC_VALUES:
        await exec(
            "INSERT IGNORE INTO goods_sku_spec_values (sku_id, spec_id, spec_value_id) VALUES (%s,%s,%s)",
            (sku_id, spec_id, spec_value_id),
        )

    # 会员：按 id/手机号幂等，等级按名称解析
    import bcrypt

    level_rows = await fetch("SELECT id, level_name FROM member_level")
    level_ids = {r["level_name"]: r["id"] for r in level_rows}
    pwd_hash = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode("utf-8")
    for mid, nickname, phone, points, consume, level_name, mstatus in MEMBERS:
        await exec(
            "INSERT IGNORE INTO members (id, nickname, phone, password_hash, level_id, points, total_consume, status, "
            "registered_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'2026-01-01 00:00:00')",
            (mid, nickname, phone, pwd_hash, level_ids.get(level_name), points, consume, mstatus),
        )
        if level_ids.get(level_name):
            await exec("UPDATE members SET level_id=%s WHERE id=%s AND level_id IS NULL", (level_ids[level_name], mid))

    # 积分流水：按 会员+事由+变动值 哨兵
    for mid, change, reason, log_type in POINTS_LOGS:
        if not await _has(fetch, "SELECT COUNT(*) AS c FROM points_logs WHERE member_id=%s AND reason=%s AND change_value=%s", (mid, reason, change)):
            await exec(
                "INSERT INTO points_logs (member_id, change_value, reason, type) VALUES (%s,%s,%s,%s)",
                (mid, change, reason, log_type),
            )
    # 会员操作日志：按 会员+动作类型+内容 哨兵
    for mid, action_type, action in MEMBER_LOGS:
        if not await _has(fetch, "SELECT COUNT(*) AS c FROM member_logs WHERE member_id=%s AND action_type=%s AND action=%s", (mid, action_type, action)):
            await exec(
                "INSERT INTO member_logs (member_id, action_type, action, ip) VALUES (%s,%s,%s,'127.0.0.1')",
                (mid, action_type, action),
            )

    # 订单：按 order_no 幂等
    for row in ORDERS:
        (
            order_no, member_id, total, freight, coupon, points_amt, pay_amt, pay_type, pay_status, order_status,
            receiver, phone, address, logistics_company, logistics_no, buyer_msg, source, paid_at, shipped_at,
            completed_at, created_at,
        ) = row
        await exec(
            "INSERT IGNORE INTO orders (order_no, member_id, total_amount, freight_amount, coupon_amount, points_amount, "
            "pay_amount, pay_type, pay_status, order_status, receiver_name, receiver_phone, receiver_address, "
            "logistics_company, logistics_no, buyer_message, order_source, paid_at, shipped_at, completed_at, "
            "created_at, created_by) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,IFNULL(%s, NOW()),0)",
            (
                order_no, member_id, total, freight, coupon, points_amt, pay_amt, pay_type, pay_status, order_status,
                receiver, phone, address, logistics_company, logistics_no, buyer_msg, source, paid_at, shipped_at,
                completed_at, created_at,
            ),
        )
    order_ids = {}
    for r in await fetch("SELECT id, order_no FROM orders"):
        order_ids[r["order_no"]] = r["id"]

    for row in ORDER_ITEMS:
        order_no, goods_id, sku_id, goods_name, price, quantity, subtotal = row
        oid = order_ids.get(order_no)
        if not oid:
            continue
        if not await _has(fetch, "SELECT COUNT(*) AS c FROM order_items WHERE order_id=%s AND sku_id=%s", (oid, sku_id)):
            await exec(
                "INSERT INTO order_items (order_id, goods_id, sku_id, goods_name, price, quantity, subtotal) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (oid, goods_id, sku_id, goods_name, price, quantity, subtotal),
            )
    for row in ORDER_LOGS:
        order_no, operator_type, action, content = row
        oid = order_ids.get(order_no)
        if not oid:
            continue
        if not await _has(fetch, "SELECT COUNT(*) AS c FROM order_logs WHERE order_id=%s AND action=%s AND content=%s", (oid, action, content)):
            await exec(
                "INSERT INTO order_logs (order_id, operator_type, action, content) VALUES (%s,%s,%s,%s)",
                (oid, operator_type, action, content),
            )

    # 售后：按 after_sale_no 幂等
    for no, order_no, member_id, atype, reason, amount, astatus in AFTER_SALES:
        oid = order_ids.get(order_no)
        if not oid:
            continue
        await exec(
            "INSERT IGNORE INTO after_sales (after_sale_no, order_id, member_id, type, reason, amount, status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (no, oid, member_id, atype, reason, amount, astatus),
        )

    for row in COUPONS:
        cid, name, ctype, amount, rate, min_amount, scope, scope_ids, total, per_limit, received, used, start_time, end_time = row
        await exec(
            "INSERT IGNORE INTO coupons (id, name, type, amount, rate, min_amount, scope, scope_ids, total_count, per_limit, "
            "received_count, used_count, start_time, end_time, status, created_by) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,0)",
            (cid, name, ctype, amount, rate, min_amount, scope, scope_ids, total, per_limit, received, used, start_time, end_time),
        )
    for coupon_id, member_id, cstatus, order_no in COUPON_RECEIVE:
        oid = order_ids.get(order_no) if order_no else None
        if not await _has(fetch, "SELECT COUNT(*) AS c FROM coupon_receive WHERE coupon_id=%s AND member_id=%s", (coupon_id, member_id)):
            await exec(
                "INSERT INTO coupon_receive (coupon_id, member_id, status, order_id) VALUES (%s,%s,%s,%s)",
                (coupon_id, member_id, cstatus, oid),
            )

    for row in SECKILL:
        name, goods_id, price, stock, per_limit, start_time, end_time = row
        if not await _has(fetch, "SELECT COUNT(*) AS c FROM seckill_activities WHERE name=%s", (name,)):
            await exec(
                "INSERT INTO seckill_activities (name, goods_id, seckill_price, seckill_stock, per_limit, start_time, "
                "end_time, status, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,1,0)",
                (name, goods_id, price, stock, per_limit, start_time, end_time),
            )
    for row in FULL_DISCOUNTS:
        fid, name, ftype, threshold, value, scope, scope_ids, start_time, end_time, stackable = row
        await exec(
            "INSERT IGNORE INTO full_discount_activities (id, name, type, threshold, discount_value, scope, scope_ids, "
            "start_time, end_time, is_stackable, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)",
            (fid, name, ftype, threshold, value, scope, scope_ids, start_time, end_time, stackable),
        )
    for row in GROUP_BUYS:
        gid, name, goods_id, leader_price, member_price, group_size, valid_hours, start_time, end_time = row
        await exec(
            "INSERT IGNORE INTO group_buy_activities (id, name, goods_id, leader_price, member_price, group_size, "
            "valid_hours, start_time, end_time, status, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1,0)",
            (gid, name, goods_id, leader_price, member_price, group_size, valid_hours, start_time, end_time),
        )

    dist_ids = {}
    for member_id, level, rate, dstatus, invited_by in DISTRIBUTORS:
        if not await _has(fetch, "SELECT COUNT(*) AS c FROM distributor WHERE member_id=%s", (member_id,)):
            await exec(
                "INSERT INTO distributor (member_id, level, commission_rate, status, invited_by, created_by) "
                "VALUES (%s,%s,%s,%s,%s,0)",
                (member_id, level, rate, dstatus, invited_by),
            )
        drow = await fetch("SELECT id FROM distributor WHERE member_id=%s", (member_id,))
        if drow:
            dist_ids[member_id] = drow[0]["id"]
    for order_no, distributor_member, amount, cstatus in COMMISSIONS:
        did = dist_ids.get(distributor_member)
        oid = order_ids.get(order_no)
        if not did or not oid:
            continue
        if not await _has(fetch, "SELECT COUNT(*) AS c FROM commission_logs WHERE distributor_id=%s AND order_id=%s", (did, oid)):
            await exec(
                "INSERT INTO commission_logs (distributor_id, order_id, amount, status) VALUES (%s,%s,%s,%s)",
                (did, oid, amount, cstatus),
            )

    for cid, name, sort in ARTICLE_CATEGORIES:
        await exec(
            "INSERT IGNORE INTO article_categories (id, name, sort, status) VALUES (%s,%s,%s,1)",
            (cid, name, sort),
        )
    for aid, title, category_id, author, cover, summary, content, status, publish_time in ARTICLES:
        await exec(
            "INSERT IGNORE INTO articles (id, title, category_id, author, cover, summary, content, seo_title, seo_keywords, "
            "seo_desc, status, publish_time, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)",
            (aid, title, category_id, author, _img(prefix, cover), summary, content, title, "", "", status, publish_time),
        )

    for pid, name, size, status in AD_POSITIONS:
        await exec(
            "INSERT IGNORE INTO ad_positions (id, name, size, status) VALUES (%s,%s,%s,%s)",
            (pid, name, size, status),
        )
    for aid2, position_id, atype, image, video, link, text, sort, start_time, end_time in ADS:
        await exec(
            "INSERT INTO ads (id, position_id, type, image, video, link, text, sort, start_time, end_time, status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1) "
            "ON DUPLICATE KEY UPDATE position_id=VALUES(position_id), type=VALUES(type), image=VALUES(image), "
            "video=VALUES(video), link=VALUES(link), text=VALUES(text), sort=VALUES(sort), start_time=VALUES(start_time), "
            "end_time=VALUES(end_time), status=VALUES(status)",
            (aid2, position_id, atype, _img(prefix, image), video, link, text, sort, start_time, end_time),
        )
    for nid, title, content, target, target_level_id, status, publish_time in NOTICES:
        await exec(
            "INSERT IGNORE INTO notices (id, title, content, target, target_level_id, publish_time, status, created_by) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,0)",
            (nid, title, content, target, target_level_id, publish_time, status),
        )
    for tid, name, ftype, free, regions in FREIGHT_TEMPLATES:
        await exec(
            "INSERT IGNORE INTO freight_templates (id, name, type, is_free_shipping, regions_json, created_by) "
            "VALUES (%s,%s,%s,%s,%s,0)",
            (tid, name, ftype, free, regions),
        )

    # 操作日志：逐条按 demo:<summary> 幂等
    for admin_id, module, action_type, target, summary, created_at in ADMIN_LOGS:
        if not await _has(fetch, "SELECT COUNT(*) AS c FROM admin_logs WHERE params_summary=%s", (f"demo:{summary}",)):
            await exec(
                "INSERT INTO admin_logs (admin_id, module, action_type, target, ip, params_summary, created_at) "
                "VALUES (%s,%s,%s,%s,'127.0.0.1',%s,%s)",
                (admin_id, module, action_type, target, f"demo:{summary}", created_at),
            )

    # 收货地址：按 会员+详址 哨兵
    for mid, name, phone, province, city, district, detail, tag, is_default in ADDRESSES:
        if not await _has(fetch, "SELECT COUNT(*) AS c FROM member_address WHERE member_id=%s AND detail=%s", (mid, detail)):
            await exec(
                "INSERT INTO member_address (member_id,receiver_name,receiver_phone,province,city,district,detail,tag,"
                "is_default) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (mid, name, phone, province, city, district, detail, tag, is_default),
            )

    # 购物车：唯一键 (member_id, sku_id) 幂等
    for mid, goods_id, sku_id, quantity, selected in CARTS:
        await exec(
            "INSERT IGNORE INTO member_cart (member_id, goods_id, sku_id, quantity, selected) VALUES (%s,%s,%s,%s,%s)",
            (mid, goods_id, sku_id, quantity, selected),
        )

    # 评价：按 商品+会员+订单 哨兵
    for goods_id, member_id, order_no, score, content, status, reply, image_file in COMMENTS:
        oid = order_ids.get(order_no)
        if not oid:
            continue
        if not await _has(
            fetch,
            "SELECT COUNT(*) AS c FROM goods_comments WHERE goods_id=%s AND member_id=%s AND order_id=%s",
            (goods_id, member_id, oid),
        ):
            await exec(
                "INSERT INTO goods_comments (goods_id,member_id,order_id,score,content,images,status,reply) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (goods_id, member_id, oid, score, content, _img(prefix, image_file), status, reply),
            )
