"""Rebuild derived meshes from the included Anvil STEP sources (millimetres)."""
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from maddie_dim.config import ROOT

folder=ROOT/'assets/vendor/anvil-gripper'
(folder/'stl').mkdir(exist_ok=True)
for name in ['gripper_base','wide-tip flange_left','wide-tip flange_right']:
    reader=STEPControl_Reader()
    reader.ReadFile(str(folder/(name+'.stp')))
    reader.TransferRoots()
    shape=reader.OneShape()
    BRepMesh_IncrementalMesh(shape,.1,False,.3,True).Perform()
    writer=StlAPI_Writer();writer.ASCIIMode=False
    writer.Write(shape,str(folder/'stl'/(name+'.stl')))
