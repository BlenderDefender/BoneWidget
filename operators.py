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
    Collection,
    LayerCollection,
    Object,
    Operator,
    PoseBone,
    UILayout
)
from bpy.props import (
    FloatProperty,
    BoolProperty,
    FloatVectorProperty
)

import numpy
from mathutils import Matrix

import typing

from .functions import (
    remove_widgets,
    add_widgets,
    bone_matrix,
    find_match_bones,
    from_widget_find_bone,
    get_collection,
    get_view_layer_collection,
    read_widgets,
    recursively_find_layer_collection,
    symmetrize_widget_helper,
)

from .custom_types import (
    AddonPreferences
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
        for bone in context.selected_pose_bones:
            self.create_widget(bone, wgts[context.scene.widget_list], self.relative_size, self.global_size, [
                1, 1, 1], self.slide, self.rotation, get_collection(context))
        return {'FINISHED'}

    def create_widget(self, bone: 'PoseBone', widget: dict, relative: bool, size: float, scale: typing.List[int], slide: float, rotation: typing.List[int], collection: 'Collection'):
        """Create a widget for a bone.

        Args:
            bone (PoseBone): The bone to create the widget for.
            widget (dict): The JSON Data of the widget to create.
            relative (bool): Whether to use relative size.
            size (float): The size of the widget.
            scale (typing.List[int]): The X, Y, Z scale of the widget.
            slide (float): The slide of the widget along the local Y-Axis
            rotation (typing.List[int]): The rotation of the widget.
            collection (Collection): The collection to create the widget in.
        """

        context = bpy.context
        D = bpy.data

        prefs: 'AddonPreferences' = context.preferences.addons[__package__].preferences

        bw_widget_prefix = prefs.widget_prefix

    #     if bone.custom_shape_transform:
    #    matrix_bone = bone.custom_shape_transform
    #     else:
        matrix_bone = bone

        if bone.custom_shape:
            bone.custom_shape.name = bone.custom_shape.name + "_old"
            bone.custom_shape.data.name = bone.custom_shape.data.name + "_old"
            if context.scene.collection.objects.get(bone.custom_shape.name):
                context.scene.collection.objects.unlink(bone.custom_shape)

        # make the data name include the prefix
        new_data = D.meshes.new(bw_widget_prefix + bone.name)

        bone_length = 1
        if not relative:
            bone_length = 1 / bone.bone.length

        # add the verts
        new_data.from_pydata(numpy.array(widget['vertices']) * [size * scale[0] * bone_length, size * scale[2]
                                                                * bone_length, size * scale[1] * bone_length], widget['edges'], widget['faces'])

        # Create tranform matrices (slide vector and rotation)
        widget_matrix = Matrix()
        trans = Matrix.Translation((0, slide, 0))
        rot = rotation.to_matrix().to_4x4()

        # Translate then rotate the matrix
        widget_matrix = widget_matrix @ trans
        widget_matrix = widget_matrix @ rot

        # transform the widget with this matrix
        new_data.transform(widget_matrix)

        new_data.update(calc_edges=True)

        new_object = D.objects.new(bw_widget_prefix + bone.name, new_data)

        new_object.data = new_data
        new_object.name = bw_widget_prefix + bone.name
        collection.objects.link(new_object)

        new_object.matrix_world = context.active_object.matrix_world @ matrix_bone.bone.matrix_local
        new_object.scale = [matrix_bone.bone.length,
                            matrix_bone.bone.length, matrix_bone.bone.length]
        layer = context.view_layer
        layer.update()

        bone.custom_shape = new_object
        bone.bone.show_wire = True


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
            self.edit_widget(active_bone)
        except KeyError:
            self.report(
                {'INFO'}, 'This widget is the not in the Widget Collection')
        return {'FINISHED'}

    def edit_widget(self, active_bone: 'PoseBone'):
        """Jump to edit mode for editing the widget of the active bone.

        Args:
            active_bone (PoseBone): The active bone.
        """

        context = bpy.context
        D = bpy.data
        widget: 'Object' = active_bone.custom_shape

        armature = active_bone.id_data
        bpy.ops.object.mode_set(mode='OBJECT')
        context.active_object.select_set(False)

        collection: 'LayerCollection' = get_view_layer_collection(
            context, widget)
        collection.hide_viewport = False

        if context.space_data.local_view:
            bpy.ops.view3d.localview()

        # select object and make it active
        widget.select_set(True)
        context.view_layer.objects.active = widget
        bpy.ops.object.mode_set(mode='EDIT')


class BONEWIDGET_OT_return_to_armature(Operator):
    """Switch back to the armature"""
    bl_idname = "bonewidget.return_to_armature"
    bl_label = "Return to armature"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'MESH'
                and context.object.mode in ['EDIT', 'OBJECT'])

    def execute(self, context: 'Context'):
        if not from_widget_find_bone(context.object):  # TODO: Move to poll
            self.report({'INFO'}, 'Object is not a bone widget')
            return {'FINISHED'}

        self.return_to_armature(context.object)
        return {'FINISHED'}

    def return_to_armature(self, widget: 'Object'):
        """Return to the armature after editing a bone widget.

        Args:
            widget (Object): The widget that was edited.
        """

        context = bpy.context
        D = bpy.data

        bone: 'PoseBone' = from_widget_find_bone(widget)
        armature: 'Armature' = bone.id_data

        if context.active_object.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')

        collection = get_view_layer_collection(context, widget)
        collection.hide_viewport = True
        if context.space_data.local_view:
            bpy.ops.view3d.localview()
        context.view_layer.objects.active = armature
        armature.select_set(True)
        bpy.ops.object.mode_set(mode='POSE')
        armature.data.bones[bone.name].select = True
        armature.data.bones.active = armature.data.bones[bone.name]


class BONEWIDGET_OT_match_bone_transforms(Operator):
    """Match the widget to the bone transforms"""
    bl_idname = "bonewidget.match_bone_transforms"
    bl_label = "Match bone transforms"

    def execute(self, context: 'Context'):
        if context.mode == "POSE":
            for bone in context.selected_pose_bones:
                bone_matrix(context, bone.custom_shape, bone)
            return {'FINISHED'}

        for ob in context.selected_objects:
            if ob.type != 'MESH':
                continue

            match_bone = from_widget_find_bone(ob)
            if match_bone:
                bone_matrix(context, ob, match_bone)
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
            # collection = get_collection(context)
            widget = context.active_pose_bone.custom_shape
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
        # widget = context.active_pose_bone.custom_shape
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
        if context.mode == "POSE":
            for bone in context.selected_pose_bones:
                objects.append(bone.custom_shape)
        else:
            for ob in context.selected_objects:
                if ob.type == 'MESH':
                    objects.append(ob)

        if not objects:
            self.report({'INFO'}, 'Select Meshes or Pose_bones')

        add_widgets(
            context, bpy.types.Scene.widget_list[1]["items"], objects)

        return {'FINISHED'}


class BONEWIDGET_OT_remove_widgets(Operator):
    """Remove selected widget object from the Bone Widget Library"""
    bl_idname = "bonewidget.remove_widgets"
    bl_label = "Remove Widgets"

    def execute(self, context: 'Context'):
        objects = context.scene.widget_list
        unwanted_list = remove_widgets(
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
        prefs: 'AddonPreferences' = context.preferences.addons[__package__].preferences

        bw_collection_name = prefs.bonewidget_collection_name
        bw_collection = recursively_find_layer_collection(
            context.view_layer.layer_collection, bw_collection_name)

        # bw_collection = context.scene.collection.children.get(bw_collection_name)
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
        D = bpy.data

        prefs: 'AddonPreferences' = context.preferences.addons[__package__].preferences

        bw_collection_name: str = prefs.bonewidget_collection_name
        collection: 'Collection' = recursively_find_layer_collection(
            context.scene.collection, bw_collection_name)
        widget_list: list = []

        for ob in D.objects:
            ob: 'Object'
            if ob.type != 'ARMATURE':
                continue

            for bone in ob.pose.bones:
                bone: 'PoseBone'
                if bone.custom_shape:
                    widget_list.append(bone.custom_shape)

        unwanted_list = [
            ob for ob in collection.all_objects if ob not in widget_list]
        # save the current context mode
        mode = context.mode
        # jump into object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        # delete unwanted widgets
        bpy.ops.object.delete({"selected_objects": unwanted_list})
        # jump back to current mode
        bpy.ops.object.mode_set(mode=mode)

        return {'FINISHED'}


class BONEWIDGET_OT_clear_bone_widgets(Operator):
    """Clear widgets from selected pose bones"""
    bl_idname = "bonewidget.clear_widgets"
    bl_label = "Clear Widgets"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):

        if context.object.type != 'ARMATURE':
            return {'FINISHED'}

        for bone in context.selected_pose_bones:
            if bone.custom_shape:
                bone.custom_shape = None
                bone.custom_shape_transform = None

        return {'FINISHED'}


class BONEWIDGET_OT_resync_widget_names(Operator):
    """Sync widget names with the names of the bones they're assigned to."""
    bl_idname = "bonewidget.resync_widget_names"
    bl_label = "Resync Widget Names"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):

        D = bpy.data

        prefs: 'AddonPreferences' = context.preferences.addons[__package__].preferences

        bw_collection_name: str = prefs.bonewidget_collection_name
        bw_widget_prefix: str = prefs.widget_prefix

        widgets_and_bones: dict = {}

        if context.object.type != 'ARMATURE':
            return {'FINISHED'}

        for bone in context.active_object.pose.bones:
            bone: 'PoseBone'
            if bone.custom_shape:
                widgets_and_bones[bone] = bone.custom_shape

        for bone, widget in widgets_and_bones.items():
            # ! This always returns True
            if bone.name != (bw_widget_prefix + bone.name):
                D.objects[widget.name].name = str(
                    bw_widget_prefix + bone.name)

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
        self.add_object_as_widget(context, get_collection(context))
        return {'FINISHED'}

    def add_object_as_widget(self, context: 'Context', collection: 'Collection') -> None:
        """Add the first selected object as the custom shape of the active bone.

        Args:
            context (Context): The current Blender context.
            collection (Collection): The collection to store the widgets in.
        """

        sel = context.selected_objects
        prefs: 'AddonPreferences' = context.preferences.addons[__package__].preferences

        # bw_collection = prefs.bonewidget_collection_name

        if sel[1].type != 'MESH':
            return

        active_bone: 'PoseBone' = context.active_pose_bone
        widget_object: 'Object' = sel[1]

        # deal with any existing shape
        if active_bone.custom_shape:
            active_bone.custom_shape.name = active_bone.custom_shape.name + "_old"
            active_bone.custom_shape.data.name = active_bone.custom_shape.data.name + "_old"

            if context.scene.collection.objects.get(active_bone.custom_shape.name):
                context.scene.collection.objects.unlink(
                    active_bone.custom_shape)

        # duplicate shape
        widget: 'Object' = widget_object.copy()
        widget.data = widget.data.copy()
        # reamame it
        bw_widget_prefix = prefs.widget_prefix
        widget_name = bw_widget_prefix + active_bone.name
        widget.name = widget_name
        widget.data.name = widget_name
        # link it
        collection.objects.link(widget)

        # match transforms
        widget.matrix_world = context.active_object.matrix_world @ active_bone.bone.matrix_local
        widget.scale = [active_bone.bone.length,
                        active_bone.bone.length, active_bone.bone.length]
        layer = context.view_layer
        layer.update()

        active_bone.custom_shape = widget
        active_bone.bone.show_wire = True

        # deselect original object
        widget_object.select_set(False)


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
