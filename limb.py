import maya.cmds as cmds
import maya.mel as mel
import lrig.limb_utils as limb_utils
import importlib

importlib.reload(limb_utils)

TRANSLATE = "translate"
ROTATE = "rotate"
SCALE = "scale"
LEFT_SHOULDER = "LeftShoulder" # "L_shoulder_JNT"
LEFT_ELBOW = "LeftElbow" # "L_elbow_JNT"
LEFT_WRIST = "LeftWrist" #"L_wrist_JNT"
LEFT_POLE_VECTOR = "LeftShoulder_PV"

arm_aliases = {LEFT_SHOULDER:'Shoulder',
               LEFT_ELBOW:'Elbow',
               LEFT_WRIST:'Wrist'}

def create_limb(side='L', limb = 'arm',
                joints = [LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST],
                aliases = arm_aliases, pole_vector = LEFT_POLE_VECTOR, 
                primary_axis='X', up_axis= 'Y',
                del_guides=False, stretch=False, color_dict={}):
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

    ik_chain = create_chain(side, joints, aliases, 'IK')
    fk_chain = create_chain(side, joints, aliases, 'FK')
    bind_chain = create_chain(side, joints, aliases, 'Bind')

    # Find and create a good size for the control based on model size
    arm_len = limb_utils.distance(fk_chain[0], fk_chain[-1])
    size = arm_len/5.0
    create_plus_control(size, up_axis, bind_chain[-1], base_name)

    # Blend IK/FK with blend color nodes to create bind limb
    blend_ik_fk(ik_chain, fk_chain, bind_chain, base_name)

# Returns a list of joints for an IK, FK, or bind chain
def create_chain(side, joints, aliases, chain_type='IK'):
    side_prefix = "Left" if side == "L" else "Right"
    chain = []
    for j in joints:
        if joints.index(j) == 0: # Root joint, no parent
            joint = cmds.joint(None, name='{}{}_{}_Joint'.format(side_prefix, aliases[j], chain_type))
        else:
            idx = joints.index(j)
            joint = cmds.joint(chain[idx-1], name='{}{}_{}_Joint'.format(side_prefix, aliases[j], chain_type))
        limb_utils.snap(joint, j, freeze_transform=True)
        chain.append(joint)
    return chain

def create_plus_control(size, up_axis='Y', bind_joint='LeftWrist_Bind_Joint', base_name=""):
    plus_shape_coords = [[-0.333, 0.333, 0.0], [-0.333, 1.0, 0.0],
                        [0.333, 1.0, 0.0], [0.333, 0.333, 0.0],
                        [1.0, 0.333, 0.0], [1.0, -0.333, 0.0],
                        [0.333, -0.333, 0.0], [0.333, -1.0, 0.0],
                        [-0.333, -1.0, 0.0], [-0.333, -0.333, 0.0],
                        [-1.0, -0.333, 0.0], [-1.0, 0.333, 0.0],
                        [-0.333, 0.333, 0.0]]
    plus_control_curve = limb_utils.create_curve(plus_shape_coords, base_name + "_Control")
    limb_utils.align_lras(snap_align=True, sel=[plus_control_curve, bind_joint])

    cmds.setAttr(plus_control_curve + '.' + SCALE, 
                 size * 0.25,
                 size * 0.25,
                 size * 0.25)
    # Offset it from the model
    offset = size * 1.5
    if up_axis[0] == '-':
        offset *= - 1
    cmds.setAttr(plus_control_curve + "." + TRANSLATE + up_axis[-1], offset)

    # Freeze transformation
    cmds.makeIdentity(plus_control_curve, apply=True, normal=False)

    # Parent constrain to wrist of our bind joint
    cmds.parentConstraint(bind_joint, plus_control_curve, maintainOffset=True)
    # Add IK/FK switching 
    cmds.addAttr(plus_control_curve, attributeType='double', min=0, max=1, defaultValue=1,
                 keyable=True, longName='iKfK')
    
                 
def blend_ik_fk(ik_chain, fk_chain, bind_chain, base_name):
    parts = [b.replace("_Bind_Joint", '') for b in bind_chain]
    for ik, fk, bind, part in zip(ik_chain, fk_chain, bind_chain, parts):
        for attr in [TRANSLATE, ROTATE, SCALE]:
            blend_node = cmds.createNode('blendColors', 
                                         name = part + "_BCN") # Blend Colors Node
            cmds.connectAttr(ik + "." + attr, blend_node + ".color1")
            cmds.connectAttr(fk + "." + attr, blend_node + ".color2")
            cmds.connectAttr(base_name + "_Control.iKfK", blend_node + ".blender")
            cmds.connectAttr(blend_node + ".output", bind + "." + attr)




    

# testing
#create_limb()