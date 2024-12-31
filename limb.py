import maya.cmds as cmds
import maya.mel as mel
import limb_utils as limb_utils

arm_aliases = {'LeftShoulder':'shoulder',
               'LeftElbow':'elbow',
               'LeftWrist':'wrist'}

def create_limb(side='L', limb = 'arm',
                parts = ['LeftShoulder', 'LeftElbow', 'LeftWrist'],
                aliases = arm_aliases, pole_vector = 'LeftShoulder_PV', 
                primary_axis='X', up_axis= 'Y',
                del_guides=False, stretch=False, color_dict={}):
   
   # Checks
    if side not in ['L', 'R']:
        cmds.error("Must specify L (left) or R (right) for side")
    if limb not in ['arm', 'leg']:
         cmds.error("Must specify arm or leg for limb")
    if len(parts) != 3 or len(aliases) != 3:
        cmds.error("Must create 3 joints for a limb")

    limb_name = side + "_" + limb 

    ik_chain = []
    fk_chain = []
    bind_chain = []

    return [ik_chain, fk_chain, bind_chain]

