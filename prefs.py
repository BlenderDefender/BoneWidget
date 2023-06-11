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
from bpy.types import AddonPreferences
from bpy.props import StringProperty

from .bl_class_registry import BlClassRegistry
from .panels import BONEWIDGET_PT_posemode_panel


@BlClassRegistry()
class BONEWIDGET_APT_Preferences(AddonPreferences):
    bl_idname = __package__

    # widget prefix
    widget_prefix: StringProperty(
        name="Bone Widget prefix",
        description="Choose a prefix for the widget objects",
        default="WGT-",
    )

    # symmetry suffix
    symmetry_suffix: StringProperty(
        name="Bone Widget symmetry suffix",
        description="Choose a naming convention for the symmetrical widgets, seperate by semicolon.",
        default="L; R",
    )

    # collection name
    bonewidget_collection_name: StringProperty(
        name="Bone Widget collection name",
        description="Choose a name for the collection the widgets will appear",
        default="WGTS",
    )

    def panel_category_update_fn(self, context):
        has_panel = hasattr(bpy.types, BONEWIDGET_PT_posemode_panel.bl_idname)
        if has_panel:
            try:
                bpy.utils.unregister_class(BONEWIDGET_PT_posemode_panel)
            except:
                pass
        BONEWIDGET_PT_posemode_panel.bl_category = self.panel_category
        bpy.utils.register_class(BONEWIDGET_PT_posemode_panel)

    panel_category: bpy.props.StringProperty(
        name="Panel Category",
        description="Category to show Bone-Widgets panel",
        default="Rig Tools",
        update=panel_category_update_fn,
    )

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        col = row.column()
        col.prop(self, "widget_prefix", text="Widget Prefix")
        col.prop(self, "bonewidget_collection_name", text="Collection name")

        row = layout.row()
        row = layout.row()
        row.prop(self, "symmetry_suffix", text="Symmetry suffix")

        row = layout.row()

        row = layout.row()
        col = row.column()
        col.label(text="Set the category to show Bone-Widgets panel:")
        col.prop(self, "panel_category")
