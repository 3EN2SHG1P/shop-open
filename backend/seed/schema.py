ENGINE = "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS admin_users (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      username VARCHAR(50) NOT NULL UNIQUE,
      password_hash VARCHAR(255) NOT NULL,
      real_name VARCHAR(50) DEFAULT NULL,
      phone VARCHAR(20) DEFAULT NULL,
      email VARCHAR(100) DEFAULT NULL,
      dept_id BIGINT UNSIGNED DEFAULT NULL,
      status TINYINT NOT NULL DEFAULT 1,
      last_login_ip VARCHAR(45) DEFAULT NULL,
      last_login_time DATETIME DEFAULT NULL,
      login_fail_count INT NOT NULL DEFAULT 0,
      locked_until DATETIME DEFAULT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS dept (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      parent_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
      dept_name VARCHAR(50) NOT NULL,
      sort INT NOT NULL DEFAULT 0,
      status TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS roles (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      role_name VARCHAR(50) NOT NULL,
      role_key VARCHAR(50) NOT NULL UNIQUE,
      description VARCHAR(255) DEFAULT NULL,
      data_scope TINYINT NOT NULL DEFAULT 3,
      status TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS permissions (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      parent_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
      permission_type VARCHAR(10) NOT NULL,
      name VARCHAR(50) NOT NULL,
      code VARCHAR(100) DEFAULT NULL,
      UNIQUE KEY uk_permission_code (code),
      path VARCHAR(200) DEFAULT NULL,
      method VARCHAR(10) DEFAULT NULL,
      icon VARCHAR(100) DEFAULT NULL,
      sort INT NOT NULL DEFAULT 0,
      status TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS user_roles (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      user_id BIGINT UNSIGNED NOT NULL,
      role_id BIGINT UNSIGNED NOT NULL,
      UNIQUE KEY uk_user_role (user_id, role_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS role_permissions (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      role_id BIGINT UNSIGNED NOT NULL,
      permission_id BIGINT UNSIGNED NOT NULL,
      UNIQUE KEY uk_role_perm (role_id, permission_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS admin_login_logs (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      admin_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
      username VARCHAR(50) DEFAULT NULL,
      ip VARCHAR(45) DEFAULT NULL,
      user_agent VARCHAR(255) DEFAULT NULL,
      success TINYINT NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_admin_login_logs_time (created_at)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS admin_logs (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      admin_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
      module VARCHAR(50) NOT NULL DEFAULT '',
      action_type TINYINT NOT NULL DEFAULT 0,
      target VARCHAR(200) DEFAULT NULL,
      ip VARCHAR(45) DEFAULT NULL,
      params_summary VARCHAR(500) DEFAULT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_admin_logs_admin (admin_id),
      KEY idx_admin_logs_time (created_at),
      KEY idx_admin_logs_module (module)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS goods_category (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      parent_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
      name VARCHAR(50) NOT NULL,
      icon VARCHAR(200) DEFAULT NULL,
      sort INT NOT NULL DEFAULT 0,
      is_show TINYINT NOT NULL DEFAULT 1,
      seo_title VARCHAR(200) DEFAULT NULL,
      seo_keywords VARCHAR(200) DEFAULT NULL,
      seo_desc VARCHAR(500) DEFAULT NULL,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_category_parent (parent_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS brands (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(100) NOT NULL,
      logo VARCHAR(200) DEFAULT NULL,
      description VARCHAR(500) DEFAULT NULL,
      sort INT NOT NULL DEFAULT 0,
      status TINYINT NOT NULL DEFAULT 1,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS specifications (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(50) NOT NULL,
      category_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
      sort INT NOT NULL DEFAULT 0,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS specification_values (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      spec_id BIGINT UNSIGNED NOT NULL,
      value VARCHAR(50) NOT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_spec_values_spec (spec_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS attributes (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(50) NOT NULL,
      category_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
      sort INT NOT NULL DEFAULT 0,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS attribute_values (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      attr_id BIGINT UNSIGNED NOT NULL,
      value VARCHAR(50) NOT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_attr_values_attr (attr_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS goods (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(200) NOT NULL,
      subtitle VARCHAR(300) DEFAULT NULL,
      category_id BIGINT UNSIGNED DEFAULT NULL,
      brand_id BIGINT UNSIGNED DEFAULT NULL,
      spu_code VARCHAR(50) DEFAULT NULL,
      unit VARCHAR(20) DEFAULT '件',
      market_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      cost_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      stock INT NOT NULL DEFAULT 0,
      warn_stock INT NOT NULL DEFAULT 0,
      status TINYINT NOT NULL DEFAULT 1,
      sales INT NOT NULL DEFAULT 0,
      is_recommend TINYINT NOT NULL DEFAULT 0,
      is_hot TINYINT NOT NULL DEFAULT 0,
      is_new TINYINT NOT NULL DEFAULT 0,
      detail_html MEDIUMTEXT,
      freight_template_id BIGINT UNSIGNED DEFAULT NULL,
      seo_title VARCHAR(200) DEFAULT NULL,
      seo_keywords VARCHAR(300) DEFAULT NULL,
      seo_desc VARCHAR(500) DEFAULT NULL,
      is_presale TINYINT NOT NULL DEFAULT 0,
      presale_start DATETIME DEFAULT NULL,
      presale_end DATETIME DEFAULT NULL,
      buy_limit INT NOT NULL DEFAULT 0,
      points_discount_ratio DECIMAL(5,2) NOT NULL DEFAULT 0.00,
      on_sale_time DATETIME DEFAULT NULL,
      audit_status TINYINT NOT NULL DEFAULT 0,
      audit_note VARCHAR(500) DEFAULT NULL,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_goods_category (category_id),
      KEY idx_goods_brand (brand_id),
      KEY idx_goods_status (status),
      KEY idx_goods_created (created_at),
      KEY idx_goods_price (price)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS goods_sku (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      goods_id BIGINT UNSIGNED NOT NULL,
      sku_code VARCHAR(100) NOT NULL,
      price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      stock INT NOT NULL DEFAULT 0,
      image VARCHAR(200) DEFAULT NULL,
      status TINYINT NOT NULL DEFAULT 1,
      version INT NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_goods_sku_code (goods_id, sku_code),
      KEY idx_sku_goods (goods_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS goods_sku_spec_values (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      sku_id BIGINT UNSIGNED NOT NULL,
      spec_id BIGINT UNSIGNED NOT NULL,
      spec_value_id BIGINT UNSIGNED NOT NULL,
      UNIQUE KEY uk_sku_spec (sku_id, spec_value_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS goods_images (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      goods_id BIGINT UNSIGNED NOT NULL,
      url VARCHAR(300) NOT NULL,
      sort INT NOT NULL DEFAULT 0,
      type TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_goods_images_goods (goods_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS goods_comments (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      goods_id BIGINT UNSIGNED NOT NULL,
      member_id BIGINT UNSIGNED NOT NULL,
      order_id BIGINT UNSIGNED DEFAULT NULL,
      score TINYINT NOT NULL DEFAULT 5,
      content VARCHAR(1000) DEFAULT NULL,
      images TEXT,
      status TINYINT NOT NULL DEFAULT 1,
      reply VARCHAR(500) DEFAULT NULL,
      reply_time DATETIME DEFAULT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_comments_goods (goods_id),
      KEY idx_comments_status (status)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS orders (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      order_no VARCHAR(32) NOT NULL UNIQUE,
      member_id BIGINT UNSIGNED NOT NULL,
      total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      freight_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      coupon_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      points_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      pay_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      pay_type TINYINT DEFAULT NULL,
      pay_status TINYINT NOT NULL DEFAULT 0,
      order_status TINYINT NOT NULL DEFAULT 1,
      receiver_name VARCHAR(50) NOT NULL,
      receiver_phone VARCHAR(20) NOT NULL,
      receiver_address VARCHAR(300) NOT NULL,
      logistics_company VARCHAR(50) DEFAULT NULL,
      logistics_no VARCHAR(100) DEFAULT NULL,
      buyer_message VARCHAR(300) DEFAULT NULL,
      order_source VARCHAR(20) DEFAULT 'h5',
      remark VARCHAR(300) DEFAULT NULL,
      paid_at DATETIME DEFAULT NULL,
      shipped_at DATETIME DEFAULT NULL,
      completed_at DATETIME DEFAULT NULL,
      canceled_at DATETIME DEFAULT NULL,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_orders_member (member_id),
      KEY idx_orders_status (order_status),
      KEY idx_orders_pay_status (pay_status),
      KEY idx_orders_created (created_at)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS order_items (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      order_id BIGINT UNSIGNED NOT NULL,
      goods_id BIGINT UNSIGNED NOT NULL,
      sku_id BIGINT UNSIGNED DEFAULT NULL,
      goods_name VARCHAR(200) NOT NULL,
      goods_image VARCHAR(300) DEFAULT NULL,
      spec_value VARCHAR(500) DEFAULT NULL,
      price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      quantity INT NOT NULL DEFAULT 1,
      subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_items_order (order_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS order_logs (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      order_id BIGINT UNSIGNED NOT NULL,
      operator_type TINYINT NOT NULL DEFAULT 1,
      operator_id BIGINT UNSIGNED DEFAULT NULL,
      operator_name VARCHAR(50) DEFAULT NULL,
      action VARCHAR(50) NOT NULL,
      content VARCHAR(500) DEFAULT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_order_logs_order (order_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS after_sales (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      after_sale_no VARCHAR(32) NOT NULL UNIQUE,
      order_id BIGINT UNSIGNED NOT NULL,
      member_id BIGINT UNSIGNED NOT NULL,
      type TINYINT NOT NULL DEFAULT 1,
      reason VARCHAR(500) DEFAULT NULL,
      amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      status TINYINT NOT NULL DEFAULT 1,
      handle_note VARCHAR(500) DEFAULT NULL,
      return_logistics_company VARCHAR(50) DEFAULT NULL,
      return_logistics_no VARCHAR(100) DEFAULT NULL,
      handle_time DATETIME DEFAULT NULL,
      handle_by BIGINT UNSIGNED DEFAULT NULL,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_after_sales_order (order_id),
      KEY idx_after_sales_status (status)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS express_companies (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(50) NOT NULL,
      code VARCHAR(30) NOT NULL UNIQUE,
      status TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS members (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      nickname VARCHAR(50) NOT NULL,
      avatar VARCHAR(300) DEFAULT NULL,
      phone VARCHAR(20) DEFAULT NULL,
      email VARCHAR(100) DEFAULT NULL,
      password_hash VARCHAR(255) NOT NULL,
      level_id BIGINT UNSIGNED DEFAULT NULL,
      points INT NOT NULL DEFAULT 0,
      total_consume DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      status TINYINT NOT NULL DEFAULT 1,
      registered_at DATETIME DEFAULT NULL,
      last_login_time DATETIME DEFAULT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_member_phone (phone),
      KEY idx_members_level (level_id),
      KEY idx_members_created (created_at)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS member_level (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      level_name VARCHAR(50) NOT NULL,
      upgrade_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      upgrade_points INT NOT NULL DEFAULT 0,
      discount_rate DECIMAL(5,2) NOT NULL DEFAULT 10.00,
      benefits VARCHAR(500) DEFAULT NULL,
      status TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS points_logs (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      member_id BIGINT UNSIGNED NOT NULL,
      change_value INT NOT NULL,
      reason VARCHAR(300) NOT NULL,
      type TINYINT NOT NULL DEFAULT 3,
      related_id BIGINT UNSIGNED DEFAULT NULL,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_points_member (member_id),
      KEY idx_points_created (created_at)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS member_logs (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      member_id BIGINT UNSIGNED NOT NULL,
      action_type VARCHAR(30) NOT NULL,
      action VARCHAR(500) DEFAULT NULL,
      ip VARCHAR(45) DEFAULT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_member_logs_member (member_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS coupons (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(100) NOT NULL,
      type TINYINT NOT NULL DEFAULT 1,
      amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      rate DECIMAL(5,2) DEFAULT NULL,
      min_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      scope TINYINT NOT NULL DEFAULT 1,
      scope_ids VARCHAR(500) DEFAULT NULL,
      total_count INT NOT NULL DEFAULT 0,
      per_limit INT NOT NULL DEFAULT 1,
      received_count INT NOT NULL DEFAULT 0,
      used_count INT NOT NULL DEFAULT 0,
      start_time DATETIME NOT NULL,
      end_time DATETIME NOT NULL,
      status TINYINT NOT NULL DEFAULT 1,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_coupons_status (status)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS coupon_receive (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      coupon_id BIGINT UNSIGNED NOT NULL,
      member_id BIGINT UNSIGNED NOT NULL,
      status TINYINT NOT NULL DEFAULT 1,
      order_id BIGINT UNSIGNED DEFAULT NULL,
      received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      used_at DATETIME DEFAULT NULL,
      UNIQUE KEY uk_coupon_receive (coupon_id, member_id),
      KEY idx_coupon_receive_member (member_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS seckill_activities (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(100) NOT NULL,
      goods_id BIGINT UNSIGNED NOT NULL,
      sku_id BIGINT UNSIGNED DEFAULT NULL,
      seckill_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      seckill_stock INT NOT NULL DEFAULT 0,
      per_limit INT NOT NULL DEFAULT 1,
      start_time DATETIME NOT NULL,
      end_time DATETIME NOT NULL,
      status TINYINT NOT NULL DEFAULT 1,
      is_stackable TINYINT NOT NULL DEFAULT 0,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_seckill_goods (goods_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS full_discount_activities (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(100) NOT NULL,
      type TINYINT NOT NULL DEFAULT 1,
      threshold DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      discount_value DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      scope TINYINT NOT NULL DEFAULT 1,
      scope_ids VARCHAR(500) DEFAULT NULL,
      start_time DATETIME NOT NULL,
      end_time DATETIME NOT NULL,
      is_stackable TINYINT NOT NULL DEFAULT 0,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS group_buy_activities (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(100) NOT NULL,
      goods_id BIGINT UNSIGNED NOT NULL,
      leader_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      member_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      group_size INT NOT NULL DEFAULT 2,
      valid_hours INT NOT NULL DEFAULT 24,
      start_time DATETIME NOT NULL,
      end_time DATETIME NOT NULL,
      status TINYINT NOT NULL DEFAULT 1,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS distributor (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      member_id BIGINT UNSIGNED NOT NULL,
      level TINYINT NOT NULL DEFAULT 1,
      commission_rate DECIMAL(5,2) NOT NULL DEFAULT 5.00,
      status TINYINT NOT NULL DEFAULT 1,
      invited_by BIGINT UNSIGNED DEFAULT NULL,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_distributor_member (member_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS commission_logs (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      distributor_id BIGINT UNSIGNED NOT NULL,
      order_id BIGINT UNSIGNED NOT NULL,
      amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
      status TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_commission_distributor (distributor_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS articles (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      title VARCHAR(200) NOT NULL,
      category_id BIGINT UNSIGNED DEFAULT NULL,
      author VARCHAR(50) DEFAULT NULL,
      cover VARCHAR(300) DEFAULT NULL,
      summary VARCHAR(500) DEFAULT NULL,
      content MEDIUMTEXT,
      seo_title VARCHAR(200) DEFAULT NULL,
      seo_keywords VARCHAR(300) DEFAULT NULL,
      seo_desc VARCHAR(500) DEFAULT NULL,
      status TINYINT NOT NULL DEFAULT 0,
      publish_time DATETIME DEFAULT NULL,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_articles_category (category_id),
      KEY idx_articles_status (status)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS article_categories (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(50) NOT NULL,
      sort INT NOT NULL DEFAULT 0,
      status TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS ad_positions (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(50) NOT NULL,
      size VARCHAR(50) DEFAULT NULL,
      status TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS ads (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      position_id BIGINT UNSIGNED NOT NULL,
      type TINYINT NOT NULL DEFAULT 1,
      image VARCHAR(300) DEFAULT NULL,
      video VARCHAR(300) DEFAULT NULL,
      link VARCHAR(300) DEFAULT NULL,
      text VARCHAR(200) DEFAULT NULL,
      sort INT NOT NULL DEFAULT 0,
      start_time DATETIME DEFAULT NULL,
      end_time DATETIME DEFAULT NULL,
      status TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_ads_position (position_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS notices (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      title VARCHAR(200) NOT NULL,
      content TEXT,
      target TINYINT NOT NULL DEFAULT 0,
      target_level_id BIGINT UNSIGNED DEFAULT NULL,
      publish_time DATETIME DEFAULT NULL,
      status TINYINT NOT NULL DEFAULT 0,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_notices_status (status)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS system_configs (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      config_key VARCHAR(100) NOT NULL UNIQUE,
      config_value TEXT,
      remark VARCHAR(255) DEFAULT NULL,
      config_group VARCHAR(30) NOT NULL DEFAULT 'basic',
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS freight_templates (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(50) NOT NULL,
      type TINYINT NOT NULL DEFAULT 1,
      is_free_shipping TINYINT NOT NULL DEFAULT 0,
      regions_json TEXT,
      created_by BIGINT UNSIGNED NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS region (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      code VARCHAR(20) NOT NULL UNIQUE,
      name VARCHAR(100) NOT NULL,
      parent_code VARCHAR(20) NOT NULL DEFAULT '',
      level TINYINT NOT NULL DEFAULT 1,
      sort INT NOT NULL DEFAULT 0,
      status TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_region_parent (parent_code)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS sms_codes (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      phone VARCHAR(20) NOT NULL,
      scene VARCHAR(20) NOT NULL DEFAULT 'register',
      code_hash VARCHAR(255) NOT NULL,
      ip VARCHAR(45) DEFAULT NULL,
      expires_at DATETIME NOT NULL,
      used_at DATETIME DEFAULT NULL,
      fail_count INT NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_sms_codes_phone (phone, scene),
      KEY idx_sms_codes_expires (expires_at)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS member_address (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      member_id BIGINT UNSIGNED NOT NULL,
      receiver_name VARCHAR(50) NOT NULL,
      receiver_phone VARCHAR(20) NOT NULL,
      province_code VARCHAR(20) NOT NULL DEFAULT '',
      province VARCHAR(50) DEFAULT NULL,
      city_code VARCHAR(20) NOT NULL DEFAULT '',
      city VARCHAR(50) DEFAULT NULL,
      district_code VARCHAR(20) NOT NULL DEFAULT '',
      district VARCHAR(50) DEFAULT NULL,
      detail VARCHAR(200) NOT NULL,
      tag VARCHAR(20) DEFAULT NULL,
      is_default TINYINT NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      KEY idx_member_address_member (member_id)
    ) """ + ENGINE,
    """
    CREATE TABLE IF NOT EXISTS member_cart (
      id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      member_id BIGINT UNSIGNED NOT NULL,
      goods_id BIGINT UNSIGNED NOT NULL,
      sku_id BIGINT UNSIGNED NOT NULL,
      quantity INT NOT NULL DEFAULT 1,
      selected TINYINT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_member_cart (member_id, sku_id),
      KEY idx_member_cart_member (member_id)
    ) """ + ENGINE,
]


def ensure_tables():
    import asyncio

    from seed.runner import _connect

    async def run():
        conn = await _connect()
        try:
            async with conn.cursor() as cur:
                for sql in TABLES:
                    await cur.execute(sql)
            await ensure_content_updated_at(conn)
            await conn.commit()
            print(f"建表完成，共 {len(TABLES)} 张表")
        finally:
            conn.close()

    asyncio.run(run())


# 前台内容表统一补 updated_at（老库迁移用，seed 幂等执行）
CONTENT_TS_TABLES = (
    "goods_category",
    "specifications",
    "specification_values",
    "goods_images",
    "article_categories",
    "ad_positions",
)


async def ensure_content_updated_at(conn):
    """幂等：为前台内容表补齐 updated_at 列（重跑 seed.runner base 时执行）。"""
    from core.config import config

    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT TABLE_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND COLUMN_NAME='updated_at' AND TABLE_NAME IN (%s,%s,%s,%s,%s,%s)",
            (config.db_name,) + CONTENT_TS_TABLES,
        )
        rows = await cur.fetchall()
        have = {row["TABLE_NAME"] for row in rows}
        for table in CONTENT_TS_TABLES:
            if table not in have:
                await cur.execute(
                    "ALTER TABLE `" + table
                    + "` ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
                )
