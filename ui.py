import webbrowser
from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import QIcon, QPixmap, QColor
from PySide2.QtWidgets import QMainWindow, QHBoxLayout, QVBoxLayout, QPushButton, QGridLayout, QColorDialog, \
    QComboBox, QLabel, QDoubleSpinBox, QDialog, QCheckBox, QFrame, QApplication, QLineEdit, QFileDialog, QMenuBar, \
    QMenu, QAction, QTreeWidget, QTreeWidgetItem
from maya import OpenMayaUI, cmds
import shiboken2
from functools import partial
import json
import os
from maya.api.OpenMaya import MMatrix


dpiF = QApplication.desktop().logicalDpiX() / 96.0


def killOtherInstances(self):
    for child in self.parent().children():
        if child == self:
            continue
        if child.__class__.__name__ != self.__class__.__name__:
            continue
        child.deleteLater()


def getMayaMainWindow():
    pointer = OpenMayaUI.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(int(pointer), QMainWindow)


def createSeparator():
    separator = QFrame()
    separator.setFrameShape(QFrame.HLine)
    separator.setFrameShadow(QFrame.Sunken)
    return separator


def formatSetAttr(edit):
    print(edit)
    editSplit = edit.split(' ')
    t = editSplit[0]
    plug = editSplit[1]

    shortPlug = plug.split('|')[-1]

    fullPlugSplit = shortPlug.split(':')
    namespace = ':'.join(fullPlugSplit[:-1])
    plug = fullPlugSplit[-1]

    plugSplit = plug.split('.')
    node = plugSplit[0]
    attr = '.'.join(plugSplit[1:])

    arguments = ' '.join(editSplit[2:])
    return namespace, node, '.{} -> {}'.format(attr, arguments)


class ReferenceEdits(QDialog):

    plop = {
        'setAttr': formatSetAttr
    }

    def __init__(self, parent=getMayaMainWindow()):
        super(ReferenceEdits, self).__init__(parent=parent)
        killOtherInstances(self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle('Reference Edits')

        # content
        self.referenceEditsTree = QTreeWidget()
        self.referenceEditsTree.setHeaderLabels(('Command',))

        referenceNodeCombo = QComboBox()
        referenceNodeCombo.currentTextChanged.connect(self.reloadReferenceEditsTree)

        for node in cmds.ls(type='reference'):
            referenceNodeCombo.addItem(node)

        # main layout
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(referenceNodeCombo)
        mainLayout.addWidget(self.referenceEditsTree)

    def reloadReferenceEditsTree(self, referenceNode):
        failed = cmds.referenceQuery(referenceNode, editStrings=True, failedEdits=True)
        successful = cmds.referenceQuery(referenceNode, editStrings=True, successfulEdits=True)

        namespaceItems = dict()
        nodeItems = dict()

        self.referenceEditsTree.clear()
        for edits, fail in ((failed, True), (successful, False)):
            for edit in edits:
                if not edit.startswith('setAttr'):
                    continue

                namespace, node, description = formatSetAttr(edit)

                if namespace not in namespaceItems.keys():
                    namespaceItem = QTreeWidgetItem(('{}:'.format(namespace),), data=namespace)
                    namespaceItems[namespace] = namespaceItem
                    self.referenceEditsTree.addTopLevelItem(namespaceItem)

                if node not in nodeItems.keys():
                    nodeItem = QTreeWidgetItem((node,), data=node)
                    nodeItems[node] = nodeItem
                    namespaceItems[namespace].addChild(nodeItem)

                editItem = QTreeWidgetItem((description,), data=edit)
                # editItem.setIcon(0, QIcon(':error.png')) if fail else None
                #
                # namespaceItems[namespace].setIcon(0, QIcon(':error.png')) if fail else None
                # nodeItems[node].setIcon(0, QIcon(':error.png')) if fail else None

                nodeItems[node].addChild(editItem)

        # self.referenceEditsTree.clear()
        # for edits, stateLabel in ((failed, 'failed'), (successful, 'successful')):
        #     stateItem = QTreeWidgetItem((stateLabel,))
        #     self.referenceEditsTree.addTopLevelItem(stateItem)
        #
        #     commandTypeItems = dict()
        #     nodeItems = dict()
        #
        #     for edit in edits:
        #         commandType = edit.split(' ')[0]
        #
        #         if commandType not in commandTypeItems.keys():
        #             commandTypeItem = QTreeWidgetItem((commandType,))
        #             commandTypeItems[commandType] = commandTypeItem
        #             stateItem.addChild(commandTypeItem)
        #
        #         formatter = self.plop.get(commandType)
        #         node, label = formatter(edit) if formatter else '', edit
        #         item = QTreeWidgetItem((label,), data=edit)
        #         commandTypeItems[commandType].addChild(item)
