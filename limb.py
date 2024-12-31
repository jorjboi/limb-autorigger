import maya.cmds as cmds
import maya.mel as mel
import lrig.limb_utils as limb_utils

arm_aliases = {'LeftShoulder':'Shoulder',
               'LeftElbow':'Elbow',
               'LeftWrist':'Wrist'}

def create_limb(side='L', limb = 'arm',
                joints = ['LeftShoulder', 'LeftElbow', 'LeftWrist'],
                aliases = arm_aliases, pole_vector = 'LeftShoulder_PV', 
                primary_axis='X', up_axis= 'Y',
                del_guides=False, stretch=False, color_dict={}):
   
   # Checks
    if side not in ['L', 'R']:
        cmds.error("Must specify L (left) or R (right) for side")
    if limb not in ['arm', 'leg']:
         cmds.error("Must specify arm or leg for limb")
    if len(joints) != 3 or len(aliases) != 3:
        cmds.error("Must create 3 joints for a limb")

    limb_name = side + "_" + limb

    ik_chain = create_chain(side, joints, aliases, 'IK')
    fk_chain = create_chain(side, joints, aliases, 'FK')
    bind_chain = create_chain(side, joints, aliases, 'Bind')

    # Find a good size for the control based on model size
    arm_len = limb_utils.distance(fk_chain[0], fk_chain[-1])
    size = arm_len/5.0
    create_plus_control(size, up_axis, bind_chain[-1])



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
        limb_utils.snap(j, joint, freeze_transform=True)
        chain.append(joint)
    return chain

def create_plus_control(size, up_axis='Y', bind_joint='LeftWrist_Bind_Joint'):
    plus_shape_coords = [[-1/3, 1/3, 0],
                     [-1/3, 1, 0],
                     [1/3, 1, 0], 
                     [1/3, 1/3, 0],
                     [1, 1/3, 0],
                     [1, -1/3, 0],
                     [1/3, -1/3, 0],
                     [1/3, -1, 0]
                     [-1/3, -1, 0],
                     [-1/3, -1/3, 0],
                     [-1, -1/3, 0],
                     [-1, 1/3, 0],
                     [-1/3, 1/3, 0]]
    plus_control_curve = limb_utils.create_curve(plus_shape_coords, "_Control")
    cmds.setAttr(plus_control_curve + '.scale', 
                 size * 0.25, 
                 size * 0.25,
                 size * 0.25)
    # Offset it from the model
    offset = size * 1.5
    if up_axis[0] == '-':
        offset *= - 1
    cmds.setAttr(plus_control_curve + ".translate" + up_axis[-1], offset)

    # Freeze transformation
    cmds.makeIdentity(plus_control_curve, apply=True, normal=False)

    # Parent constrain to wrist
    limb_utils.align_lras(snap_align=False, delete_history=True, sel=None)
    cmds.parentConstraint(bind_joint, plus_control_curve, maintainOffset=True)

    # Add IK/FK switching 
    cmds.addAttr(plus_control_curve, attributeType='float', min=0, max=1.0, defaultValue=1.0,
                 keyable=True, longName='FK/IK')
    
                 

    

# testing
#create_limb()