import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from scientific_memory_view import ScientificMemoryView


app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
view = ScientificMemoryView(
    vocabulary_path="assets/editions/gaokao/vocabulary.json"
)
view.resize(1280, 820)
view.show()
app.processEvents()
view.show_home()
app.processEvents()
view.grab().save("scientific_memory_home_preview.png")
view.show_catalog("root")
app.processEvents()
view.grab().save("scientific_memory_root_text_catalog_preview.png")
view.show_catalog("phonics")
app.processEvents()
view.grab().save("scientific_memory_phonics_text_catalog_preview.png")
view.show_catalog("scene")
app.processEvents()
view.grab().save("scientific_memory_compact_scene_preview.png")
view.show_catalog("relations")
app.processEvents()
view.grab().save("scientific_memory_relations_list_preview.png")
view.current_method = "root"
view.show_group(view.catalog.groups["root"][0])
app.processEvents()
view.grab().save("scientific_memory_verify_inside_preview.png")
QtCore.QTimer.singleShot(100, app.quit)
app.exec()
