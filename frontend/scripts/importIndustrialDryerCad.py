"""Convert the licensed 3D Warehouse rotary-dryer Collada model to the runtime GLB.

Usage (Blender 4.x):
  blender --background --python importIndustrialDryerCad.py -- model.dae output.glb

The source DAE is intentionally not stored in this repository. The generated GLB is
an adapted, optimized part of the ProcessPilot combined work.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector


args = sys.argv[sys.argv.index("--") + 1 :]
if len(args) != 2:
    raise SystemExit("expected: model.dae output.glb")
source_path, output_path = map(Path, args)


GROUP_RULES = (
    ("feed_hopper", ("CAPOTA_ALIMENTACION", "SELLO_EN_ALIMENTACION")),
    ("product_outlet", ("CAPOTA_DESCARGA", "SELLO_EN_DESCARGA")),
    ("air_heater", ("DAMPER", "FILTRO_AIRE")),
    ("supply_fan", ("BCS_222", "DESCARGA_VENT_BCS222", "BASE_VENTI_BCS222")),
    ("exhaust_outlet", ("CICLON", "LS_2021", "CHIMENEA", "SALIDA_VENTILADOR", "BASE_VENTI_LS2021")),
    ("process_piping", ("DIVERTER", "PLENUM", "DUCTO", "CODO", "TRANSICION", "SOPORTE_DUCTO")),
    ("maintenance_platform", ("ESTRUCTURA", "BASES_Y_EDIFICIO", "COLUMNAS", "SOPORTE_VERTICAL", "BASE_ANTIVIBRATORIA")),
    ("dryer_drum", ("SHELL", "ROLDANAS", "SKF_SNH", "EJE_Y_PIÑON", "CATALINA", "LLANTA", "SOPORTE_LLANTA", "MOTOR_160M", "GUARDA_CATALINA")),
)


def source_instances(path: Path) -> dict[str, str]:
    root = ET.parse(path).getroot()
    namespace = {"c": root.tag.split("}")[0].strip("{")}
    library_names = {
        node.get("id"): node.get("name", "")
        for node in root.findall(".//c:library_nodes/c:node", namespace)
    }
    result = {}
    for node in root.findall(".//c:library_visual_scenes//c:node", namespace):
        instance = node.find("./c:instance_node", namespace)
        if instance is None:
            continue
        result[node.get("name", "")] = library_names.get(instance.get("url", "").lstrip("#"), "")
    return result


def semantic_group(component_name: str) -> str:
    normalized = component_name.upper()
    for group, patterns in GROUP_RULES:
        if any(pattern in normalized for pattern in patterns):
            return group
    return "maintenance_platform"


def bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return low, high


def join_group(group_name: str, objects: list[bpy.types.Object]) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    merged = bpy.context.object
    merged.name = group_name
    merged.data.name = f"{group_name}_geometry"
    merged["semantic_node"] = group_name
    merged["source_components"] = len(objects)
    return merged


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.collada_import(filepath=str(source_path))

instance_map = source_instances(source_path)
grouped = defaultdict(list)
component_counts = defaultdict(int)
for obj in list(bpy.data.objects):
    if obj.type != "MESH":
        continue
    # Collada stores assembly placement on parent nodes. Detach without changing
    # the world matrix before hierarchy cleanup, otherwise the plant collapses
    # into the component-local coordinate systems.
    world_matrix = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world_matrix
    base_name = re.sub(r"\.\d{3}$", "", obj.name)
    component = instance_map.get(base_name, "")
    group = semantic_group(component)
    grouped[group].append(obj)
    component_counts[component or "unclassified"] += 1

merged = []
for group_name, _patterns in GROUP_RULES:
    objects = grouped.get(group_name, [])
    if objects:
        merged.append(join_group(group_name, objects))

for obj in list(bpy.data.objects):
    if obj.type != "MESH":
        bpy.data.objects.remove(obj, do_unlink=True)

if not merged:
    raise RuntimeError("Collada import produced no semantic meshes")

# Normalize the plant to a predictable runtime footprint while preserving proportions.
low, high = bounds(merged)
size = high - low
center = (low + high) * 0.5
scale = 31.0 / max(size)
for obj in merged:
    obj.location = (obj.location - center) * scale
    obj.scale *= scale
bpy.context.view_layer.update()

# Put the lowest point on the floor and center the horizontal footprint.
low, high = bounds(merged)
for obj in merged:
    obj.location.x -= (low.x + high.x) * 0.5
    obj.location.y -= (low.y + high.y) * 0.5
    obj.location.z -= low.z

for material in bpy.data.materials:
    material.use_nodes = True
    material.diffuse_color[3] = 1.0
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if not bsdf:
        continue
    bsdf.inputs["Roughness"].default_value = 0.58
    bsdf.inputs["Metallic"].default_value = 0.32
    bsdf.inputs["IOR"].default_value = 1.5

root = bpy.data.objects.new("industrial_dryer_cad", None)
bpy.context.collection.objects.link(root)
root["source_title"] = "Industrial Rotary Dryer"
root["source_author"] = "Alibre Design"
root["source_url"] = "https://3dwarehouse.sketchup.com/model/ec181059cdc3036a5970eada872fb5c/Industrial-Rotary-Dryer"
root["source_license"] = "3D Warehouse General Model License; incorporated into a Combined Work"
root["adaptation"] = "semantic regrouping, material normalization, coordinate normalization, Draco compression"
for obj in merged:
    obj.parent = root

manifest = {
    "source_meshes": sum(component_counts.values()),
    "runtime_meshes": len(merged),
    "semantic_nodes": [obj.name for obj in merged],
    "source_components": dict(sorted(component_counts.items())),
}
root["conversion_manifest"] = json.dumps(manifest, ensure_ascii=False)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=str(output_path),
    export_format="GLB",
    use_selection=True,
    export_extras=True,
    export_yup=True,
    export_apply=True,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
    export_draco_position_quantization=14,
    export_draco_normal_quantization=10,
)
print("A14_CAD_CONVERSION", json.dumps(manifest, ensure_ascii=False))
