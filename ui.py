import webbrowser
from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import QIcon, QPixmap, QColor
from PySide2.QtWidgets import QMainWindow, QHBoxLayout, QVBoxLayout, QPushButton, QGridLayout, QColorDialog, \
    QComboBox, QLabel, QDoubleSpinBox, QDialog, QCheckBox, QFrame, QApplication, QLineEdit, QFileDialog, QMenuBar, \
    QMenu, QAction, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator
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
    return edit.split(' ')[1]


def connectAttInfo(edit):
    return edit.split(' ')[2][1:-1]


def parentAttrInfo(edit):
    return edit.split('\"')[-2]


def splitPlug(plug):
    plugSplit = plug.split('.')
    node = plugSplit.pop(0)
    attr = '.'.join(plugSplit)

    return node, attr


def getRootNamespace(plug):
    plugSplit = plug.split(':')
    return plugSplit[0]


class ReferenceEdits(QDialog):
    # "addAttr", "connectAttr", "deleteAttr", "disconnectAttr", "parent", "setAttr", "lock" and "unlock"

    plop = {
        'setAttr': formatSetAttr
    }

    def __init__(self, parent=getMayaMainWindow()):
        super(ReferenceEdits, self).__init__(parent=parent)
        killOtherInstances(self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle('Reference Edits')
        self.setMinimumSize(QSize(250 * dpiF, 250 * dpiF))

        # content
        self.referenceEditsTree = QTreeWidget()
        self.referenceEditsTree.setHeaderHidden(True)
        self.referenceEditsTree.setSelectionMode(QTreeWidget.ExtendedSelection)

        # menu
        reloadAct = QAction('Reload', self)
        reloadAct.triggered.connect(self.reloadReferenceEditsTree)

        fileMenu = QMenu('File')
        fileMenu.addAction(reloadAct)

        menuBar = QMenuBar()
        menuBar.addMenu(fileMenu)

        # main layout
        mainLayout = QVBoxLayout(self)
        mainLayout.setMenuBar(menuBar)
        mainLayout.addWidget(self.referenceEditsTree)

        self.reloadReferenceEditsTree()

    def contextMenuEvent(self, event):
        selectTargetAct = QAction('Select In Scene Selected Targets', self)
        selectTargetAct.triggered.connect(self.selectTargets)

        unloadReferenceAct = QAction('Unload Selected References', self)
        unloadReferenceAct.triggered.connect(self.unloadReferences)

        loadReferenceAct = QAction('Load Selected References', self)
        loadReferenceAct.triggered.connect(self.loadReferences)

        removeEditAct = QAction('Remove Selected Edits', self)
        removeEditAct.triggered.connect(self.removeSelectedEdits)

        removeAllFailedEditAct = QAction('Remove All Failed Edits From Selected References', self)
        removeAllFailedEditAct.triggered.connect(self.removeAllFailedEdits)

        self.referenceEditsTree.isTopLevel()

        menu = QMenu()
        menu.addAction(selectTargetAct)
        menu.addSeparator()
        menu.addAction(unloadReferenceAct)
        menu.addAction(loadReferenceAct)
        menu.addSeparator()
        menu.addAction(removeEditAct)
        menu.addAction(removeAllFailedEditAct)
        menu.exec_(self.mapToGlobal(event.pos()))

    def reloadReferenceEditsTree(self):
        # store
        memory = dict()
        iterator = QTreeWidgetItemIterator(self.referenceEditsTree)
        while iterator.value():
            item = iterator.value()  # type: QTreeWidgetItem
            data = item.data(0, Qt.UserRole)
            memory[data['id']] = item.isExpanded(), item.isSelected()
            iterator += 1

        # create items
        self.referenceEditsTree.clear()
        for referenceNode in cmds.ls(type='reference'):
            if referenceNode == 'sharedReferenceNode' or cmds.referenceQuery(referenceNode, isNodeReferenced=True):
                continue

            isLoaded = cmds.referenceQuery(referenceNode, isLoaded=True)

            referenceTargets = list()
            referenceID = 'reference_{}'.format(referenceNode)
            referenceItem = QTreeWidgetItem((referenceNode,))
            referenceItem.setData(0, Qt.UserRole, {'targets': [referenceNode], 'referenceNode': referenceNode, 'id': referenceID})
            referenceItem.setToolTip(0, referenceNode)
            referenceItem.setIcon(0, QIcon(':out_reference.png' if isLoaded else ':unloadedReference.png'))
            self.referenceEditsTree.addTopLevelItem(referenceItem)

            failedEdits = cmds.referenceQuery(referenceNode, editStrings=True, failedEdits=True, successfulEdits=False)
            successfulEdits = cmds.referenceQuery(referenceNode, editStrings=True, failedEdits=False, successfulEdits=True)

            nodeItems = dict()

            for edits, failed in (failedEdits, True), (successfulEdits, False):
                for edit in edits:
                    commandType = edit.split(' ')[0]
                    target = None
                    if commandType == 'setAttr':
                        target = setAttInfo(edit)
                    elif commandType == 'connectAttr':
                        target = connectAttInfo(edit)
                    elif commandType == 'parent':
                        target = parentAttrInfo(edit)

                    if target is None:
                        editID = 'edit_{}'.format(edit)
                        editItem = QTreeWidgetItem((edit,))
                        editItem.setDisabled(True)
                        editItem.setToolTip(0, 'Type not supported.')
                        editItem.setData(0, Qt.UserRole, {'targets': [edit], 'referenceNode': referenceNode, 'id': editID, 'commandType': commandType})
                        editItem.setIcon(0, QIcon(':error.png')) if failed else None
                        referenceItem.addChild(editItem)

                    elif '.' in target:
                        plug = target

                        node, attr = splitPlug(plug)

                        if node not in nodeItems.keys():
                            nodeID = 'node_{}'.format(node)
                            nodeShortName = node.split('|')[-1].split(':')[-1]
                            nodeItem = QTreeWidgetItem((nodeShortName,))
                            nodeItem.setToolTip(0, node)
                            nodeItem.setData(0, Qt.UserRole, {'targets': [node], 'referenceNode': referenceNode, 'id': nodeID})
                            nodeItems[node] = nodeItem
                            referenceItem.addChild(nodeItem)

                        editID = 'edit_{}'.format(plug)
                        editItem = QTreeWidgetItem((edit,))
                        editItem.setData(0, Qt.UserRole, {'targets': [plug], 'referenceNode': referenceNode, 'id': editID, 'commandType': commandType})
                        editItem.setToolTip(0, plug)
                        editItem.setIcon(0, QIcon(':error.png')) if failed else None

                        plugID = 'plug_{}'.format(plug)
                        plugShortName = '.'.join(plug.split('|')[-1].split('.')[1:])
                        plugItem = QTreeWidgetItem((plugShortName,))
                        plugItem.setToolTip(0, plug)
                        plugItem.setData(0, Qt.UserRole, {'targets': [plug], 'referenceNode': referenceNode, 'id': plugID})
                        plugItem.setIcon(0, QIcon(':error.png')) if failed else None
                        plugItem.addChild(editItem)

                        nodeItems[node].addChild(plugItem)
                        nodeItems[node].setIcon(0, QIcon(':error.png')) if failed else None

                        referenceTargets.append(node)

                    else:
                        node = target

                        nodeID = 'node_{}'.format(node)
                        nodeShortName = node.split('|')[-1].split(':')[-1]
                        nodeItem = QTreeWidgetItem((nodeShortName,))
                        nodeItem.setData(0, Qt.UserRole, {'targets': [node], 'referenceNode': referenceNode, 'id': nodeID})
                        nodeItem.setToolTip(0, node)
                        nodeItems[node] = nodeItem
                        referenceItem.addChild(nodeItem)

                        editID = 'edit_{}'.format(node)
                        editItem = QTreeWidgetItem((edit,))
                        editItem.setData(0, Qt.UserRole, {'targets': [node], 'referenceNode': referenceNode, 'id': editID, 'commandType': commandType})
                        editItem.setIcon(0, QIcon(':error.png')) if failed else None
                        nodeItem.addChild(editItem)

        # restore
        iterator = QTreeWidgetItemIterator(self.referenceEditsTree)
        while iterator.value():
            item = iterator.value()  # type: QTreeWidgetItem
            data = item.data(0, Qt.UserRole)
            id_ = data['id']
            if id_ in memory:
                expanded, selected = memory[id_]
                item.setExpanded(expanded)
                item.setSelected(selected)
            iterator += 1

    def removeAllFailedEdits(self):
        selectedItems = self.referenceEditsTree.selectedItems()
        referenceNodes = list({x.data(0, Qt.UserRole)['referenceNode'] for x in selectedItems})

        reload_ = False
        for referenceNode in referenceNodes:
            isLoaded = cmds.referenceQuery(referenceNode, isLoaded=True)
            if isLoaded:
                cmds.warning('To proceed, please unload {}.'.format(repr(str(referenceNode))))
                continue
            cmds.referenceEdit(referenceNode, removeEdits=True)
            reload_ = True

        self.reloadReferenceEditsTree() if reload_ else None

    def unloadReferences(self):
        selectedItems = self.referenceEditsTree.selectedItems()
        referenceNodes = list({x.data(0, Qt.UserRole)['referenceNode'] for x in selectedItems})

        if not referenceNodes:
            cmds.warning('No references selected')

        reload_ = False
        for referenceNode in referenceNodes:
            if cmds.referenceQuery(referenceNode, isLoaded=True):
                cmds.file(unloadReference=referenceNode)
                reload_ = True

        self.reloadReferenceEditsTree() if reload_ else None

    def loadReferences(self):
        selectedItems = self.referenceEditsTree.selectedItems()
        referenceNodes = list({x.data(0, Qt.UserRole)['referenceNode'] for x in selectedItems})

        if not referenceNodes:
            cmds.warning('No references selected')

        reload_ = False
        for referenceNode in referenceNodes:
            if not cmds.referenceQuery(referenceNode, isLoaded=True):
                cmds.file(loadReference=referenceNode)
                reload_ = True

        self.reloadReferenceEditsTree() if reload_ else None

    def selectTargets(self):
        selectedItems = self.referenceEditsTree.selectedItems()

        targets = list()
        for item in selectedItems:
            for target in item.data(0, Qt.UserRole)['targets']:
                if target not in targets and cmds.objExists(target):
                    targets.append(target)

        cmds.select(targets)

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
                cmds.warning('To proceed, please unload {}.'.format(repr(str(referenceNode))))
                continue

            if not targets:
                cmds.warning('Nothing to remove found.')
                continue

            commandType = data.get('commandType')

            referenceEditKwargs = dict()
            if commandType:
                referenceEditKwargs = dict(editCommand=commandType)

            for target in targets:
                cmds.referenceEdit(target, removeEdits=True, successfulEdits=True, **referenceEditKwargs)

            reload_ = True

        self.reloadReferenceEditsTree() if reload_ else None
