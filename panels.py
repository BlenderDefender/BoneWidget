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
    Panel,
    UILayout
)
from bpy.props import (EnumProperty)

from .bl_class_registry import BlClassRegistry
from .functions import (
    read_widgets,
    recur_layer_collection,
)


@BlClassRegistry()
class BONEWIDGET_PT_posemode_panel(Panel):
    bl_label = "Bone Widget"
    bl_category = "Rig Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_idname = 'VIEW3D_PT_bw_posemode_panel'

    items: list = []
    for key, value in read_widgets().items():
        items.append(key)

    items_sort: list = []
    for key in sorted(items):
        items_sort.append((key, key, ""))

    bpy.types.Scene.widget_list = EnumProperty(
        items=items_sort, name="Shape", description="Shape")

    def draw(self, context: 'Context'):
        layout: 'UILayout' = self.layout

        row = layout.row(align=True)
        row.prop(context.scene, "widget_list", expand=False, text="")

        row = layout.row(align=True)
        row.menu("BONEWIDGET_MT_bw_specials", icon='DOWNARROW_HLT', text="")
        row.operator("bonewidget.create_widget", icon="OBJECT_DATAMODE")

        if bpy.context.mode == "POSE":
            row.operator("bonewidget.edit_widget", icon="OUTLINER_DATA_MESH")
        else:
            row.operator("bonewidget.return_to_armature",
                         icon="LOOP_BACK", text='To bone')

        layout.separator()
        layout.operator("bonewidget.symmetrize_shape",
                        icon='MOD_MIRROR', text="Symmetrize Shape")
        layout.operator("bonewidget.match_bone_transforms",
                        icon='GROUP_BONE', text="Match Bone Transforms")
        layout.operator("bonewidget.resync_widget_names",
                        icon='FILE_REFRESH', text="Resync Widget Names")
        layout.separator()
        layout.operator("bonewidget.clear_widgets",
                        icon='X', text="Clear Bone Widget")
        layout.operator("bonewidget.delete_unused_widgets",
                        icon='TRASH', text="Delete Unused Widgets")

        if bpy.context.mode == 'POSE':
            layout.operator("bonewidget.add_as_widget",
                            text="Use Selected Object",
                            icon='RESTRICT_SELECT_OFF')

        # if the bw collection exists, show the visibility toggle
        bw_collection_name: str = context.preferences.addons[__package__].preferences.bonewidget_collection_name
        bw_collection = recur_layer_collection(
            bpy.context.view_layer.layer_collection, bw_collection_name)

        if bw_collection is not None:
            if bw_collection.hide_viewport:
                icon = "HIDE_ON"
                text = "Show Collection"
            else:
                icon = "HIDE_OFF"
                text = "Hide Collection"

            row = layout.row()
            row.separator()
            row = layout.row()
            row.operator("bonewidget.toggle_collection_visibilty",
                         icon=icon, text=text)
