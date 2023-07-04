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

import typing

import numpy


from .. import __package__
from ..prefs import BONEWIDGET_APT_Preferences as Preferences


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
        verts.append(tuple(numpy.array(tuple(v.co)) *
                           (object.scale[0], object.scale[1], object.scale[2])))

    polygons: list = []
    for pol in mesh.polygons:
        polygons.append(tuple(pol.vertices))

    edges: list = []

    for e in mesh.edges:
        if len(polygons) == 0:
            edges.append(e.key)
            continue

        for vert_indices in polygons:
            if e.key[0] and e.key[1] not in vert_indices:
                edges.append(e.key)

    wgts: dict = { "vertices": verts, "edges": edges, "faces": polygons }
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

    with open(json_file, 'r') as f:
        wgts = json.load(f)

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

    f = open(json_file, 'w')
    f.write(json.dumps(wgts))
    f.close()


def add_remove_widgets(context: 'Context', add_or_remove: str, items: typing.List[typing.Tuple[str]], widgets: typing.Union[str, typing.List['Object']]) -> str:
    """Add or remove a widget to the widgets file.

    Args:
        context (Context): The current Blender context
        add_or_remove (str): Whether to add or to remove the widget.
        items (typing.List[typing.Tuple[str]]): The List of Enum Items (for the UI EnumProperty)
        widgets (typing.Union[str, typing.List['Object']]): The list of widget objects if add, else the name of the widget that should be removed.

    Returns:
        str: Message of the return status.
    """

    wgts: dict = read_widgets()
    prefs: 'Preferences' = context.preferences.addons[__package__].preferences

    widget_items: list = []
    for widget_item in items:
        widget_items.append(widget_item[1])

    active_shape: str = None
    ob_name: str = None

    if add_or_remove == 'add':
        bw_widget_prefix = prefs.widget_prefix
        for ob in widgets:
            ob_name = ob.name.removeprefix(bw_widget_prefix)

            if ob_name in widget_items:
                continue

            widget_items.append(ob_name)
            wgts[ob_name] = object_data_to_dico(context, ob)
            active_shape = ob_name

    elif add_or_remove == 'remove':
        del wgts[widgets]
        widget_items.remove(widgets)
        active_shape = widget_items[0]

    if active_shape is not None:
        del bpy.types.Scene.widget_list

        widget_items_sorted: list = []
        for w in sorted(widget_items):
            widget_items_sorted.append((w, w, ""))

        bpy.types.Scene.widget_list = bpy.props.EnumProperty(
            items=widget_items_sorted, name="Shape", description="Shape")
        context.scene.widget_list = active_shape
        write_widgets(wgts)
        return ""

    if ob_name is not None:
        return "Widget - " + ob_name + " already exists!"

    return ""
