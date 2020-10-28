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


class BoneWidgetPreferences(AddonPreferences):
    bl_idname = 'boneWidget'

    # widget prefix
    widget_prefix: StringProperty(
        name="Bone Widget prefix",
        description="Choose a prefix for the widget objects",
        default="WDGT_",
    )
    '''
    #symmetry suffix (will try to implement this later)
    symmetry_suffix: EnumProperty(
        name="Bone Widget symmetry suffix",
        description="Choose a naming convention for the symmetrical widgets",
        default=".L",
    )
    '''
    # collection name
    bonewidget_collection_name: StringProperty(
        name="Bone Widget collection name",
        description="Choose a name for the collection the widgets will appear",
        default="WDGT_shapes",
    )

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        col = row.column()
        col.prop(self, "widget_prefix", text="Widget Prefix")
        # add symmetry suffix later
        #col.prop(self, "symmetry_suffix", text="Symmetry suffix")
        col.prop(self, "bonewidget_collection_name", text="Collection name")


classes = (
    BoneWidgetPreferences,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
