"""Deterministic URDF-to-MJCF conversion of DimOS's hardware gravity model.

The upstream planning model has different kinematics. We deliberately preserve
this model's frames, axes, mass and inertia, and expose its provenance.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image
from .config import ROOT, config
from .frame import RIGHT, DOWN


def numbers(v):
    return " ".join(f"{float(x):.10g}" for x in v)


def origin(element):
    el = element.find("origin")
    if el is None:
        return {"pos": "0 0 0", "quat": "1 0 0 0"}
    r = Rotation.from_euler(
        "xyz", np.fromstring(el.get("rpy", "0 0 0"), sep=" ")
    ).as_quat()
    return {"pos": el.get("xyz", "0 0 0"), "quat": numbers(r[[3, 0, 1, 2]])}


def build_scene(c=None) -> Path:
    c = c or config()
    folder = ROOT / "assets/generated"
    folder.mkdir(parents=True, exist_ok=True)
    src = ROOT / "assets/vendor/yam_description"
    robot = ET.parse(src / "urdf/yam_gripper_gravity.urdf").getroot()
    root = ET.Element("mujoco", model="maddie_dim_openyam_provisional")
    ET.SubElement(
        root, "compiler", angle="radian", autolimits="true", inertiafromgeom="false"
    )
    ET.SubElement(
        root,
        "option",
        timestep=str(c["physics_dt_s"]),
        integrator="implicitfast",
        gravity="0 0 -9.81",
        iterations="80",
        tolerance="1e-10",
    )
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "global", offwidth="1200", offheight="1400")
    ET.SubElement(vis, "headlight", ambient="0.4 0.4 0.4", diffuse="0.7 0.7 0.7")
    default = ET.SubElement(root, "default")
    ET.SubElement(
        default,
        "geom",
        solref="0.004 1",
        solimp="0.99 0.999 0.001",
        friction=f"{c['paper_friction']} 0.005 0.0001",
        condim="3",
    )
    assets = ET.SubElement(root, "asset")
    Image.new("RGB", (840, 1188), "white").save(folder / "blank.png")
    ET.SubElement(
        assets, "texture", name="paint", type="2d", file=str(folder / "blank.png")
    )
    ET.SubElement(
        assets,
        "material",
        name="paper_material",
        texture="paint",
        texuniform="false",
        specular="0",
        reflectance="0",
    )
    w, h = np.array(c["paper_mm"]) / 2000
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(
        world,
        "light",
        pos="0.2 -0.3 1.5",
        dir="0 0 -1",
        diffuse="0.85 0.85 0.85",
        castshadow="true",
    )
    ET.SubElement(
        world,
        "geom",
        name="table",
        type="box",
        pos="0.3 0 -0.021",
        size="0.65 0.5 0.02",
        rgba="0.36 0.32 0.28 1",
    )
    center = np.array(c["paper_center_m"])
    ET.SubElement(
        world,
        "geom",
        name="paper",
        type="box",
        pos=numbers(center - [0, 0, 0.0002]),
        size=numbers([w, h, 0.0002]),
        quat="0.7071067812 0 0 -0.7071067812",
        rgba="1 1 1 1",
    )
    world.find("geom[@name='paper']").set("material", "paper_material")
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            ET.SubElement(
                world,
                "geom",
                name=f"tape_{sx}_{sy}",
                type="box",
                pos=numbers(
                    center
                    + RIGHT * sx * w
                    - DOWN * sy * (h - 0.015)
                    + np.array([0, 0, 0.00005])
                ),
                size="0.02 0.009 0.00006",
                quat="0.7071067812 0 0 -0.7071067812",
                rgba="0.82 0.74 0.5 1",
                contype="0",
                conaffinity="0",
            )
    ET.SubElement(
        world,
        "camera",
        name="overhead",
        pos=numbers(center + [0, 0, 0.60]),
        quat="0.7071067812 0 0 -0.7071067812",
        fovy=str(c["camera_fovy_deg"]),
    )
    ET.SubElement(
        world,
        "camera",
        name="overview",
        pos="0.9 -0.95 0.85",
        xyaxes="0.846 0.534 0 -0.286 0.453 0.844",
        fovy="45",
    )
    links = {l.get("name"): l for l in robot.findall("link")}
    joints = {j.find("child").get("link"): j for j in robot.findall("joint")}
    bodies = {}
    for name in ["yam_base_link"] + [f"yam_link_{i}" for i in range(1, 7)]:
        link = links[name]
        j = joints.get(name)
        par = world if j is None else bodies[j.find("parent").get("link")]
        body = ET.SubElement(
            par, "body", name=name, **({"pos": "0 0 0"} if j is None else origin(j))
        )
        bodies[name] = body
        inertia = link.find("inertial")
        if inertia is not None:
            tensor = inertia.find("inertia")
            mat = np.array(
                [
                    [float(tensor.get(k)) for k in row]
                    for row in [
                        ("ixx", "ixy", "ixz"),
                        ("ixy", "iyy", "iyz"),
                        ("ixz", "iyz", "izz"),
                    ]
                ]
            )
            io = origin(inertia)
            quat = np.fromstring(io.pop("quat"), sep=" ")
            r = Rotation.from_quat(quat[[1, 2, 3, 0]]).as_matrix()
            mat = r @ mat @ r.T
            ET.SubElement(
                body,
                "inertial",
                mass=inertia.find("mass").get("value"),
                fullinertia=numbers(
                    [mat[0, 0], mat[1, 1], mat[2, 2], mat[0, 1], mat[0, 2], mat[1, 2]]
                ),
                **io,
            )
        if j is not None:
            limit = j.find("limit")
            ET.SubElement(
                body,
                "joint",
                name=j.get("name"),
                type="hinge",
                axis=j.find("axis").get("xyz"),
                range=f"{limit.get('lower')} {limit.get('upper')}",
                damping="0.02",
                frictionloss="0.003",
                armature="0.01",
            )
        for kind in ["visual", "collision"]:
            for i, g in enumerate(link.findall(kind)):
                geo = g.find("geometry")
                args = origin(g)
                mesh = geo.find("mesh")
                if mesh is not None:
                    path = (
                        src
                        / mesh.get("filename").split("package://yam_description/")[1]
                    )
                    mn = f"{name}_{kind}_{i}"
                    ET.SubElement(assets, "mesh", name=mn, file=str(path))
                    args.update(type="mesh", mesh=mn)
                elif geo.find("cylinder") is not None:
                    cy = geo.find("cylinder")
                    args.update(
                        type="cylinder",
                        size=f"{cy.get('radius')} {float(cy.get('length')) / 2}",
                    )
                else:
                    continue
                args.update(
                    name=f"{name}_{kind}_{i}",
                    group="1" if kind == "visual" else "3",
                    contype="0" if kind == "visual" else "1",
                    conaffinity="0" if kind == "visual" else "1",
                    rgba="0.72 0.31 0.09 1" if kind == "visual" else "0.5 0.5 0.5 0",
                )
                ET.SubElement(body, "geom", **args)
    hand = ET.SubElement(
        bodies["yam_link_6"], "body", name="anvil_gripper", pos="0 0 0.05"
    )
    # Manufacturer's total with-gripper mass increment is 0.7 kg. Inertials
    # are already lumped into the upstream wrist; no duplicate mass is added.
    cad = ROOT / "assets/vendor/anvil-gripper/stl"
    for name, offset in [
        ("gripper_base", 0),
        ("wide-tip flange_left", 0.009),
        ("wide-tip flange_right", -0.009),
    ]:
        mn = name.replace(" ", "_")
        ET.SubElement(
            assets,
            "mesh",
            name=mn,
            file=str(cad / (name + ".stl")),
            scale="0.001 0.001 0.001",
        )
        ET.SubElement(
            hand,
            "geom",
            name=mn,
            type="mesh",
            mesh=mn,
            quat="0 1 0 0",
            pos=f"0 {-offset} 0",
            rgba="0.16 0.17 0.19 1",
        )
    pen = ET.SubElement(
        bodies["yam_link_6"],
        "body",
        name="pen",
        pos=f"0 0 {c['tip_from_wrist_m'] - 0.001}",
    )
    ET.SubElement(
        pen,
        "inertial",
        pos="0 0 -0.065",
        mass=str(c["pen_mass_kg"]),
        diaginertia="0.000017 0.000017 0.00000015",
    )
    ET.SubElement(
        pen,
        "geom",
        name="barrel",
        type="cylinder",
        pos="0 0 -0.065",
        size=f"{c['pen_radius_m']} {c['pen_length_m'] / 2 - 0.002}",
        rgba="0.08 0.08 0.09 1",
    )
    nib = ET.SubElement(pen, "body", name="nib", pos="0 0 0")
    ET.SubElement(
        nib,
        "joint",
        name="nib_compression",
        type="slide",
        axis="0 0 -1",
        range="0 0.0015",
        stiffness=str(c["nib_stiffness_N_m"]),
        damping=str(c["nib_damping_N_s_m"]),
        armature="0.0001",
    )
    ET.SubElement(
        nib, "inertial", pos="0 0 0", mass="0.0005", diaginertia="1e-9 1e-9 1e-9"
    )
    ET.SubElement(
        nib,
        "geom",
        name="nib_contact",
        type="sphere",
        size="0.00035",
        pos="0 0 0.00065",
        rgba="0.015 0.015 0.015 1",
    )
    ET.SubElement(
        nib, "site", name="tip", pos="0 0 0.001", size="0.001", rgba="0 0 0 0"
    )
    contact = ET.SubElement(root, "contact")
    ET.SubElement(contact, "exclude", body1="yam_base_link", body2="yam_link_1")
    ET.SubElement(contact, "exclude", body1="yam_link_6", body2="anvil_gripper")
    ET.SubElement(contact, "exclude", body1="anvil_gripper", body2="pen")
    actuator = ET.SubElement(root, "actuator")
    for i in range(1, 7):
        ET.SubElement(
            actuator,
            "motor",
            name=f"motor{i}",
            joint=f"yam_joint{i}",
            ctrllimited="true",
            ctrlrange="-10 10",
        )
    path = folder / "scene.xml"
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="unicode")
    return path
