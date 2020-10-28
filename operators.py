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
    findMatchBones,
    fromWidgetFindBone,
    findMirrorObject,
    symmetrizeWidget,
    boneMatrix,
    createWidget,
    editWidget,
    returnToArmature,
    addRemoveWidgets,
    readWidgets,
    objectDataToDico,
    getCollection,
    getViewLayerCollection,
    deleteUnusedWidgets,
    clearBoneWidgets,
    resyncWidgetNames,
)
from bpy.types import Operator
from bpy.props import FloatProperty, BoolProperty, FloatVectorProperty


class BONEWIDGET_OT_createWidget(bpy.types.Operator):
    """Creates a widget for selected bone"""
    bl_idname = "bonewidget.create_widget"
    bl_label = "Create"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.mode == 'POSE')

    relative_size: BoolProperty(
        name="Scale to Bone length",
        default=True,
        description="Scale Widget to bone length"
    )

    global_size: FloatProperty(
        name="Global Size",
        default=1.0,
        description="Global Size"
    )

    slide: FloatProperty(
        name="Slide",
        default=0.0,
        subtype='NONE',
        unit='NONE',
        description="Slide widget along y axis"
    )
    rotation: FloatVectorProperty(
        name="Rotation",
        description="Rotate the widget NOT YET WORKING",
        default=(0.0, 0.0, 0.0),
        subtype='EULER',
        unit='ROTATION',
        precision=1,
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column()
        row = col.row(align=True)
        row.prop(self, "relative_size")
        row = col.row(align=True)
        row.prop(self, "global_size", expand=False)
        row = col.row(align=True)
        row.prop(self, "slide")
        row = col.row(align=True)
        row.prop(self, "rotation", text="Rotation")

    def execute(self, context):
        wgts = readWidgets()
        for bone in bpy.context.selected_pose_bones:
            createWidget(bone, wgts[context.scene.widget_list], self.relative_size, self.global_size, [
                         1, 1, 1], self.slide, self.rotation, getCollection(context))

        return {'FINISHED'}


class BONEWIDGET_OT_editWidget(bpy.types.Operator):
    """Edit the widget for selected bone"""
    bl_idname = "bonewidget.edit_widget"
    bl_label = "Edit"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.pose)

    def execute(self, context):
        editWidget(context.active_pose_bone)
        return {'FINISHED'}


class BONEWIDGET_OT_returnToArmature(bpy.types.Operator):
    """Switch back to the armature"""
    bl_idname = "bonewidget.return_to_armature"
    bl_label = "Return to armature"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'MESH'
                and context.object.mode in ['EDIT', 'OBJECT'])

    def execute(self, context):
        if fromWidgetFindBone(bpy.context.object):
            returnToArmature(bpy.context.object)

        else:
            self.report({'INFO'}, 'Object is not a bone widget')

        return {'FINISHED'}


class BONEWIDGET_OT_matchBoneTransforms(bpy.types.Operator):
    """Match the widget to the bone transforms"""
    bl_idname = "bonewidget.match_bone_transforms"
    bl_label = "Match bone transforms"

    def execute(self, context):
        if bpy.context.mode == "POSE":
            for bone in bpy.context.selected_pose_bones:
                # if bone.custom_shape_transform and bone.custom_shape:
                #boneMatrix(bone.custom_shape, bone.custom_shape_transform)
                # elif bone.custom_shape:
                boneMatrix(bone.custom_shape, bone)

        else:
            for ob in bpy.context.selected_objects:
                if ob.type == 'MESH':
                    matchBone = fromWidgetFindBone(ob)
                    if matchBone:
                        # if matchBone.custom_shape_transform:
                        #boneMatrix(ob, matchBone.custom_shape_transform)
                        # else:
                        boneMatrix(ob, matchBone)

        return {'FINISHED'}


class BONEWIDGET_OT_matchSymmetrizeShape(bpy.types.Operator):
    """Symmetrize to the opposite side, if it is named with a .L or .R"""
    bl_idname = "bonewidget.symmetrize_shape"
    bl_label = "Symmetrize"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        collection = getCollection(context)
        widgetsAndBones = findMatchBones()[0]
        activeObject = findMatchBones()[1]
        widgetsAndBones = findMatchBones()[0]

        if not activeObject:
            self.report({"INFO"}, "No active bone or object")
            return {'FINISHED'}

        for bone in widgetsAndBones:
            if activeObject.name.endswith("L"):
                if bone.name.endswith("L") and widgetsAndBones[bone]:
                    symmetrizeWidget(bone, collection)
            elif activeObject.name.endswith("R"):
                if bone.name.endswith("R") and widgetsAndBones[bone]:
                    symmetrizeWidget(bone, collection)

        return {'FINISHED'}


class BONEWIDGET_OT_addWidgets(bpy.types.Operator):
    """Add selected mesh object to Bone Widget Library"""
    bl_idname = "bonewidget.add_widgets"
    bl_label = "Add Widgets"

    def execute(self, context):
        objects = []
        if bpy.context.mode == "POSE":
            for bone in bpy.context.selected_pose_bones:
                objects.append(bone.custom_shape)
        else:
            for ob in bpy.context.selected_objects:
                if ob.type == 'MESH':
                    objects.append(ob)

        if not objects:
            self.report({'INFO'}, 'Select Meshes or Pose_bones')

        addRemoveWidgets(
            context, "add", bpy.types.Scene.widget_list[1]['items'], objects)

        return {'FINISHED'}


class BONEWIDGET_OT_removeWidgets(bpy.types.Operator):
    """Remove selected widget object from the Bone Widget Library"""
    bl_idname = "bonewidget.remove_widgets"
    bl_label = "Remove Widgets"

    def execute(self, context):
        objects = bpy.context.scene.widget_list
        addRemoveWidgets(context, "remove",
                         bpy.types.Scene.widget_list[1]['items'], objects)
        return {'FINISHED'}


class BONEWIDGET_OT_toggleCollectionVisibility(bpy.types.Operator):
    """HideUnhide the bone widget collection"""
    bl_idname = "bonewidget.toggle_collection_visibilty"
    bl_label = "Collection Visibilty"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.pose)

    def execute(self, context):
        collection = getViewLayerCollection(context)
        collection.hide_viewport = not collection.hide_viewport
        return {'FINISHED'}


class BONEWIDGET_OT_deleteUnusedWidgets(bpy.types.Operator):
    """Delete unused objects in the WDGT collection"""
    bl_idname = "bonewidget.delete_unused_widgets"
    bl_label = "Delete Unused Widgets"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.pose)

    def execute(self, context):
        deleteUnusedWidgets()
        return {'FINISHED'}


class BONEWIDGET_OT_clearBoneWidgets(bpy.types.Operator):
    """Clear widgets from selected pose bones"""
    bl_idname = "bonewidget.clear_widgets"
    bl_label = "Clear Widgets"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.pose)

    def execute(self, context):
        clearBoneWidgets()
        return {'FINISHED'}


class BONEWIDGET_OT_resyncWidgetNames(bpy.types.Operator):
    """Clear widgets from selected pose bones"""
    bl_idname = "bonewidget.resync_widget_names"
    bl_label = "Resync Widget Names"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.pose)

    def execute(self, context):
        resyncWidgetNames()
        return {'FINISHED'}


classes = (
    BONEWIDGET_OT_removeWidgets,
    BONEWIDGET_OT_addWidgets,
    BONEWIDGET_OT_matchSymmetrizeShape,
    BONEWIDGET_OT_matchBoneTransforms,
    BONEWIDGET_OT_returnToArmature,
    BONEWIDGET_OT_editWidget,
    BONEWIDGET_OT_createWidget,
    BONEWIDGET_OT_toggleCollectionVisibility,
    BONEWIDGET_OT_deleteUnusedWidgets,
    BONEWIDGET_OT_clearBoneWidgets,
    BONEWIDGET_OT_resyncWidgetNames,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
