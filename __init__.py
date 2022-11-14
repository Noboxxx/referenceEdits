"""
import sys
toDelete = list()
for n, m in sys.modules.items():
    if n.startswith('referenceEdits') and m:
        toDelete.append(n)
for k in toDelete:
    print(k)
    del sys.modules[k]


from referenceEdits.ui import ReferenceEdits
ui = ReferenceEdits()
ui.show()
"""

# TODO:
#   - unknown edits
#   - all command types
#   - search edits through nodes and attr. Not just trough referenceNode
#   - export / import edits ?