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
    LayerCollection,
    Object,
    Panel,
    UILayout,
)
from bpy.props import (
    EnumProperty,
    PointerProperty
)

from .bl_class_registry import BlClassRegistry
from .functions import (
    read_widgets,
)
from .objects import (
    BonewidgetCollection
)


def get_widget_list_items(self, context: 'Context'):
    items = []

    for key in sorted(read_widgets().keys()):
        items.append((key, key, ""))

    return items


def widget_object_poll(self, object: 'Object'):
    return object and object.type == "MESH"


@BlClassRegistry()
class BONEWIDGET_PT_posemode_panel(Panel):
    bl_label = "Bone Widget"
    bl_category = "Rig Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_idname = 'VIEW3D_PT_bw_posemode_panel'

    bpy.types.Scene.widget_list = EnumProperty(
        items=get_widget_list_items, name="Shape", description="Shape")
    bpy.types.Scene.widget_object = PointerProperty(
        type=Object, poll=widget_object_poll)

    def draw(self, context: 'Context'):
        layout: 'UILayout' = self.layout

        row = layout.row(align=True)
        row.prop(context.scene, "widget_list", expand=False, text="")

        row = layout.row(align=True)
        row.menu("BONEWIDGET_MT_bw_specials", icon='DOWNARROW_HLT', text="")
        row.operator("bonewidget.create_widget", icon="OBJECT_DATAMODE")

        if context.mode == "POSE":
            row.operator("bonewidget.edit_widget", icon="OUTLINER_DATA_MESH")
        else:
            row.operator("bonewidget.return_to_armature",
                         icon="LOOP_BACK", text='To bone')

        layout.operator("bonewidget.add_as_widget",
                        text="Use Object from Scene",
                        icon='RESTRICT_SELECT_OFF')

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

        # If the widget collection exists, show the visibility toggle
        bw_collection: 'LayerCollection' = BonewidgetCollection().collection

        if bw_collection is not None:
            icon = "HIDE_OFF"
            text = "Hide Collection"

            if bw_collection.hide_viewport:
                icon = "HIDE_ON"
                text = "Show Collection"

            row = layout.row()
            row.separator()
            row = layout.row()
            row.operator("bonewidget.toggle_collection_visibilty",
                         icon=icon, text=text)
