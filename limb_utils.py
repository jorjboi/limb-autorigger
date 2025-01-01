import math
import maya.cmds as cmds
import maya.mel as mel


def reset_to_origin(node):
    # Find position
    node_pos = cmds.xform(node, query=True, worldSpace=True, rotatePivot=True)

    # Freeze transformation for translation
    cmds.makeIdentity(node, apply=True, translate=True,
                      rotate=False, scale=False, normal=False)

    # Find translation and move to origin
    node_translation = [-p for p in node_pos]
    cmds.xform(node, worldSpace=True, translation=node_translation)

    # Reset rotation and freeze transform
    reset_transformation(node, rotate=True)
    cmds.makeIdentity(node, apply=True, translate=True,
                      rotate=True, scale=False, normal=False)


# Moves target object to destination object's position and orientation
# Won't work if objects are locked or have translate or rotate connections
def snap(target, dest, freeze_transform=False, translate=True, rotate=True):

    # Use selected objects if None are provided
    if target == None and dest == None:
        target = cmds.ls(selection=True)[0]
        dest = cmds.ls(selection=True)[1]
    if target == None or dest == None:
        cmds.error("Must provide a target and destination object")

    # Set position and orientation of the target to the dest
    if translate:
        dest_translation = cmds.xform(
            dest, query=True, translation=True, worldSpace=True)
        cmds.xform(target, translation=dest_translation, worldSpace=True)
    if rotate:
        dest_rotation = cmds.xform(
            dest, query=True, rotation=True, worldSpace=True)
        cmds.xform(target, rotation=dest_rotation, worldSpace=True)
    if freeze_transform:
        cmds.makeIdentity(target, apply=True, translate=True, rotate=True,
                          scale=True, normal=False)


def distance(node_a, node_b):
    a_loc = cmds.xform(node_a, query=True, worldSpace=True, rotatePivot=True)
    b_loc = cmds.xform(node_b, query=True, worldSpace=True, rotatePivot=True)
    dist = pow(sum([pow(a-b, 2) for a, b in zip(a_loc, b_loc)]), 0.5)
    return dist


def create_curve(point_list, name, deg=1):
    curve = cmds.curve(degree=deg, p=point_list, name=name)
    shape = cmds.listRelatives(curve, shapes=True)[0]
    cmds.rename(shape, curve + 'Shape')
    return curve

# align local rotation axes of control to the joint
# Code taken from Nick Miller


def align_lras(snap_align=False, delete_history=True, sel=None):
    # get selection (first ctrl, then joint)
    if not sel:
        sel = cmds.ls(selection=True)

    if len(sel) <= 1:
        cmds.error('Select the control first, then the joint to align.')
    ctrl = sel[0]
    jnt = sel[1]

    # check to see if the control has a parent
    # if it does, un parent it by parenting it to the world
    parent_node = cmds.listRelatives(ctrl, parent=True)
    if parent_node:
        cmds.parent(ctrl, world=True)

    # store the ctrl/joint's world space position, rotation, and matrix
    jnt_matrix = cmds.xform(jnt, query=True, worldSpace=True, matrix=True)
    jnt_pos = cmds.xform(jnt, query=True, worldSpace=True, rotatePivot=True)
    jnt_rot = cmds.xform(jnt, query=True, worldSpace=True, rotation=True)
    ctrl_pos = cmds.xform(ctrl, query=True, worldSpace=True, rotatePivot=True)
    ctrl_rot = cmds.xform(ctrl, query=True, worldSpace=True, rotation=True)

    # in maya 2020 we can choose to use the offsetParentMatrix instead of
    # using an offset group
    if cmds.objExists(ctrl + '.offsetParentMatrix'):
        off_grp = False
        # ensure offset matrix has default values
        cmds.setAttr(ctrl + '.offsetParentMatrix',
                     [1.0, 0.0, 0.0, 0.0, 0.0,
                      1.0, 0.0, 0.0, 0.0, 0.0,
                      1.0, 0.0, 0.0, 0.0, 0.0,
                      1.0], type='matrix')
        reset_to_origin(ctrl)
        # copy joint's matrix to control's offsetParentMatrix
        cmds.setAttr(ctrl + '.offsetParentMatrix', jnt_matrix, type='matrix')

        if parent_node:
            # make temporary joints to help calculate offset matrix
            tmp_parent_jnt = cmds.joint(None, name='tmp_01_JNT')
            tmp_child_jnt = cmds.joint(tmp_parent_jnt, name='tmp_02_JNT')
            snap(tmp_parent_jnt, parent_node[0])
            snap(tmp_child_jnt, jnt)
            cmds.parent(ctrl, parent_node[0])
            reset_transformation(ctrl, True, True, True)

            child_matrix = cmds.getAttr(tmp_child_jnt + '.matrix')
            cmds.setAttr(ctrl + '.offsetParentMatrix',
                         child_matrix, type='matrix')
            cmds.delete(tmp_parent_jnt)

    # Maya 2019 and below
    else:
        reset_to_origin(ctrl)
        # create offset group
        off_grp = cmds.createNode('transform', name=ctrl + '_OFF_GRP')

        # move offset group to joint position, parent ctrl to it, zero channels
        cmds.xform(off_grp, worldSpace=True,
                   translation=jnt_pos, rotation=jnt_rot)
        if parent_node:
            cmds.parent(off_grp, parent_node[0])

    # move the control back into place
    cmds.xform(ctrl, worldSpace=True, translation=ctrl_pos)
    cmds.xform(ctrl, worldSpace=True, rotation=ctrl_rot)

    # parent control to offset group, if it exists
    if off_grp:
        cmds.parent(ctrl, off_grp)

    # freeze transforms again, then move pivot to match joint's
    if snap_align:
        reset_transformation(ctrl, True, True, True)
    else:
        cmds.makeIdentity(ctrl, apply=True, translate=True, rotate=True,
                          scale=False, normal=False)
    cmds.xform(ctrl, worldSpace=True, pivots=jnt_pos)

    # delete construction history
    if delete_history:
        cmds.delete(ctrl, ch=True)
    if off_grp:
        return off_grp
    else:
        return ctrl


def reset_transformation(nodes, translate=False, rotate=False, scale=False):
    if not nodes:
        nodes = cmds.ls(selection=True)
    if not isinstance(nodes, list):
        nodes = [nodes]
    for node in nodes:
        if translate:
            cmds.setAttr(node + '.translate', 0, 0, 0)
        if rotate:
            cmds.setAttr(node + '.rotate', 0, 0, 0)
        if scale:
            cmds.setAttr(node + '.scale', 1, 1, 1)


def get_axis_vector(axis='X'):
    axis_vec = (1, 0, 0)
    if axis[-1] == 'X':
        pass
    elif axis[-1] == 'Y':
        axis_vec = (0, 1, 0)
    elif axis[-1] == 'Z':
        axis_vec = (0, 0, 1)
    else:
        cmds.error("Must be X, Y, Z or -X, -Y, -Z")
    if axis[0] == '-':
        axis_vec = tuple((-a for a in axis))
    return axis_vec
