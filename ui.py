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


def setAttInfo(edit):
    editSplit = edit.split(' ')

    editSplit.pop(0)

    plug = editSplit.pop(0)
    arguments = ''.join(editSplit)
    return plug, arguments


def splitPlug(plug):
    plugSplit = plug.split('.')
    node = plugSplit.pop(0)
    attr = '.'.join(plugSplit)

    return node, attr


def getRootNamespace(plug):
    plugSplit = plug.split(':')
    return plugSplit[0]


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
        self.referenceEditsTree.setHeaderHidden(True)

        # main layout
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(self.referenceEditsTree)

        self.reloadReferenceEditsTree()

    def reloadReferenceEditsTree(self):
        # items = self.referenceEditsTree.items()

        self.referenceEditsTree.clear()
        for referenceNode in cmds.ls(type='reference'):
            if referenceNode == 'sharedReferenceNode' or cmds.referenceQuery(referenceNode, isNodeReferenced=True):
                continue

            isLoaded = cmds.referenceQuery(referenceNode, isLoaded=True)

            referenceTargets = list()
            referenceItem = QTreeWidgetItem((referenceNode,))
            referenceItem.setIcon(0, QIcon(':out_reference.png' if isLoaded else ':unloadedReference.png'))
            self.referenceEditsTree.addTopLevelItem(referenceItem)

            failedEdits = cmds.referenceQuery(referenceNode, editStrings=True, failedEdits=True, successfulEdits=False)
            successfulEdits = cmds.referenceQuery(referenceNode, editStrings=True, failedEdits=False, successfulEdits=True)

            nodeItems = dict()

            for edits, failed in (failedEdits, True), (successfulEdits, False):
                for edit in edits:
                    if not edit.startswith('setAttr'):
                        continue

                    plug, arguments = setAttInfo(edit)
                    node, attr = splitPlug(plug)

                    if node not in nodeItems.keys():
                        nodeItem = QTreeWidgetItem((node,))
                        nodeItem.setData(0, Qt.UserRole, {'targets': [node], 'referenceNode': referenceNode})
                        nodeItems[node] = nodeItem
                        referenceItem.addChild(nodeItem)

                    editItem = QTreeWidgetItem((edit,))
                    editItem.setData(0, Qt.UserRole, {'targets': [plug], 'referenceNode': referenceNode})
                    editItem.setIcon(0, QIcon(':error.png')) if failed else None

                    referenceTargets.append(node)

                    nodeItems[node].setIcon(0, QIcon(':error.png')) if failed else None

                    nodeItems[node].addChild(editItem)

            referenceItem.setData(0, Qt.UserRole, {'targets': referenceTargets, 'referenceNode': referenceNode})

    def contextMenuEvent(self, event):
        removeEditAct = QAction('Remove Selected Edits', self)
        removeEditAct.triggered.connect(self.removeSelectedEdits)

        unloadReferenceAct = QAction('Unload Selected References', self)
        # unloadReferenceAct.triggered.connect(self.unloadReferences)

        self.referenceEditsTree.isTopLevel()

        menu = QMenu()
        menu.addAction(removeEditAct)
        menu.addAction(unloadReferenceAct)
        menu.exec_(self.mapToGlobal(event.pos()))

    def removeSelectedEdits(self):
        selectedItems = self.referenceEditsTree.selectedItems()

        if not selectedItems:
            cmds.warning('Nothing selected.')
            return

        reload_ = False
        for item in selectedItems:
            data = item.data(0, Qt.UserRole)
            referenceNode = data['referenceNode']
            isLoaded = cmds.referenceQuery(referenceNode, isLoaded=True)
            targets = data['targets']

            if isLoaded:
                print('To proceed, please unload {}.'.format(repr(str(referenceNode))))
                continue

            if not targets:
                print('Nothing to remove found.')
                continue

            [cmds.referenceEdit(target, removeEdits=True, successfulEdits=True) for target in targets]
            reload_ = True

        self.reloadReferenceEditsTree() if reload_ else None
