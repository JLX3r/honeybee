# By Mostapha Sadeghipour Roudsari
# Sadeghipour@gmail.com
# Honeybee started by Mostapha Sadeghipour Roudsari is licensed
# under a Creative Commons Attribution-ShareAlike 3.0 Unported License.

"""
Change Honeybee Object Names

-
Provided by Honeybee 0.0.53

    Args:
        HBObjects: Any valid Honeybee object
        _names: List of new names for HBObjects
    Returns:
        readMe!: Information about the Honeybee object
"""
ghenv.Component.Name = "Honeybee_ChangeHBObjName"
ghenv.Component.NickName = 'changeHBObjName'
ghenv.Component.Message = 'VER 0.0.53\nJUL_04_2014'
ghenv.Component.Category = "Honeybee"
ghenv.Component.SubCategory = "00 | Honeybee"
try: ghenv.Component.AdditionalHelpFromDocStrings = "0"
except: pass


import scriptcontext as sc
import Grasshopper.Kernel as gh
import uuid

def main(HBObjects, names):
    # check for Honeybee
    if not sc.sticky.has_key('honeybee_release'):
        msg = "You should first let Honeybee fly..."
        ghenv.Component.AddRuntimeMessage(gh.GH_RuntimeMessageLevel.Warning, msg)
        return
    
    # call the objects from the lib
    hb_hive = sc.sticky["honeybee_Hive"]()
    HBObjectsFromHive = hb_hive.callFromHoneybeeHive(HBObjects)
    
    HBObjs = range(len(HBObjectsFromHive))
    
    for count, HBO in enumerate(HBObjectsFromHive):
        try:
            HBO.setName(names[count])
        except:
            pass
        
        HBObjs[count] = HBO
    
    return hb_hive.addToHoneybeeHive(HBObjs, ghenv.Component.InstanceGuid.ToString() + str(uuid.uuid4()))

if _HBObjects and _names:
    HBObjects = main(_HBObjects, _names)