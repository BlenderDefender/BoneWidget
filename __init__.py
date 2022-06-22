# ##### BEGIN GPL LICENSE BLOCK #####
#
# Copyright (C) 2020 Manuel Rais
# manu@g-lul.com
#
# Created by Manuel Rais and Christophe Seux
#
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

import os

from . import bl_class_registry
from . import operators
from . import panels
from . import prefs
from . import menus

bl_info = {
    "name": "Bone Widget",
    "author": "Blender Defender, Manuel Rais, Christophe Seux, Bassam Kurdali, Wayne Dixon, Max Nadolny",
    "version": (1, 9, 0),
    "blender": (2, 93, 0),
    "location": "UI > Properties Panel",
    "description": "Easily Create Bone Widgets",
    "warning": "",
    "doc_url": "https://github.com/BlenderDefender/boneWidget#description",
    "tracker_url": "https://github.com/BlenderDefender/boneWidget/issues",
    "endpoint_url": "https://raw.githubusercontent.com/BlenderDefender/BlenderDefender/updater_endpoints/BONEWIDGET.json",
    "category": "Rigging"
}


def get_user_preferences(context):
    if hasattr(context, "user_preferences"):
        return context.user_preferences

    return context.preferences


def check_version(major, minor, _):
    """
    Check blender version
    """

    if bpy.app.version[0] == major and bpy.app.version[1] == minor:
        return 0
    if bpy.app.version[0] > major:
        return 1
    if bpy.app.version[1] > minor:
        return 1
    return -1


def register():
    operators.register()
    menus.register()
    bl_class_registry.BlClassRegistry.register()

    # Apply preferences of the panel location.
    context = bpy.context
    pref = get_user_preferences(context).addons[__package__].preferences
    # Only default panel location is available in < 2.80
    if check_version(2, 80, 0) < 0:
        pref.panel_category = "Rig Tools"
    prefs.BoneWidgetPreferences.panel_category_update_fn(pref, context)


def unregister():
    operators.unregister()
    menus.unregister()
    # TODO: Unregister by BlClassRegistry
    bl_class_registry.BlClassRegistry.unregister()


if __name__ == "__main__":
    register()
