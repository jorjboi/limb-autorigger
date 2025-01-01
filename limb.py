import maya.cmds as cmds
import maya.mel as mel
import lrig.limb_utils as limb_utils
import importlib
importlib.reload(limb_utils)

TRANSLATE = "translate"
ROTATE = "rotate"
SCALE = "scale"
LEFT_SHOULDER = "LeftShoulder"  # "L_shoulder_JNT"
LEFT_ELBOW = "LeftElbow"  # "L_elbow_JNT"
LEFT_WRIST = "LeftWrist"  # "L_wrist_JNT"
LEFT_POLE_VECTOR = "LeftShoulder_PV"

arm_aliases = {LEFT_SHOULDER: 'Shoulder',
               LEFT_ELBOW: 'Elbow',
               LEFT_WRIST: 'Wrist'}


def create_limb(side='L', limb='arm',
                joints=[LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST],
                aliases=arm_aliases, pole_vector=LEFT_POLE_VECTOR,
                primary_axis='X', up_axis='Y',
                del_guides=False, stretch=True, color_dict={}):
   # Checks
    if side not in ['L', 'R']:
        cmds.error("Must specify L (left) or R (right) for side")
    if limb not in ['arm', 'leg']:
        cmds.error("Must specify arm or leg for limb")
    if len(joints) != 3 or len(aliases) != 3:
        cmds.error("Must create 3 joints for a limb")

    side_name = "Left" if side == 'L' else "Right"
    limb_name = limb.capitalize()
    base_name = side_name + limb_name

    ik_chain = create_chain(side_name, joints, aliases, 'IK')
    fk_chain = create_chain(side_name, joints, aliases, 'FK')
    bind_chain = create_chain(side_name, joints, aliases, 'Bind')

    # Find and create a good size for the control based on model size
    arm_len = limb_utils.distance(fk_chain[0], fk_chain[-1])
    size = arm_len/5.0
    create_blend_control(size, up_axis, bind_chain[-1], base_name)

    # Blend IK/FK with blend color nodes to create bind limb
    blend_ik_fk(ik_chain, fk_chain, bind_chain, base_name)

    # Create FK Controls
    fk_ctrls = create_fk_controls(fk_chain, primary_axis, size)

    # Create IK Controls and Handle
    ik_ctrls = create_ik_controls_and_handle(
        base_name, ik_chain, pole_vector, primary_axis, size)
    ik_base_ctrl = ik_ctrls['base_ctrl']
    ik_world_ctrl = ik_ctrls['world_ctrl']
    ik_local_ctrl = ik_ctrls['local_ctrl']
    if stretch:
        ik_stretch_ctrls = add_ik_stretch(base_name, 'arm', ik_chain,
                                          ik_base_ctrl, ik_world_ctrl, ik_local_ctrl,
                                          primary_axis)
        add_fk_stretch(fk_chain, fk_ctrls, primary_axis)

# Returns a list of joints for an IK, FK, or bind chain


def create_chain(side, joints, aliases, chain_type='IK'):
    chain = []
    idx = 0
    for j in joints:
        if idx == 0:  # Root joint, no parent
            joint = cmds.joint(None, name='{}{}_{}_Joint'.format(
                side, aliases[j], chain_type))
        else:
            joint = cmds.joint(chain[idx-1],
                               name='{}{}_{}_Joint'.format(side, aliases[j], chain_type))
        limb_utils.snap(joint, j, freeze_transform=True)
        chain.append(joint)
        idx += 1
    return chain


def create_blend_control(size=1, up_axis='Y', bind_joint='LeftWrist_Bind_Joint', base_name=""):
    plus_shape_coords = [[-0.333, 0.333, 0.0], [-0.333, 1.0, 0.0],
                         [0.333, 1.0, 0.0], [0.333, 0.333, 0.0],
                         [1.0, 0.333, 0.0], [1.0, -0.333, 0.0],
                         [0.333, -0.333, 0.0], [0.333, -1.0, 0.0],
                         [-0.333, -1.0, 0.0], [-0.333, -0.333, 0.0],
                         [-1.0, -0.333, 0.0], [-1.0, 0.333, 0.0],
                         [-0.333, 0.333, 0.0]]
    plus_control_curve = limb_utils.create_curve(
        plus_shape_coords, base_name + "_Control")
    limb_utils.align_lras(snap_align=True, sel=[
                          plus_control_curve, bind_joint])

    cmds.setAttr(plus_control_curve + '.' + SCALE,
                 size * 0.25, size * 0.25, size * 0.25)
    # Offset it from the model
    offset = size * 1.5 * sum(limb_utils.get_axis_vector(up_axis))
    cmds.setAttr(plus_control_curve + "." + TRANSLATE + up_axis[-1], offset)

    # Freeze transformation
    cmds.makeIdentity(plus_control_curve, apply=True, normal=False)

    # Parent constrain to wrist of our bind joint
    cmds.parentConstraint(bind_joint, plus_control_curve, maintainOffset=True)
    # Add IK/FK switching
    cmds.addAttr(plus_control_curve, attributeType='double', min=0, max=1, defaultValue=1,
                 keyable=True, longName='iKfK')
    return plus_control_curve


def blend_ik_fk(ik_chain, fk_chain, bind_chain, base_name):
    parts = [b.replace("_Bind_Joint", '') for b in bind_chain]
    for ik, fk, bind, part in zip(ik_chain, fk_chain, bind_chain, parts):
        for attr in [TRANSLATE, ROTATE, SCALE]:
            blend_node = cmds.createNode('blendColors',
                                         name=part + "_BCN")  # Blend Colors Node
            cmds.connectAttr(ik + "." + attr, blend_node + ".color1")
            cmds.connectAttr(fk + "." + attr, blend_node + ".color2")
            cmds.connectAttr(base_name + "_Control.iKfK",
                             blend_node + ".blender")
            cmds.connectAttr(blend_node + ".output", bind + "." + attr)


def create_fk_controls(fk_joints, axis='X', size=1):
    primary_axis = limb_utils.get_axis_vector(axis)
    idx = 0
    fk_controls = []
    for fk in fk_joints:
        # Create a circle
        circle_ctrl = cmds.circle(radius=size, normal=primary_axis, degree=3,
                                  name=fk.replace("_Joint", "_Control"))[0]
        # Parent control to the previous unless its the root
        if idx > 0:
            cmds.parent(circle_ctrl, fk_controls[idx-1])
        # Snap circles to the joint and point/orient constrain to joint
        ctrl_offset = limb_utils.align_lras(
            snap_align=True, sel=[circle_ctrl, fk])
        cmds.pointConstraint(circle_ctrl, fk)
        cmds.orientConstraint(circle_ctrl, fk)  # This line may need work?
        # cmds.connectAttr(circle_ctrl + '.rotate', fk + '.rotate')
        fk_controls.append(circle_ctrl)
        idx += 1
    return fk_controls


def create_ik_controls_and_handle(base_name, ik_joints, pole_vector, axis='X', size=1):
    # Create world control for wrist
    primary_axis = limb_utils.get_axis_vector(axis)
    world_ctrl = cmds.circle(radius=size*1.2, normal=primary_axis, degree=1, sections=4,
                             constructionHistory=False, name=base_name + "_IK_Control")[0]
    cmds.setAttr(world_ctrl + '.rotate' + axis[-1], 45)
    limb_utils.snap(world_ctrl, ik_joints[-1],
                    freeze_transform=True, rotate=False)

    # Create local control for wrist
    local_ctrl = cmds.circle(radius=size*1.2, normal=primary_axis, degree=1, sections=4,
                             constructionHistory=False, name=base_name + "Local_IK_Control")[0]
    cmds.setAttr(local_ctrl + '.rotate' + axis[-1], 45)
    local_off = limb_utils.align_lras(
        snap_align=True, sel=[local_ctrl, ik_joints[-1]])

    # Parent local to world
    cmds.parent(local_off, world_ctrl)

    # Create pole vector control
    pv_ctrl_points = [[0, 1, 0], [0, -1, 0], [0, 0, 0],
                      [-1, 0, 0], [1, 0, 0], [0, 0, 0],
                      [0, 0, -1], [0, 0, 1]]
    pv_ctrl = limb_utils.create_curve(
        pv_ctrl_points, name=base_name + "_PV_Control")
    cmds.setAttr(pv_ctrl + "." + SCALE, size * 0.25, size * 0.25, size * 0.25)
    limb_utils.snap(pv_ctrl, pole_vector, rotate=False, freeze_transform=True)

    # Create Base Control at shoulder
    base_ctrl = cmds.circle(radius=size*1.2, normal=primary_axis, degree=1, sections=4,
                            constructionHistory=False, name=base_name + "_Base_Control")[0]
    cmds.setAttr(base_ctrl + '.rotate' + axis[-1], 45)
    limb_utils.snap(base_ctrl, ik_joints[0],
                    rotate=False, freeze_transform=True)
    cmds.parentConstraint(base_ctrl, ik_joints[0], maintainOffset=True)

   # Create IK Handle
    ik_handle = cmds.ikHandle(name=base_name + "IK_Handle", startJoint=ik_joints[0],
                              endEffector=ik_joints[-1], sticky='sticky', solver='ikRPsolver',
                              setupForRPsolver=True)[0]
    cmds.parentConstraint(local_ctrl, ik_handle, maintainOffset=True)
    cmds.poleVectorConstraint(pv_ctrl, ik_handle)

    control_dict = {'base_ctrl': base_ctrl,
                    'world_ctrl': world_ctrl,
                    'local_ctrl': local_ctrl}
    return control_dict


def add_ik_stretch(base_name, limb, ik_joints, ik_base_ctrl, ik_world_ctrl, ik_local_ctrl, axis):
    up_name = "up" + limb.capitalize()
    lo_name = "lo" + limb.capitalize()
    # Add on/off control for stretch and limb lengths
    cmds.addAttr(ik_world_ctrl, attributeType='double', min=0, max=1,
                 defaultValue=1, keyable=True, longName='stretch')
    # Add lower and upper arm lengths
    cmds.addAttr(ik_world_ctrl, attributeType='double', min=0.001, defaultValue=1,
                 keyable=True, longName=up_name)
    cmds.addAttr(ik_world_ctrl, attributeType='double', min=0.001, defaultValue=1,
                 keyable=True, longName=lo_name)

    # Lengths of upper bone and lower bone
    upper_bone_length = limb_utils.distance(ik_joints[0], ik_joints[1])
    lower_bone_length = limb_utils.distance(ik_joints[1], ik_joints[2])
    total_bone_length = upper_bone_length + lower_bone_length

    # Create locators at the shoulder and the wrist
    start_loc = cmds.spaceLocator(name=base_name + "_startLocator")[0]
    end_loc = cmds.spaceLocator(name=base_name + "_endLocator")[0]
    cmds.pointConstraint(ik_base_ctrl, start_loc, maintainOffset=False)
    cmds.pointConstraint(ik_local_ctrl, end_loc, maintainOffset=False)

    # Create node that calculates distance between start and end
    distance_start_end = cmds.createNode(
        "distanceBetween", name=base_name + "_distanceBetween")
    cmds.connectAttr(
        start_loc + ".worldMatrix[0]", distance_start_end + ".inMatrix1")
    cmds.connectAttr(
        end_loc + ".worldMatrix[0]", distance_start_end + ".inMatrix2")

    # Calculate Stretch Ratio (distance to total bone length)
    stretch_ratio = cmds.createNode(
        "multiplyDivide", name=base_name + "_stretchFactor")
    cmds.connectAttr(distance_start_end + ".distance",
                     stretch_ratio + ".input1X")
    cmds.setAttr(stretch_ratio + ".input2X", total_bone_length)
    # To perform divison between input1X and input2X
    cmds.setAttr(stretch_ratio + ".operation", 2)

    # Condition node. If stretch ratio >= 1, perform a stretch
    stretch_cond = cmds.createNode(
        "condition", name=base_name + "_stretch_condition")
    cmds.connectAttr(distance_start_end + ".distance",
                     stretch_cond + '.firstTerm')
    cmds.connectAttr(stretch_ratio + ".outputX",
                     stretch_cond + ".colorIfTrueR")
    cmds.setAttr(stretch_cond + '.secondTerm', total_bone_length)
    # firstTerm > secondTerm, greater than operator
    cmds.setAttr(stretch_cond + '.operation', 3)

    # stretching on/off
    stretch_bta = cmds.createNode(
        'blendTwoAttr', name=base_name + "_stretch_BTA")
    cmds.setAttr(stretch_bta + ".input[0]", 1)
    cmds.connectAttr(stretch_cond + ".outColorR", stretch_bta + ".input[1]")
    cmds.connectAttr(ik_world_ctrl + ".stretch",
                     stretch_bta + ".attributesBlender")

    # Add length to upper/lower arms
    up_pma = cmds.createNode('plusMinusAverage', name=up_name + "PMA")
    lo_pma = cmds.createNode('plusMinusAverage', name=lo_name + "PMA")
    cmds.connectAttr(ik_world_ctrl + '.' + up_name, up_pma + ".input1D[0]")
    cmds.connectAttr(ik_world_ctrl + '.' + lo_name, lo_pma + ".input1D[0]")
    cmds.connectAttr(stretch_bta + '.output', up_pma + ".input1D[1]")
    cmds.connectAttr(stretch_bta + '.output', lo_pma + ".input1D[1]")
    cmds.setAttr(up_pma + '.input1D[2]', -1)
    cmds.setAttr(lo_pma + '.input1D[2]', -1)

    # Scale upper and lower limbs
    cmds.connectAttr(up_pma + '.output1D',
                     ik_joints[0] + '.' + SCALE + axis[-1])
    cmds.connectAttr(lo_pma + '.output1D',
                     ik_joints[1] + '.' + SCALE + axis[-1])

    control_dict = {'measure_locs': [start_loc, end_loc],
                    'total_length': total_bone_length,
                    'mdn': stretch_ratio,
                    'cnd': stretch_cond}
    return control_dict


def add_fk_stretch(fk_joints, fk_ctrls, axis):
    for i, fk_ctrl in enumerate(fk_ctrls):
        if i != len(fk_ctrls) - 1:
            # Add stretch attribute control on shoulder and elbow (but not wrist)
            cmds.addAttr(fk_ctrl, attributeType='double', min=0.001, defaultValue=1,
                         keyable=True, longName='stretch')
            cmds.createNode('multDoubleLinear',
                            name=fk_ctrl.replace("_Control", "_MDL"))
            # Create locator
            offset_loc = cmds.spaceLocator(
                name=fk_ctrl[i].replace('_Control', "_offLOC"))[0]
            # Parent to this joint
            cmds.parent(offset_loc, fk_joints[i])
            # Move locators to position elblow locator -> wrist, shoulder -> elbow
            limb_utils.snap(offset_loc, fk_joints[i+1])
            # make MDL to find stretch factor
            fk_stretch_mdl = cmds.createNode("multDoubleLinear",
                                             name=fk_ctrl.replace("_Control", "_FK_Stretch_MDL"))
            # Make input1 translate_x of offset locator
            offset_x = cmds.getAttr(
                offset_loc + '.' + TRANSLATE + axis[-1])
            cmds.setAttr(fk_stretch_mdl + ".input1", offset_x)
            # Make input2 the stretch factor from each joint's control
            cmds.connectAttr(fk_ctrl + ".stretch", fk_stretch_mdl + ".input2")
            # Add the output to the translate x of locator
            cmds.connectAttr(fk_stretch_mdl + ".output",
                             offset_loc + ".translate" + axis[-1])
            # Connect stretch attribute into bone scaling
            cmds.connectAttr(fk_ctrl + ".stretch",
                             fk_joints[i] + ".scale" + axis[-1])
            # Maya 2019 and above have offsetParentMatrix
            cmds.connectAttr(offset_loc + ".matrix",
                             fk_joints[i+1] + ".offsetParentMatrix")
