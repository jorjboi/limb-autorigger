import maya.cmds as cmds
import maya.mel as mel
import limb_utils as limb_utils

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

    print(ik_chain, fk_chain, bind_chain)

# Returns a list of joints for an IK, FK, or bind chain
def create_chain(side, joints, aliases, chain_type='IK'):
    chain = []
    for j in joints:
        if joints.index(j) == 0: # Root joint, no parent
            joint = cmds.joint(None, name='{}{}_{}_Joint'.format(side, aliases[j], chain_type))
        else:
            idx = joints.index(j)
            joint = cmds.joint(chain[idx-1], name='{}{}_{}_Joint'.format(side, aliases[j], chain_type))
        limb_utils.snap(j, joint, freeze_transform=True)
        chain.append(joint)
    return chain


