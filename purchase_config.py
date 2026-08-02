"""Single source of truth for the public Taobao purchase entry."""

from PySide6 import QtCore, QtGui, QtWidgets


# 统一店铺首页用于广告和新品关注。
TAOBAO_PURCHASE_URL = ""

TAOBAO_BUTTON_STYLE = (
    "QPushButton { background:#ff6a00; color:white; border:1px solid #e85d00; "
    "border-radius:8px; padding:0 16px; font-size:14px; font-weight:600; }"
    "QPushButton:hover { background:#e85d00; border-color:#cf5200; }"
    "QPushButton:pressed { background:#cf5200; }"
)


def open_taobao_purchase(parent=None, edition_id=None, product_title=""):
    """Open the one public Taobao product page; the buyer selects its SKU."""
    configured = str(TAOBAO_PURCHASE_URL).strip()
    if not configured:
        QtWidgets.QMessageBox.information(
            parent,
            "淘宝购买入口即将开放",
            "淘宝商品地址正在配置。\n\n"
            "商品上架并填写地址后，此按钮会打开统一商品页面，"
            "购买版本由您在淘宝商品规格中选择。",
        )
        return False

    url = QtCore.QUrl.fromUserInput(configured)
    host = url.host().lower()
    allowed = (
        url.scheme().lower() == "https"
        and (host == "taobao.com" or host.endswith(".taobao.com")
             or host == "m.tb.cn")
    )
    if not url.isValid() or not allowed:
        QtWidgets.QMessageBox.warning(
            parent,
            "购买链接暂不可用",
            "淘宝购买地址尚未正确配置，请通过官方客服购买或稍后重试。",
        )
        return False

    if not QtGui.QDesktopServices.openUrl(url):
        QtWidgets.QMessageBox.warning(
            parent,
            "无法打开淘宝",
            "系统未能打开浏览器，请稍后重试或通过官方客服购买。",
        )
        return False
    return True
