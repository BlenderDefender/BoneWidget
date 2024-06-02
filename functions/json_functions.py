# ##### BEGIN GPL LICENSE BLOCK #####
#
# Copyright (C) 2020 Manuel Rais
# manu@g-lul.com

# Created by Manuel Rais and Christophe Seux

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy.types import (
    Context,
    Mesh,
    Object,
)

import os
from os import path as p

import json

import numpy


from .. import (
    __package__
)


def object_data_to_dico(context: 'Context', object: 'Object') -> dict:
    """Convert an object to JSON data.

    Args:
        context (Context): The current Blender context.
        object (Object): The object that should be converted to JSON data.

    Returns:
        dict: The JSON representation of the object in the following format: `{ "vertices": [], "edges": [], "faces": [] }`
    """

    verts: list = []

    depsgraph = context.evaluated_depsgraph_get()
    mesh: 'Mesh' = object.evaluated_get(depsgraph).to_mesh()
    for v in mesh.vertices:
        verts.append(list(numpy.array(tuple(v.co)) *
                           (object.scale[0], object.scale[1], object.scale[2])))

    polygons: list = []
    for pol in mesh.polygons:
        polygons.append(list(pol.vertices))

    edges: list = []

    for e in mesh.edges:
        if len(polygons) == 0:
            edges.append(list(e.key))
            continue

        for vert_indices in polygons:
            if e.key[0] and e.key[1] not in vert_indices:
                edges.append(list(e.key))

    wgts: dict = {"vertices": verts, "edges": edges, "faces": polygons}
    # print(wgts)
    return wgts


def read_widgets() -> dict:
    """Read the widgets file and return the JSON data.

    Returns:
        dict: The JSON data dictionary.
    """

    json_file = p.join(p.dirname(
        p.dirname(__file__)), 'widgets.json')

    if not p.exists(json_file):
        return {}

    with open(json_file, "r", encoding="utf-8") as f:
        wgts: dict = json.load(f)

    return wgts


def write_widgets(wgts: dict) -> None:
    """Write to the widgets file.

    Args:
        wgts (dict): The updated widgets object.
    """

    json_file = p.join(p.dirname(
        p.dirname(__file__)), 'widgets.json')

    if not p.exists(json_file):
        return

    with open(json_file, "w+", encoding="utf-8") as f:
        json.dump(wgts, f)
