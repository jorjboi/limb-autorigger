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


# Moves target object to destination object's position and orientation
# Won't work if objects are locked or have translate or rotate connections
def snap(target, dest, freeze_transform=False):
    
    # Use selected objects if None are provided
    if target == None and dest == None:
        target = cmds.ls(selection=True)[0]
        dest = cmds.ls(selection=True)[1]
    if target == None or dest == None:
        cmds.error("Must provide a target and destination object")
    
    # Get the world position and orientation of the destination
    dest_translation = cmds.xform(dest, query=True, translation=True, worldSpace=True)
    dest_rotation = cmds.xform(dest, query=True, rotation=True, worldSpace=True)
    
    # Set the world position of the target object to match the destination
    cmds.xform(target, translation=dest_translation, worldSpace=True)
    cmds.xform(target, rotation=dest_rotation, worldSpace=True)

    if freeze_transform:
        cmds.makeIdentity(target, apply=True, translate=True, rotate=True,
                                scale=True, normal=False)

    



