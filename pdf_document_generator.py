# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

from PySide6 import QtCore, QtGui


SHOP_NAME = "\u53cc\u6167\u7684\u6559\u8f85\u8d44\u6599\u5c0f\u5e9796"
APP_NAME = "\u9ad8\u4e2d/\u9ad8\u8003\u82f1\u8bed\u5355\u8bcd\u52a9\u624b"


def _license_path():
    return os.path.join(os.path.expanduser("~"), ".HighSchoolEnglishHelper", "licensing.dat")


def _read_license_data():
    try:
        with open(_license_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _activation_tail(activation_code):
    compact = "".join(ch for ch in str(activation_code) if ch.isalnum())
    return compact[-4:].upper() if compact else "\u672a\u8bb0\u5f55"


def _short_machine_id(machine_id):
    compact = str(machine_id or "").replace("-", "").upper()
    if len(compact) >= 8:
        return compact[:4] + "-" + compact[-4:]
    return compact or "\u672a\u8bb0\u5f55"


def _watermark_texts(watermark_mode, machine_id=None, activation_code=None):
    if watermark_mode == "store":
        return {
            "center": f"{SHOP_NAME} | \u6b63\u7248\u6559\u8f85\u8d44\u6599",
            "footer": f"\u6b63\u7248\u6e20\u9053\uff1a\u6dd8\u5b9d\u5e97\u300c{SHOP_NAME}\u300d | \u7981\u6b62\u8f6c\u552e\u3001\u642c\u8fd0\u3001\u4e8c\u6b21\u4e0a\u4f20",
        }

    license_data = _read_license_data()
    machine = machine_id or license_data.get("machine_id", "")
    activation = activation_code or license_data.get("activation_code", "")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "center": f"{APP_NAME} | {SHOP_NAME} | \u4ec5\u9650\u6388\u6743\u7528\u6237\u672c\u4eba\u4f7f\u7528",
        "footer": (
            f"\u6b63\u7248\u6e20\u9053\uff1a{SHOP_NAME} | "
            f"\u6388\u6743\u8bbe\u5907\uff1a{_short_machine_id(machine)} | "
            f"\u6fc0\u6d3b\u7801\u5c3e\u53f7\uff1a{_activation_tail(activation)} | "
            f"\u751f\u6210\u65f6\u95f4\uff1a{generated_at} | "
            f"\u7981\u6b62\u8f6c\u552e\u4f20\u64ad"
        ),
    }


def _mode_labels(mode, data_type):
    labels = {
        "normal": ("\u82f1\u8bed", "\u4e2d\u6587"),
        "en_dictate_cn": ("\u53ef\u89c1\u5185\u5bb9", "\u9ed8\u5199\u533a"),
        "cn_dictate_en": ("\u53ef\u89c1\u5185\u5bb9", "\u9ed8\u5199\u533a"),
    }
    visible, blank = labels.get(mode, labels["normal"])
    if data_type == "phrases" and mode == "normal":
        return "\u77ed\u8bed", "\u7ffb\u8bd1"
    if data_type == "irregular_verbs" and mode == "normal":
        return "\u539f\u5f62", "\u8fc7\u53bb\u5f0f / \u8fc7\u53bb\u5206\u8bcd / \u4e2d\u6587"
    return visible, blank


def _entry_text(item, mode):
    word = str(item.get("word") or item.get("english") or "")
    content = str(item.get("content") or item.get("translation") or "")
    if mode == "en_dictate_cn":
        return word, ""
    if mode == "cn_dictate_en":
        return content, ""
    return word, content


def _draw_text(painter, rect, text, font, color, flags=None):
    painter.save()
    painter.setFont(font)
    painter.setPen(QtGui.QColor(color))
    if flags is None:
        flags = QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.TextFlag.TextWordWrap
    painter.drawText(rect, int(flags), str(text))
    painter.restore()


def _make_font(family, point_size, bold=False):
    font = QtGui.QFont(family)
    font.setPointSizeF(float(point_size))
    font.setBold(bool(bold))
    return font


def _fit_font(text, rect, family, preferred_size, minimum_size, flags, bold=False):
    """Choose the largest font that keeps all text inside the cell."""
    value = str(text or "")
    size = float(preferred_size)
    while size >= float(minimum_size):
        font = _make_font(family, size, bold=bold)
        bounds = QtGui.QFontMetricsF(font).boundingRect(rect, int(flags), value)
        if bounds.width() <= rect.width() + 0.5 and bounds.height() <= rect.height() + 0.5:
            return font
        size -= 0.25
    return _make_font(family, minimum_size, bold=bold)


def _draw_fitted_text(
    painter,
    rect,
    text,
    family,
    preferred_size,
    minimum_size,
    color,
    flags,
    bold=False,
):
    font = _fit_font(
        text,
        rect,
        family,
        preferred_size,
        minimum_size,
        flags,
        bold=bold,
    )
    _draw_text(painter, rect, text, font, color, flags)


def _draw_watermark(painter, width, height, texts):
    painter.save()
    painter.translate(width / 2, height / 2)
    painter.rotate(-28)
    font = QtGui.QFont("Microsoft YaHei", 20)
    font.setBold(True)
    painter.setFont(font)
    color = QtGui.QColor(120, 120, 120, 36)
    painter.setPen(color)
    rect = QtCore.QRectF(-width * 0.65, -height * 0.25, width * 1.3, height * 0.5)
    painter.drawText(rect, int(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.TextFlag.TextWordWrap), texts["center"])
    painter.restore()


def _draw_footer(painter, width, height, margin_x, texts):
    footer_rect = QtCore.QRectF(margin_x, height - 122, width - margin_x * 2, 42)
    _draw_fitted_text(
        painter,
        footer_rect,
        texts["footer"],
        "Microsoft YaHei",
        7.5,
        6.5,
        QtGui.QColor(95, 95, 95),
        QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.TextFlag.TextWordWrap,
    )


def _draw_page(painter, width, height, page_items, start_index, mode, data_type, texts, document_title):
    margin_x = 95
    margin_top = 100
    table_top = 235
    table_bottom = height - 150
    row_count = 18
    header_h = 72
    row_h = (table_bottom - table_top - header_h) / row_count
    table_w = width - margin_x * 2
    col_widths = [0.055, 0.19, 0.255, 0.055, 0.19, 0.255]
    col_widths = [table_w * w for w in col_widths]

    _draw_watermark(painter, width, height, texts)

    _draw_fitted_text(
        painter,
        QtCore.QRectF(margin_x + table_w * 0.22, margin_top - 72, table_w * 0.56, 86),
        document_title or APP_NAME,
        "Microsoft YaHei",
        15,
        11,
        QtGui.QColor(30, 30, 30),
        QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.TextFlag.TextWordWrap,
        bold=True,
    )

    _draw_text(
        painter,
        QtCore.QRectF(margin_x, margin_top - 62, table_w * 0.23, 62),
        APP_NAME,
        QtGui.QFont("Microsoft YaHei", 8),
        QtGui.QColor(80, 80, 80),
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
    )

    shop_font = QtGui.QFont("Microsoft YaHei", 7)
    shop_font.setBold(True)
    _draw_text(
        painter,
        QtCore.QRectF(margin_x + table_w * 0.77, margin_top - 62, table_w * 0.23, 62),
        f"淘宝店：{SHOP_NAME}",
        shop_font,
        QtGui.QColor(210, 40, 40),
        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.TextFlag.TextWordWrap,
    )

    painter.save()
    painter.setPen(QtGui.QPen(QtGui.QColor(90, 90, 90), 1))
    painter.setBrush(QtGui.QColor(245, 247, 250))
    painter.drawRect(QtCore.QRectF(margin_x, table_top, table_w, header_h))
    painter.restore()

    visible_header, blank_header = _mode_labels(mode, data_type)
    headers = ["#", visible_header, blank_header, "#", visible_header, blank_header]
    x = margin_x
    for idx, col_w in enumerate(col_widths):
        rect = QtCore.QRectF(x, table_top, col_w, header_h)
        _draw_text(
            painter,
            rect.adjusted(6, 0, -6, 0),
            headers[idx],
            _make_font("Microsoft YaHei", 9, bold=True),
            QtGui.QColor(20, 20, 20),
            QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.TextFlag.TextWordWrap,
        )
        x += col_w

    for row in range(row_count):
        y = table_top + header_h + row * row_h
        painter.save()
        painter.setPen(QtGui.QPen(QtGui.QColor(170, 170, 170), 1))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawRect(QtCore.QRectF(margin_x, y, table_w, row_h))
        painter.restore()

        for half in range(2):
            item_index = row * 2 + half
            if item_index >= len(page_items):
                continue
            item = page_items[item_index]
            visible, blank = _entry_text(item, mode)
            values = [str(start_index + item_index + 1), visible, blank]
            base_col = half * 3
            x = margin_x + sum(col_widths[:base_col])
            for offset, value in enumerate(values):
                col_w = col_widths[base_col + offset]
                rect = QtCore.QRectF(x + 6, y + 5, col_w - 12, row_h - 10)
                if offset == 0:
                    flags = QtCore.Qt.AlignmentFlag.AlignCenter
                    family, preferred, minimum = "Microsoft YaHei", 7.5, 7
                    color = QtGui.QColor(115, 115, 115)
                else:
                    flags = (
                        QtCore.Qt.AlignmentFlag.AlignVCenter
                        | QtCore.Qt.TextFlag.TextWordWrap
                        | QtCore.Qt.TextFlag.TextWrapAnywhere
                    )
                    is_english_column = offset == 1 and mode != "cn_dictate_en"
                    family = "Arial" if is_english_column else "Microsoft YaHei"
                    preferred = 9.5 if is_english_column else 9
                    minimum = 7.5
                    color = QtGui.QColor(28, 32, 36)
                _draw_fitted_text(
                    painter,
                    rect,
                    value,
                    family,
                    preferred,
                    minimum,
                    color,
                    flags,
                )
                x += col_w

    painter.save()
    painter.setPen(QtGui.QPen(QtGui.QColor(120, 120, 120), 1))
    x = margin_x
    for col_w in col_widths:
        painter.drawLine(QtCore.QPointF(x, table_top), QtCore.QPointF(x, table_bottom))
        x += col_w
    painter.drawLine(QtCore.QPointF(margin_x + table_w, table_top), QtCore.QPointF(margin_x + table_w, table_bottom))
    painter.drawLine(QtCore.QPointF(margin_x, table_top), QtCore.QPointF(margin_x + table_w, table_top))
    painter.drawLine(QtCore.QPointF(margin_x, table_bottom), QtCore.QPointF(margin_x + table_w, table_bottom))
    painter.restore()

    _draw_footer(painter, width, height, margin_x, texts)


def generate_pdf_table(data, output_file, mode="normal", data_type="words", watermark_mode="licensed", machine_id=None, activation_code=None, document_title=None):
    writer = QtGui.QPdfWriter(output_file)
    writer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))
    writer.setResolution(300)
    writer.setCreator(APP_NAME)
    writer.setTitle(document_title or APP_NAME)

    painter = QtGui.QPainter(writer)
    if not painter.isActive():
        raise RuntimeError("PDF painter failed to start")

    texts = _watermark_texts(watermark_mode, machine_id=machine_id, activation_code=activation_code)
    width = writer.width()
    height = writer.height()
    items_per_page = 36

    try:
        for page_start in range(0, len(data), items_per_page):
            if page_start:
                writer.newPage()
            page_items = data[page_start:page_start + items_per_page]
            _draw_page(painter, width, height, page_items, page_start, mode, data_type, texts, document_title)
    finally:
        painter.end()
