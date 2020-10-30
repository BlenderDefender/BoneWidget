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
from .functions import (
    readWidgets,
    getViewLayerCollection,
)
from .bl_class_registry import BlClassRegistry
from .menus import BONEWIDGET_MT_bw_specials


@BlClassRegistry()
class BONEWIDGET_PT_posemode_panel(bpy.types.Panel):
    bl_label = "Bone Widget"
    bl_category = "Rig Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_idname = 'VIEW3D_PT_bw_posemode_panel'

    items = []
    for key, value in readWidgets().items():
        items.append(key)

    itemsSort = []
    for key in sorted(items):
        itemsSort.append((key, key, ""))

    bpy.types.Scene.widget_list = bpy.props.EnumProperty(
        name="Shape", items=itemsSort, description="Shape")

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)

        if len(bpy.types.Scene.widget_list[1]['items']) < 6:
            row.prop(context.scene, "widget_list", expand=True)
        else:
            row.prop(context.scene, "widget_list", expand=False, text="")

        row = layout.row(align=True)
        row.menu("BONEWIDGET_MT_bw_specials", icon='DOWNARROW_HLT', text="")
        row.operator("bonewidget.create_widget", icon="OBJECT_DATAMODE")

        if bpy.context.mode == "POSE":
            row.operator("bonewidget.edit_widget", icon="OUTLINER_DATA_MESH")
        else:
            row.operator("bonewidget.return_to_armature",
                         icon="LOOP_BACK", text='To bone')

        layout = self.layout
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

        import os
        if bpy.context.mode.title() == 'Pose':
            layout.operator("bonewidget.select_object",
                            text="Select Object as widget shape",
                            icon='RESTRICT_SELECT_OFF')
        elif bpy.context.mode.title() == 'Object' and os.path.exists(os.path.join(os.path.expanduser("~"), "temp.txt")):
            layout.operator("bonewidget.confirm_widget",
                            text="Confirm selected Object as widget shape",
                            icon='CHECKMARK')

        try:
            collection = getViewLayerCollection(context)
        except:
            collection = None

        if collection is not None:
            if collection.hide_viewport:
                icon = "HIDE_ON"
                text = "Unhide Collection"
            else:
                icon = "HIDE_OFF"
                text = "Hide Collection"
            row = layout.row()
            row.separator()
            row = layout.row()
            row.operator("bonewidget.toggle_collection_visibilty",
                         icon=icon, text=text)
