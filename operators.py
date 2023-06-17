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
    Operator,
    UILayout
)
from bpy.props import (
    FloatProperty,
    BoolProperty,
    FloatVectorProperty
)

from .functions import (
    find_match_bones,
    from_widget_find_bone,
    symmetrize_widget_helper,
    bone_matrix,
    create_widget,
    edit_widget,
    return_to_armature,
    add_remove_widgets,
    read_widgets,
    get_collection,
    get_view_layer_collection,
    recur_layer_collection,
    delete_unused_widgets,
    clear_bone_widgets,
    resync_widget_names,
    add_object_as_widget,
)



class BONEWIDGET_OT_create_widget(Operator):
    """Creates a widget for selected bone"""
    bl_idname = "bonewidget.create_widget"
    bl_label = "Create"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: 'Context'):
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

    def draw(self, context: 'Context'):
        layout: 'UILayout' = self.layout
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

    def execute(self, context: 'Context'):
        wgts = read_widgets()
        for bone in bpy.context.selected_pose_bones:
            create_widget(bone, wgts[context.scene.widget_list], self.relative_size, self.global_size, [
                1, 1, 1], self.slide, self.rotation, get_collection(context))
        return {'FINISHED'}


class BONEWIDGET_OT_edit_widget(Operator):
    """Edit the widget for selected bone"""
    bl_idname = "bonewidget.edit_widget"
    bl_label = "Edit"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE'
                and context.active_pose_bone.custom_shape is not None)

    def execute(self, context: 'Context'):
        active_bone = context.active_pose_bone
        try:
            edit_widget(active_bone)
        except KeyError:
            self.report(
                {'INFO'}, 'This widget is the not in the Widget Collection')
        return {'FINISHED'}


class BONEWIDGET_OT_return_to_armature(Operator):
    """Switch back to the armature"""
    bl_idname = "bonewidget.return_to_armature"
    bl_label = "Return to armature"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'MESH'
                and context.object.mode in ['EDIT', 'OBJECT'])

    def execute(self, context: 'Context'):
        b = bpy.context.object
        if from_widget_find_bone(bpy.context.object):
            return_to_armature(bpy.context.object)
        else:
            self.report({'INFO'}, 'Object is not a bone widget')
        return {'FINISHED'}


class BONEWIDGET_OT_match_bone_transforms(Operator):
    """Match the widget to the bone transforms"""
    bl_idname = "bonewidget.match_bone_transforms"
    bl_label = "Match bone transforms"

    def execute(self, context: 'Context'):
        if bpy.context.mode == "POSE":
            for bone in bpy.context.selected_pose_bones:
                bone_matrix(bone.custom_shape, bone)
            return {'FINISHED'}

        for ob in bpy.context.selected_objects:
            if ob.type != 'MESH':
                continue

            match_bone = from_widget_find_bone(ob)
            if match_bone:
                bone_matrix(ob, match_bone)
        return {'FINISHED'}


class BONEWIDGET_OT_match_symmetrize_shape(Operator):
    """Symmetrize to the opposite side ONLY if it is named with a .L or .R (default settings)"""
    bl_idname = "bonewidget.symmetrize_shape"
    bl_label = "Symmetrize"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE'
                and context.object.mode in ['POSE'])

    def execute(self, context: 'Context'):
        try:
            #collection = get_collection(context)
            widget = bpy.context.active_pose_bone.custom_shape
            collection = get_view_layer_collection(context, widget)
            widgets_and_bones = find_match_bones()[0]
            active_object = find_match_bones()[1]
            widgets_and_bones = find_match_bones()[0]

            if not active_object:
                self.report({"INFO"}, "No active bone or object")
                return {'FINISHED'}

            for bone in widgets_and_bones:
                symmetrize_widget_helper(
                    bone, collection, active_object, widgets_and_bones)
        except Exception as e:
            self.report({'INFO'}, "There is nothing to mirror to")
            # pass

        # ! Incoming
        # widget = bpy.context.active_pose_bone.custom_shape
        # collection = get_view_layer_collection(context, widget)
        # widgets_and_bones = find_match_bones()[0]
        # active_object = find_match_bones()[1]
        # widgets_and_bones = find_match_bones()[0]

        # if not active_object:
        #     self.report({"INFO"}, "No active bone or object")
        #     return {'FINISHED'}

        # for bone in widgets_and_bones:
        #     symmetrize_widget_helper(bone, collection, active_object, widgets_and_bones)

        return {'FINISHED'}


class BONEWIDGET_OT_add_widgets(Operator):
    """Add selected mesh object to Bone Widget Library"""
    bl_idname = "bonewidget.add_widgets"
    bl_label = "Add Widgets"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'MESH' and context.object.mode == 'OBJECT'
                and context.active_object is not None)

    def execute(self, context: 'Context'):
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

        add_remove_widgets(
            context, "add", bpy.types.Scene.widget_list[1]["items"], objects)

        return {'FINISHED'}


class BONEWIDGET_OT_remove_widgets(Operator):
    """Remove selected widget object from the Bone Widget Library"""
    bl_idname = "bonewidget.remove_widgets"
    bl_label = "Remove Widgets"

    def execute(self, context: 'Context'):
        objects = bpy.context.scene.widget_list
        unwanted_list = add_remove_widgets(
            context, "remove", bpy.types.Scene.widget_list[1]["items"], objects)
        return {'FINISHED'}


class BONEWIDGET_OT_toggle_collection_visibility(Operator):
    """Show/hide the bone widget collection"""
    bl_idname = "bonewidget.toggle_collection_visibilty"
    bl_label = "Collection Visibilty"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):
        bw_collection_name = context.preferences.addons[__package__].preferences.bonewidget_collection_name
        bw_collection = recur_layer_collection(
            bpy.context.view_layer.layer_collection, bw_collection_name)

        #bw_collection = context.scene.collection.children.get(bw_collection_name)
        bw_collection.hide_viewport = not bw_collection.hide_viewport
        # need to recursivly search for the view_layer
        bw_collection.exclude = False
        # collection = get_view_layer_collection(context)
        # collection.hide_viewport = not collection.hide_viewport
        # collection.exclude = False
        return {'FINISHED'}


class BONEWIDGET_OT_delete_unused_widgets(Operator):
    """Delete unused objects in the WGT collection"""
    bl_idname = "bonewidget.delete_unused_widgets"
    bl_label = "Delete Unused Widgets"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):
        delete_unused_widgets()
        return {'FINISHED'}


class BONEWIDGET_OT_clear_bone_widgets(Operator):
    """Clear widgets from selected pose bones"""
    bl_idname = "bonewidget.clear_widgets"
    bl_label = "Clear Widgets"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):
        clear_bone_widgets()
        return {'FINISHED'}


class BONEWIDGET_OT_resync_widget_names(Operator):
    """Clear widgets from selected pose bones"""
    bl_idname = "bonewidget.resync_widget_names"
    bl_label = "Resync Widget Names"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):
        resync_widget_names()
        return {'FINISHED'}


'''
class BONEWIDGET_OT_select_object(Operator):
    """Select object as widget for selected bone"""
    bl_idname = "bonewidget.select_object"
    bl_label = "Select Object as Widget"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def active_armature(self, context: 'Context'):
        ob = context.object
        ob = str(ob).split('"')
        ob = ob[1]
        return ob

    def active_bone(self, context: 'Context'):
        ob = context.active_bone
        ob = str(ob).split('"')
        ob = ob[1]
        return ob

    def execute(self, context: 'Context'):
        active_armature = self.active_armature(context)
        active_bone = self.active_bone(context)
        write_temp(active_armature, active_bone)
        log_operation("info", 'Write armature name: "{}" and bone name: "{}" to file temp.txt'.format(active_armature, active_bone))
        select_object()
        return {'FINISHED'}


class BONEWIDGET_OT_confirm_widget(Operator):
    """Set selected object as widget for selected bone"""
    bl_idname = "bonewidget.confirm_widget"
    bl_label = "Confirm selected Object as widget shape"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'MESH' and context.object.mode == 'OBJECT')

    def execute(self, context: 'Context'):
        arm_bone = read_temp().split(",")
        active_armature = arm_bone[0]
        active_bone = arm_bone[1]

        active_bone = bpy.data.objects[active_armature].pose.bones[active_bone]
        active_armature = bpy.data.objects[active_armature]

        print(active_armature, active_bone)

        c_w = confirm_widget(context, active_bone, active_armature)

        log_operation("info", 'Duplicate Object "{}" and set duplicate as custom shape for Bone "{}" in Armature "{}".'.format(c_w, active_bone, active_armature))

        return {'FINISHED'}
'''


class BONEWIDGET_OT_add_object_as_widget(Operator):
    """Add selected object as widget for active bone."""
    bl_idname = "bonewidget.add_as_widget"
    bl_label = "Confirm selected Object as widget shape"

    @classmethod
    def poll(cls, context: 'Context'):
        return (len(context.selected_objects) == 2 and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):
        add_object_as_widget(context, get_collection(context))
        return {'FINISHED'}


classes = (
    BONEWIDGET_OT_remove_widgets,
    BONEWIDGET_OT_add_widgets,
    BONEWIDGET_OT_match_symmetrize_shape,
    BONEWIDGET_OT_match_bone_transforms,
    BONEWIDGET_OT_return_to_armature,
    BONEWIDGET_OT_edit_widget,
    BONEWIDGET_OT_create_widget,
    BONEWIDGET_OT_toggle_collection_visibility,
    BONEWIDGET_OT_delete_unused_widgets,
    BONEWIDGET_OT_clear_bone_widgets,
    BONEWIDGET_OT_resync_widget_names,
    BONEWIDGET_OT_add_object_as_widget,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
