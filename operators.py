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
    symmetrizeWidget_helper,
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
    selectObject,
    confirmWidget,
    writeTemp,
    readTemp,
    logOperation,
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
        description="Rotate the widget",
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
            logOperation("info", 'Created Widget {} for Bone {} '.format(
                context.scene.widget_list, bone))

        return {'FINISHED'}


class BONEWIDGET_OT_editWidget(bpy.types.Operator):
    """Edit the widget for selected bone"""
    bl_idname = "bonewidget.edit_widget"
    bl_label = "Edit"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE'
                and context.active_pose_bone.custom_shape is not None)

    def execute(self, context):
        active_bone = context.active_pose_bone
        editWidget(active_bone)
        logOperation("info", 'Edit Widget of Bone {} '.format(active_bone))

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
        b = bpy.context.object
        if fromWidgetFindBone(bpy.context.object):
            returnToArmature(bpy.context.object)
            logOperation(
                "info", 'Return to Armature after editing Widgets: {} '.format(b))

        else:
            logOperation(
                "warning", 'Return to Armature: Object is not a bone widget')
            self.report({'INFO'}, 'Object is not a bone widget')

        return {'FINISHED'}


class BONEWIDGET_OT_matchBoneTransforms(bpy.types.Operator):
    """Match the widget to the bone transforms"""
    bl_idname = "bonewidget.match_bone_transforms"
    bl_label = "Match bone transforms"

    def execute(self, context):
        if bpy.context.mode == "POSE":
            for bone in bpy.context.selected_pose_bones:
                #     if bone.custom_shape_transform and bone.custom_shape:
                #    boneMatrix(bone.custom_shape, bone.custom_shape_transform)
                #     elif bone.custom_shape:
                boneMatrix(bone.custom_shape, bone)
                logOperation("info", 'Match Bone Transforms: Widget {} for Bone {}.'.format(
                    bone.custom_shape, bone))

        else:
            for ob in bpy.context.selected_objects:
                if ob.type == 'MESH':
                    matchBone = fromWidgetFindBone(ob)
                    if matchBone:
                        #     if matchBone.custom_shape_transform:
                        #     boneMatrix(ob, matchBone.custom_shape_transform)
                        #     else:
                        boneMatrix(ob, matchBone)
                        logOperation(
                            "info", 'Match Bone Transforms: Widget {} for Bone {}.'.format(ob, matchBone))

        return {'FINISHED'}


class BONEWIDGET_OT_matchSymmetrizeShape(bpy.types.Operator):
    """Symmetrize to the opposite side, if it is named with a .L or .R"""
    bl_idname = "bonewidget.symmetrize_shape"
    bl_label = "Symmetrize"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            collection = getCollection(context)
            widgetsAndBones = findMatchBones()[0]
            activeObject = findMatchBones()[1]
            widgetsAndBones = findMatchBones()[0]

            if not activeObject:
                self.report({"INFO"}, "No active bone or object")
                logOperation(
                    "warning", 'No active bone or object when trying to symmetrize Bones.')
                return {'FINISHED'}

            for bone in widgetsAndBones:
                symmetrizeWidget_helper(
                    bone, collection, activeObject, widgetsAndBones)
                logOperation("info", 'Symmetrized left and right with following data: {}'.format(
                    widgetsAndBones))
        except Exception as e:
            logOperation(
                "error", "Error when trying to symmetrize: {}".format(str(e)))
            pass

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
                logOperation(
                    "info", "Added item to Widgets List: {}".format(bone.custom_shape))
        else:
            for ob in bpy.context.selected_objects:
                if ob.type == 'MESH':
                    objects.append(ob)
                    logOperation(
                        "info", "Added item to Widgets List: {}".format(ob))

        if not objects:
            self.report({'INFO'}, 'Select Meshes or Pose_bones')
            logOperation(
                "warning", "Error when trying to add item to Widgets List: No Mesh or Pose Bone selected!")

        addRemoveWidgets(
            context, "add", bpy.types.Scene.widget_list[1]['items'], objects)

        return {'FINISHED'}


class BONEWIDGET_OT_removeWidgets(bpy.types.Operator):
    """Remove selected widget object from the Bone Widget Library"""
    bl_idname = "bonewidget.remove_widgets"
    bl_label = "Remove Widgets"

    def execute(self, context):
        objects = bpy.context.scene.widget_list
        unwantedList = addRemoveWidgets(
            context, "remove", bpy.types.Scene.widget_list[1]['items'], objects)
        logOperation(
            "info", 'Deleted Widgets: {} from Widgets list.'.format(objects))
        return {'FINISHED'}


class BONEWIDGET_OT_toggleCollectionVisibility(bpy.types.Operator):
    """HideUnhide the bone widget collection"""
    bl_idname = "bonewidget.toggle_collection_visibilty"
    bl_label = "Collection Visibilty"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context):
        collection = getViewLayerCollection(context)
        collection.hide_viewport = not collection.hide_viewport
        logOperation("info", 'Toggle Collection visibility')
        return {'FINISHED'}


class BONEWIDGET_OT_deleteUnusedWidgets(bpy.types.Operator):
    """Delete unused objects in the WDGT collection"""
    bl_idname = "bonewidget.delete_unused_widgets"
    bl_label = "Delete Unused Widgets"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context):
        deleteUnusedWidgets()
        logOperation("info", 'Deleted unused Widgets.')
        return {'FINISHED'}


class BONEWIDGET_OT_clearBoneWidgets(bpy.types.Operator):
    """Clear widgets from selected pose bones"""
    bl_idname = "bonewidget.clear_widgets"
    bl_label = "Clear Widgets"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context):
        clearBoneWidgets()
        logOperation("info", 'Cleared Bone Widget')
        return {'FINISHED'}


class BONEWIDGET_OT_resyncWidgetNames(bpy.types.Operator):
    """Clear widgets from selected pose bones"""
    bl_idname = "bonewidget.resync_widget_names"
    bl_label = "Resync Widget Names"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context):
        resyncWidgetNames()
        logOperation("info", 'Resynced Widget names')
        return {'FINISHED'}


class BONEWIDGET_OT_selectObject(bpy.types.Operator):
    """Select object as widget for selected bone"""
    bl_idname = "bonewidget.select_object"
    bl_label = "Select Object as Widget"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def active_armature(self, context):
        ob = context.object
        ob = str(ob).split('"')
        ob = ob[1]
        return ob

    def active_bone(self, context):
        ob = context.active_bone
        ob = str(ob).split('"')
        ob = ob[1]
        return ob

    def execute(self, context):
        active_armature = self.active_armature(context)
        active_bone = self.active_bone(context)
        writeTemp(active_armature, active_bone)
        logOperation("info", 'Write armature name: {} and bone name: {} to file temp.txt'.format(
            active_armature, active_bone))
        selectObject()
        return {'FINISHED'}


class BONEWIDGET_OT_confirmWidget(bpy.types.Operator):
    """Set selected object as widget for selected bone"""
    bl_idname = "bonewidget.confirm_widget"
    bl_label = "Confirm selected Object as widget shape"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'MESH' and context.object.mode == 'OBJECT')

    def execute(self, context):
        arm_bone = readTemp().split(",")
        active_armature = arm_bone[0]
        active_bone = arm_bone[1]

        active_bone = bpy.data.objects[active_armature].pose.bones[active_bone]
        active_armature = bpy.data.objects[active_armature]

        print(active_armature, active_bone)

        cW = confirmWidget(context, active_bone, active_armature)

        logOperation("info", "Duplicate Object {} and set duplicate as custom shape for Bone {} in Armature {}.".format(
            cW, active_bone, active_armature))
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
    BONEWIDGET_OT_selectObject,
    BONEWIDGET_OT_confirmWidget,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)

    try:
        import os
        os.remove(os.path.join(os.path.expanduser("~"), "temp.txt"))
    except:
        pass
