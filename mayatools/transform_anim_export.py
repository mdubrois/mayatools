from __future__ import absolute_import

import os

from uitools.qt import QtGui

from maya import cmds

import ks.maya.downgrade

import sgpublish.exporter.maya
import sgpublish.exporter.ui.publish.maya
import sgpublish.exporter.ui.tabwidget
import sgpublish.exporter.ui.workarea
import sgpublish.uiutils
from sgpublish.exporter.ui.publish.generic import PublishSafetyError

from .locators import bake_global_locators, iter_nuke_script
from . import context
from .set_picker import SetPicker
from .tickets import ticket_ui_context


class Exporter(sgpublish.exporter.maya.Exporter):

    def __init__(self):
        super(Exporter, self).__init__(
            workspace=cmds.workspace(q=True, fullName=True) or None,
            filename_hint=cmds.file(q=True, sceneName=True) or 'locators.ma',
            publish_type='maya_locators',
        )

    def export_publish(self, publish, **kwargs):
        publish.path = os.path.join(publish.directory, 'locators.ma')
        self.export(publish.directory, publish.path, **kwargs)

    def export(self, directory, path, nodes):

        if not os.path.exists(directory):
            os.makedirs(directory)

        version = int(cmds.about(version=True).split()[0])
        locators = bake_global_locators(nodes)

        try:

            with context.selection():
                cmds.select(locators, replace=True)

                if version > 2011:
                    export_path = '%s.%d.ma' % (os.path.splitext(path)[0], version)
                    cmds.file(export_path, exportSelected=True, type='mayaAscii')
                    ks.maya.downgrade.downgrade_to_2011(
                        export_path,
                        path,
                    )

                else:
                    cmds.file(path, exportSelected=True, type='mayaAscii')

            # Nuke export.
            with open(os.path.splitext(path)[0] + '.nk', 'wb') as nuke_fh:
                for locator in locators:
                    nuke_fh.write(''.join(iter_nuke_script(locator)))

        finally:
            cmds.delete(*locators)
                

class Dialog(QtGui.QDialog):

    def __init__(self):
        super(Dialog, self).__init__()
        
        self._setupGui()
    
    def _warning(self, message):
        cmds.warning(message)

    def _error(self, message):
        cmds.confirmDialog(title='Scene Name Error', message=message, icon='critical')
        cmds.error(message)
            
    def _setupGui(self):
        self.setWindowTitle('Locator Export')
        self.setMinimumWidth(600)
        self.setLayout(QtGui.QVBoxLayout())
        
        self._setPicker = SetPicker(pattern='__locators__*', namesEnabled=False)
        self.layout().addWidget(self._setPicker)

        self._exporter = Exporter()
        self._exporter_widget = sgpublish.exporter.ui.tabwidget.Widget()
        self.layout().addWidget(self._exporter_widget)

        # SGPublishes.
        tab = sgpublish.exporter.ui.publish.maya.Widget(self._exporter)
        tab.beforeScreenshot.connect(lambda *args: self.hide())
        tab.afterScreenshot.connect(lambda *args: self.show())
        self._exporter_widget.addTab(tab, "Publish to Shotgun")

        # Work area.
        tab = sgpublish.exporter.ui.workarea.Widget(self._exporter, {
            'directory': 'data/locators',
            'sub_directory': '',
            'extension': '.ma',
            'workspace': cmds.workspace(q=True, fullName=True) or None,
            'filename': cmds.file(q=True, sceneName=True) or 'locators.ma',
            'warning': self._warning,
            'error': self._warning,
        })
        self._exporter_widget.addTab(tab, "Export to Work Area")

        button_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(button_layout)
        
        button_layout.addStretch()
        
        button = QtGui.QPushButton("Export", clicked=self._onExportClicked)
        button_layout.addWidget(button)
        
    def _onExportClicked(self):

        try:
            publisher = self._exporter_widget.export(nodes=self._setPicker.allSelectedNodes())
        except PublishSafetyError:
            return
    
        if publisher:
            sgpublish.uiutils.announce_publish_success(publisher)
        self.close()


def __before_reload__():
    if dialog:
        dialog.close()

dialog = None

def run():
    
    global dialog
    
    if dialog:
        dialog.close()
    
    # Be cautious if the scene was never saved
    filename = cmds.file(query=True, sceneName=True)
    if not filename:
        res = QtGui.QMessageBox.warning(None, 'Unsaved Scene', 'This scene has not beed saved. Continue anyways?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No
        )
        if res & QtGui.QMessageBox.No:
            return
    
    workspace = cmds.workspace(q=True, rootDirectory=True)
    if filename and not filename.startswith(workspace):
        res = QtGui.QMessageBox.warning(None, 'Mismatched Workspace', 'This scene is not from the current workspace. Continue anyways?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No
        )
        if res & QtGui.QMessageBox.No:
            return

    dialog = Dialog()    
    dialog.show()
