import maya.cmds as cmds
import maya.mel as mel

def reset_to_origin(node):
    # Find position
    node_pos = cmds.xform(node, query=True, worldSpace=True, rotatePivot=True)

    # Freeze transformation for translation
    cmds.makeIdentity(node, apply=True, translate=True, rotate=False, scale=False, normal=False)

    # Find translation and move to origin
    node_translation = [-p for p in node_pos]
    cmds.xform(node, worldSpace=True, translation=node_translation)

    # Reset rotation and freeze transform
    cmds.setAttr(node + ".rotate", 0, 0, 0)
    cmds.makeIdentity(node, apply=True, translate=True, rotate=True, scale=False, normal=False)


    